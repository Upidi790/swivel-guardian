"""Validation-selected model comparison; existing test is retrospective, not fresh."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
os.environ.setdefault('OPENBLAS_NUM_THREADS','4')
from pathlib import Path
import argparse, gc, json, time, warnings, zipfile
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from scipy import sparse
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, precision_recall_curve
from sklearn.exceptions import ConvergenceWarning
from train_ml import evaluate, select_threshold, split_masks
from ml_model import FEATURES as BASIC, CATEGORICAL as BASIC_CAT, ARTIFACTS, normalize, encode

OUT=ARTIFACTS/'benchmark'

def rich_data(path, all_v=False):
    cats=BASIC_CAT+[f'M{i}' for i in range(1,10)]+[f'id_{i:02d}' for i in range(12,39)]
    base_num=['TransactionAmt','dist1','dist2']+[f'C{i}' for i in range(1,15)]+[f'D{i}' for i in range(1,16)]+[f'id_{i:02d}' for i in range(1,12)]
    # Unsupervised redundancy selection on only the first 5,000 source rows.
    # Neither labels nor validation/test data are used to select V columns.
    with zipfile.ZipFile(path) as z:
        with z.open('train_transaction.csv') as f:
            sample=pd.read_csv(f,nrows=5000,usecols=lambda c:c.startswith('V') or c=='TransactionDT',dtype=np.float32)
        vcols=[c for c in sample if c.startswith('V')]
        corr=sample[vcols].corr().abs()
        kept=[]
        for col in vcols:
            if sample[col].nunique()<2: continue
            if not any(corr.loc[col,prior]>.95 for prior in kept): kept.append(col)
            if len(kept)>=80: break
        if all_v:
            kept=vcols
        nums=base_num+kept
        txcols=['TransactionID','TransactionDT','isFraud']+[c for c in nums+cats if not c.startswith('id_') and c not in ('DeviceInfo','DeviceType')]
        with z.open('train_transaction.csv') as f:
            tx=pd.read_csv(f,usecols=txcols,dtype={c:'string' if c in cats else np.float32 for c in txcols if c not in ('TransactionID','TransactionDT','isFraud')})
        idcols=['TransactionID']+[c for c in nums+cats if c.startswith('id_') or c in ('DeviceInfo','DeviceType')]
        with z.open('train_identity.csv') as f:
            identity=pd.read_csv(f,usecols=idcols,dtype={c:'string' if c in cats else np.float32 for c in idcols if c!='TransactionID'})
    data=tx.merge(identity,how='left',on='TransactionID',validate='one_to_one').sort_values(['TransactionDT','TransactionID']).reset_index(drop=True)
    if data.TransactionID.duplicated().any(): raise ValueError('Duplicate IDs')
    for col in cats: data[col]=data[col].fillna('__MISSING__').astype(str)
    for col,parts in {'card1_addr1':['card1','addr1'],'card1_card2':['card1','card2'],'email_pair':['P_emaildomain','R_emaildomain']}.items():
        data[col]=data[parts[0]]+'|'+data[parts[1]]
        cats.append(col)
    assert sample.TransactionDT.max()<data.TransactionDT.iloc[int(len(data)*.7)]
    return data,nums,cats,kept

def best_f1(y,p):
    precision,recall,thresholds=precision_recall_curve(y,p)
    f1=2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1],1e-15)
    return float(thresholds[int(np.argmax(f1))])

def matrix_for_trees(data,nums,cats,mask):
    x=data[nums+cats].copy()
    vocab={}
    for col in cats:
        vocab[col]=list(data.loc[mask,col].unique())
        x[col]=pd.Categorical(data[col],categories=vocab[col])
    return x,vocab

def fit_linear(data,nums,cats,masks):
    # Train-only clipping and scaling; exact same transforms at inference.
    numeric=data[nums].to_numpy(dtype=np.float32)
    numeric=np.sign(numeric)*np.log1p(np.abs(numeric))
    low=np.nanquantile(numeric[masks['train']],.001,axis=0).astype(np.float32)
    high=np.nanquantile(numeric[masks['train']],.999,axis=0).astype(np.float32)
    numeric=np.clip(numeric,low,high)
    imputer=SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)
    imputer.fit(numeric[masks['train']])
    numeric=imputer.transform(numeric).astype(np.float32)
    scaler=StandardScaler()
    scaler.fit(numeric[masks['train']])
    numeric=scaler.transform(numeric).astype(np.float32)
    encoder=OneHotEncoder(handle_unknown='infrequent_if_exist',min_frequency=50,max_categories=1000,dtype=np.float32)
    encoder.fit(data.loc[masks['train'],cats])
    x=sparse.hstack([sparse.csr_matrix(numeric),encoder.transform(data[cats])],format='csr',dtype=np.float32)
    del numeric
    gc.collect()
    model=LogisticRegression(C=.1,solver='liblinear',max_iter=200,tol=1e-4,random_state=42)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always',ConvergenceWarning)
        model.fit(x[masks['train']],data.loc[masks['train'],'isFraud'])
    converged=not any(issubclass(w.category,ConvergenceWarning) for w in caught)
    print('Logistic convergence:',converged,'iterations:',model.n_iter_.tolist(),flush=True)
    scores=model.predict_proba(x)[:,1]
    pack={'algorithm':'LogisticRegression','model':model,'numeric':nums,'categorical':cats,'imputer':imputer,'scaler':scaler,'encoder':encoder,'low':low,'high':high,'converged':converged}
    del x
    gc.collect()
    return scores,pack

def main(path):
    OUT.mkdir(exist_ok=True)
    print('Loading richer features with train-only redundancy filtering...',flush=True)
    data,nums,cats,kept=rich_data(path)
    masks=split_masks(data)
    time_values=data.TransactionDT.to_numpy()
    early_cut=time_values[int(len(data)*.775)]
    early=masks['validation'] & (time_values<early_cut)
    selection=masks['validation'] & (time_values>=early_cut)
    y=data.isFraud.to_numpy(dtype=int)
    protocol={'train_rows':int(masks['train'].sum()),'early_stopping_rows':int(early.sum()),'selection_rows':int(selection.sum()),'test_rows':int(masks['test'].sum()),
              'selection':'Highest selection-set average precision among converged candidates; threshold maximizes selection F1. Test labels not used for choosing a candidate or threshold.',
              'test_status':'Retrospective comparison on previously inspected temporal test. No fresh independent validation is claimed.',
              'v_selection':'First 5,000 training rows only; remove abs correlation > .95 greedily, at most 80 V features.',
              'retained_v_features':kept,'numeric':nums,'categorical':cats}
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    print('Feature counts:',len(nums),'numeric;',len(cats),'categorical',flush=True)
    candidates={}
    def record(name,p,pack):
        threshold=best_f1(y[selection],p[selection])
        fpr_threshold=select_threshold(y[selection],p[selection])
        result={'algorithm':pack['algorithm'],'features':len(pack['numeric'])+len(pack['categorical']),
                'threshold_max_f1':threshold,'threshold_fpr2':fpr_threshold,
                'selection_max_f1':evaluate(y[selection],p[selection],threshold),
                'selection_fpr2':evaluate(y[selection],p[selection],fpr_threshold),
                'eligible':pack.get('converged',True)}
        pack['threshold']=threshold
        pack['fpr2_threshold']=fpr_threshold
        joblib.dump(pack,OUT/(name+'.joblib'))
        np.save(OUT/(name+'-scores.npy'),p)
        candidates[name]=result
        (OUT/'selection-results.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
        print(name,'selection AP:',round(result['selection_max_f1']['average_precision'],4),'F1:',round(result['selection_max_f1']['f1'],4),flush=True)
    print('Fitting logistic regression with richer features...',flush=True)
    p,pack=fit_linear(data,nums,cats,masks)
    record('logistic_rich',p,pack)
    del pack,p
    gc.collect()
    for name,ns,cs,leaves in [('lightgbm_basic',list(BASIC[:3]),list(BASIC_CAT),31),('lightgbm_rich',nums,cats,63)]:
        print('Fitting',name,flush=True)
        x,vocab=matrix_for_trees(data,ns,cs,masks['train'])
        model=lgb.LGBMClassifier(n_estimators=1600,learning_rate=.035,num_leaves=leaves,min_child_samples=80,
              colsample_bytree=.85,subsample=.8,subsample_freq=1,reg_lambda=5,reg_alpha=.1,
              n_jobs=4,random_state=42,verbosity=-1,force_col_wise=True,max_bin=127)
        model.fit(x.loc[masks['train']],y[masks['train']],eval_set=[(x.loc[early],y[early])],eval_metric='average_precision',
                  callbacks=[lgb.early_stopping(100,first_metric_only=True,verbose=False),lgb.log_evaluation(200)])
        p=model.predict_proba(x)[:,1]
        pack={'algorithm':'LGBMClassifier','model':model,'numeric':ns,'categorical':cs,'vocab':vocab,'best_iteration':model.best_iteration_}
        record(name,p,pack)
        del x,p,pack,model
        gc.collect()
    # Winner frozen before computing any test metrics for the new candidates.
    winner=max((n for n,r in candidates.items() if r['eligible']),key=lambda n:candidates[n]['selection_max_f1']['average_precision'])
    (OUT/'winner-selection.json').write_text(json.dumps({'winner':winner,'criterion':'selection average precision'},indent=2),encoding='utf-8')
    print('Validation-selected winner:',winner,flush=True)
    for name,result in candidates.items():
        p=np.load(OUT/(name+'-scores.npy'))
        result['test_max_f1']=evaluate(y[masks['test']],p[masks['test']],result['threshold_max_f1'])
        result['test_fpr2']=evaluate(y[masks['test']],p[masks['test']],result['threshold_fpr2'])
    previous=json.loads((ARTIFACTS/'evaluation.json').read_text(encoding='utf-8'))
    report={'protocol':protocol,'winner':winner,'candidates':candidates,'previous_model':previous['test'],
            'source_zip_sha256':previous['source_zip_sha256'], 'selected_model_version':'ieee-benchmark-v3-'+winner+'-'+previous['source_zip_sha256'][:12]}
    (OUT/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    pack=joblib.load(OUT/(winner+'.joblib'))
    pack['model_version']=report['selected_model_version']
    pack['dataset_key']='ieee_cis_'+previous['source_zip_sha256'][:12]
    pack['required_features']=[c for c in pack['numeric']+pack['categorical'] if c not in ('card1_addr1','card1_card2','email_pair')]
    joblib.dump(pack,OUT/'selected-model.joblib')
    p=np.load(OUT/(winner+'-scores.npy'))
    exported=pd.DataFrame({'transaction_id':data.TransactionID,'relative_seconds':data.TransactionDT,'model_score':p,'split':np.select([masks['train'],masks['validation']],['train','validation'],default='test')})
    exported.to_csv(OUT/'predictions.csv.gz',index=False,compression='gzip')
    test_positions=np.flatnonzero(masks['test'])
    for name,pos in [('high_score',test_positions[np.argmax(p[masks['test']])]),('low_score',test_positions[np.argmin(p[masks['test']])])]:
        fields={c:None if pd.isna(data.iloc[pos][c]) or data.iloc[pos][c]=='__MISSING__' else data.iloc[pos][c] for c in pack['required_features']}
        payload={'dataset':'ieee_cis','transaction_id':str(int(data.iloc[pos].TransactionID)),'features':fields}
        (OUT/(name+'-request.json')).write_text(json.dumps(payload,indent=2,default=lambda v:v.item()),encoding='utf-8')
    print(json.dumps({'winner':winner,'comparison':{n:r['test_max_f1'] for n,r in candidates.items()}},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--zip',required=True)
    main(parser.parse_args().zip)
