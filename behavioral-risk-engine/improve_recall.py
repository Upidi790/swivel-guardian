"""Expanded V-feature experiment with validation-only operating-point selection."""
from benchmark_models import *

DEST=ARTIFACTS/'recall-v4'

def recall_threshold(y,p,target=.90):
    precision,recall,thresholds=precision_recall_curve(y,p)
    eligible=np.flatnonzero(recall[:-1]>=target)
    return float(thresholds[eligible[-1]])

def main(path, temporal=False, balance=False):
    global DEST
    if temporal: DEST=ARTIFACTS/'recall-v5'
    if balance:
        temporal=True
        DEST=ARTIFACTS/'balance-v6'
    DEST.mkdir(exist_ok=True)
    data,nums,cats,kept=rich_data(path,all_v=True)
    masks=split_masks(data)
    times=data.TransactionDT.to_numpy()
    cut=times[int(len(data)*.775)]
    early=masks['validation']&(times<cut)
    selection=masks['validation']&(times>=cut)
    y=data.isFraud.to_numpy(dtype=int)
    required=[c for c in nums+cats if c not in ('card1_addr1','card1_card2','email_pair')]
    if temporal:
        import temporal_features as tf
        data=tf.transform(data)
        nums=nums+tf.NUMERIC
        cats=cats+tf.CATEGORICAL
        required=required+['TransactionDT']
    # Keep the inference contract identical to v3 apart from additional V columns.
    x,vocab=matrix_for_trees(data,nums,cats,masks['train'])
    ids=data.TransactionID.to_numpy()
    raw_times=data.TransactionDT.to_numpy()
    del data
    gc.collect()
    protocol={'feature_count':len(nums)+len(cats),'v_features':kept,
      'selection':'Minimize validation false-positive rate at >=90% validation recall; thresholds fixed before test evaluation.',
      'test_status':'Previously inspected chronological test; retrospective comparison, not independent validation.',
      'early_stopping':'Explicit AUC metric, chronological early-stopping partition.',
      'train_rows':int(masks['train'].sum()),'early_rows':int(early.sum()),'selection_rows':int(selection.sum()),'test_rows':int(masks['test'].sum())}
    (DEST/'protocol.json').write_text(json.dumps(protocol,indent=2))
    results={}
    configurations=[('temporal_v',127,1)] if temporal else [('full_v',63,1),('full_v_weighted',127,4)]
    if balance:
        import shutil
        prior=json.loads((ARTIFACTS/'recall-v5'/'comparison.json').read_text())
        results['temporal_baseline']=prior['candidates']['temporal_v']
        for suffix in ('.joblib','-scores.npy'):
            shutil.copyfile(ARTIFACTS/'recall-v5'/('temporal_v'+suffix),DEST/('temporal_baseline'+suffix))
        ratio=float(np.sum(y[masks['train']]==0)/np.sum(y[masks['train']]==1))
        configurations=[('balanced_loss',127,ratio),('undersampled_4to1',127,1),('recent_weighted',127,4)]
        protocol['balance_policy']='Training only: inverse class-frequency loss; 4:1 majority undersampling; or 30-day half-life recency weights with fraud loss weight 4. Original validation/test distributions preserved. No fabricated synthetic rows.'
        protocol['training_class_ratio']=ratio
        (DEST/'protocol.json').write_text(json.dumps(protocol,indent=2))
    for name,leaves,weight in configurations:
        print('Training',name,'with',len(x.columns),'features',flush=True)
        model=lgb.LGBMClassifier(n_estimators=1800,learning_rate=.035,num_leaves=leaves,
            min_child_samples=60,colsample_bytree=.7,subsample=.8,subsample_freq=1,
            reg_lambda=5,reg_alpha=.1,n_jobs=4,random_state=42,verbosity=-1,
            force_col_wise=True,max_bin=127,scale_pos_weight=weight,metric='None')
        train_positions=np.flatnonzero(masks['train'])
        sample_weight=None
        if name=='undersampled_4to1':
            positive=train_positions[y[train_positions]==1]
            negative=train_positions[y[train_positions]==0]
            chosen=np.random.default_rng(42).choice(negative,size=min(len(negative),4*len(positive)),replace=False)
            train_positions=np.sort(np.concatenate([positive,chosen]))
        elif name=='recent_weighted':
            age=(times[train_positions].max()-times[train_positions])/86400
            sample_weight=np.power(.5,age/30)
            sample_weight=sample_weight/sample_weight.mean()
        assert np.all(masks['train'][train_positions])
        print('Training rows:',len(train_positions),'fraud:',int(y[train_positions].sum()),'fraud loss weight:',weight,flush=True)
        model.fit(x.iloc[train_positions],y[train_positions],sample_weight=sample_weight,eval_set=[(x.loc[early],y[early])],eval_metric='auc',
            callbacks=[lgb.early_stopping(120,first_metric_only=True,verbose=True),lgb.log_evaluation(100)])
        p=np.full(len(y),np.nan)
        for mask in [selection,masks['test']]:
            p[mask]=model.predict_proba(x.loc[mask])[:,1]
        thresholds={'recall90':recall_threshold(y[selection],p[selection]),
                    'recall95':recall_threshold(y[selection],p[selection],.95),
                    'max_f1':best_f1(y[selection],p[selection]),
                    'fpr2':select_threshold(y[selection],p[selection])}
        results[name]={'best_iteration':model.best_iteration_,'training_rows':len(train_positions),'training_fraud_rows':int(y[train_positions].sum()),'fraud_loss_weight':weight,'thresholds':thresholds,
                      'validation':{k:evaluate(y[selection],p[selection],t) for k,t in thresholds.items()}}
        pack={'algorithm':'LGBMClassifier','model':model,'numeric':nums,'categorical':cats,'vocab':vocab,
              'threshold':thresholds['max_f1'],'thresholds':thresholds,
              'required_features':required,'temporal_features':temporal,
              'model_version':('ieee-balance-v6-' if balance else 'ieee-recall-v5-' if temporal else 'ieee-recall-v4-')+name,'dataset_key':'ieee_cis_4cc646da09d0'}
        joblib.dump(pack,DEST/(name+'.joblib'))
        np.save(DEST/(name+'-scores.npy'),p)
        (DEST/'selection.json').write_text(json.dumps(results,indent=2))
        print(name,'validation',results[name]['validation'],flush=True)
        del model,pack
        gc.collect()
    winner=min(results,key=lambda n:results[n]['validation']['recall90']['false_positive_rate'])
    (DEST/'winner.json').write_text(json.dumps({'winner':winner,'protocol':protocol},indent=2))
    for name,result in results.items():
        p=np.load(DEST/(name+'-scores.npy'))
        result['test']={k:evaluate(y[masks['test']],p[masks['test']],t) for k,t in result['thresholds'].items()}
    report={'winner':winner,'protocol':protocol,'candidates':results}
    (DEST/'comparison.json').write_text(json.dumps(report,indent=2))
    pack=joblib.load(DEST/(winner+'.joblib'))
    joblib.dump(pack,DEST/'selected-model.joblib')
    p=np.load(DEST/(winner+'-scores.npy'))
    # Round-trip examples are extracted from the exact model matrix, without labels.
    positions=np.flatnonzero(masks['test'])
    for label,pos in [('high_score',positions[np.argmax(p[positions])]),('low_score',positions[np.argmin(p[positions])])]:
        row=x.iloc[pos]
        fields={c:None if pd.isna(row[c]) or row[c]=='__MISSING__' else row[c] for c in pack['required_features'] if c!='TransactionDT'}
        if temporal: fields['TransactionDT']=int(raw_times[pos])
        payload={'dataset':'ieee_cis','transaction_id':str(int(ids[pos])),'features':fields}
        (DEST/(label+'-request.json')).write_text(json.dumps(payload,indent=2,default=lambda v:v.item()))
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--zip',required=True);parser.add_argument('--temporal',action='store_true');parser.add_argument('--balance',action='store_true')
    args=parser.parse_args();main(args.zip,args.temporal,args.balance)
