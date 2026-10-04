"""Reproducible 50-customer Sparkov demo, strict past-only evaluation."""
import argparse,hashlib,json,zipfile
from collections import defaultdict
from itertools import groupby
from pathlib import Path
import joblib,numpy as np,pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import confusion_matrix,precision_score,recall_score,f1_score,roc_curve
from lightgbm import LGBMClassifier
from behavior_features import CustomerState,NUMERIC

OUT=Path(__file__).parent/'sparkov_artifacts'
def identifier(value):return hashlib.sha256(('sparkov-demo:'+str(value)).encode()).hexdigest()[:20]
def metrics(y,s,t):
    pred=s>=t;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
    return {'rows':len(y),'fraud_rows':int(sum(y)),'precision':float(precision_score(y,pred,zero_division=0)),
      'recall':float(recall_score(y,pred,zero_division=0)),'f1':float(f1_score(y,pred,zero_division=0)),
      'false_positive_rate':float(fp/(fp+tn)),'accuracy':float((tp+tn)/len(y)),
      'true_positives':int(tp),'false_positives':int(fp),'false_negatives':int(fn),'true_negatives':int(tn)}
def threshold(y,s):
    fp,tp,ts=roc_curve(y,s,drop_intermediate=False)
    eligible=np.flatnonzero(fp<=.02);best=eligible[np.argmax(tp[eligible])]
    return float(ts[best]) if np.isfinite(ts[best]) else float(np.max(s)+1)
def build(path):
    OUT.mkdir(exist_ok=True)
    digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z:
        cards=set()
        for chunk in pd.read_csv(z.open('fraudTrain.csv'),usecols=['cc_num'],dtype=str,chunksize=100000):cards.update(chunk.cc_num)
        selected=set(sorted(cards,key=identifier)[:50])
        cols=['cc_num','trans_date_trans_time','amt','merchant','category','lat','long','merch_lat','merch_long','trans_num','is_fraud']
        parts=[]
        for name,split in [('fraudTrain.csv','development'),('fraudTest.csv','test')]:
            for chunk in pd.read_csv(z.open(name),usecols=cols,dtype={'cc_num':str},chunksize=100000):
                keep=chunk[chunk.cc_num.isin(selected)].copy();keep['partition']=split;parts.append(keep)
    data=pd.concat(parts,ignore_index=True).sort_values(['trans_date_trans_time','trans_num']).reset_index(drop=True)
    assert data.trans_num.is_unique
    assert data.loc[data.partition=='development','trans_date_trans_time'].max()<data.loc[data.partition=='test','trans_date_trans_time'].min()
    rows=[]
    for r in data.itertuples(index=False):
        rows.append({'transaction_id':r.trans_num,'user_id':identifier(r.cc_num),'timestamp':r.trans_date_trans_time.replace(' ','T'),
          'amount':float(r.amt),'merchant_id':identifier(r.merchant),'category':r.category,
          'home_latitude':float(r.lat),'home_longitude':float(r.long),'merchant_latitude':float(r.merch_lat),'merchant_longitude':float(r.merch_long)})
    labels=data.is_fraud.to_numpy(dtype=int);is_test=(data.partition=='test').to_numpy()
    times=data.trans_date_trans_time.to_numpy();cut=times[np.flatnonzero(~is_test)[int((~is_test).sum()*.8)]]
    train=(~is_test)&(times<cut);val=(~is_test)&(times>=cut)
    states=defaultdict(CustomerState);features=[];rule_scores=[]
    print('Selected customer rows:',len(rows),'customers:',len(selected),flush=True)
    # Score all simultaneous events before observing any of them.
    for _,batch in groupby(rows,key=lambda r:r['timestamp']):
        batch=list(batch)
        for row in batch:
            f,baseline,signals=states[row['user_id']].describe(row)
            features.append(f);rule_scores.append(sum(s['points'] for s in signals))
        for row in batch:states[row['user_id']].observe(row)
    frame=pd.DataFrame(features)[NUMERIC];covered=(frame.history_count>=20).to_numpy()
    masks={'train':train&covered,'validation':val&covered,'test':is_test&covered}
    imputer=SimpleImputer(strategy='median',add_indicator=True,keep_empty_features=True)
    imputer.fit(frame.loc[masks['train']]);x=imputer.transform(frame)
    models={};scores={'rules':np.array(rule_scores,dtype=float)}
    print('Fitting Isolation Forest and behavioral-feature LightGBM...',flush=True)
    models['isolation_forest']=IsolationForest(n_estimators=200,max_samples=512,random_state=42,n_jobs=4)
    models['isolation_forest'].fit(x[masks['train']])
    scores['isolation_forest']=-models['isolation_forest'].score_samples(x)
    models['behavioral_lightgbm']=LGBMClassifier(n_estimators=300,num_leaves=15,max_depth=-1,learning_rate=.04,min_child_samples=40,reg_lambda=5,n_jobs=4,random_state=42,verbosity=-1)
    models['behavioral_lightgbm'].fit(x[masks['train']],labels[masks['train']])
    scores['behavioral_lightgbm']=models['behavioral_lightgbm'].predict_proba(x)[:,1]
    candidates={}
    for name,s in scores.items():
        t=threshold(labels[masks['validation']],s[masks['validation']])
        candidates[name]={'threshold':t,'validation':metrics(labels[masks['validation']],s[masks['validation']],t)}
    winner=max(candidates,key=lambda n:(candidates[n]['validation']['recall'],-candidates[n]['validation']['false_positive_rate']))
    (OUT/'selection.json').write_text(json.dumps({'winner':winner,'candidates':candidates},indent=2))
    for name,s in scores.items():candidates[name]['test']=metrics(labels[masks['test']],s[masks['test']],candidates[name]['threshold'])
    report={'source':'Sparkov synthetic credit-card dataset, Kaggle kartik2112/fraud-detection',
      'source_sha256':digest,'customer_selection':'First 50 training-card identifiers sorted by salted SHA256, independent of labels.',
      'customers':50,'rows':len(rows),'split':'Earliest 80% of selected official training observations for fit; remaining 20% for selection; official fraudTest.csv for test. Chronological cutoff respects ties.',
      'covered_rows':{k:int(v.sum()) for k,v in masks.items()},'cold_start_test_rows':int((is_test&~covered).sum()),
      'features':NUMERIC,'winner':winner,'candidates':candidates,
      'unusual_legitimate_test':{name:metrics(labels[masks['test']&(labels==0)&(np.array(rule_scores)>=40)],s[masks['test']&(labels==0)&(np.array(rule_scores)>=40)],candidates[name]['threshold']) if np.sum(masks['test']&(labels==0)&(np.array(rule_scores)>=40)) else None for name,s in scores.items()},
      'limits':['Synthetic data; not real APP scam detection accuracy.','50-customer reproducible subset, not full population.','Unusual-legitimate subset defined by predeclared rule score >=40; not independent human annotation.','Baseline includes prior observed source transactions regardless of fraud label; success status unavailable.','Merchant locations are not customer/device locations; timestamps use the source clock without a verified local timezone.']}
    version='sparkov-behavior-1-'+digest[:12]
    artifact={'version':version,'winner':winner,'threshold':candidates[winner]['threshold'],'model':models.get(winner),
      'imputer':imputer,'feature_names':NUMERIC,'reference_scores':np.sort(scores[winner][masks['train']])}
    joblib.dump(artifact,OUT/'model.joblib');joblib.dump(rows,OUT/'history.joblib',compress=3)
    pd.DataFrame({'transaction_id':[r['transaction_id'] for r in rows],'is_fraud':labels,'partition':np.select([train,val],['train','validation'],default='test'),
      'score':scores[winner],'covered':covered,'requires_intervention':scores[winner]>=artifact['threshold']}).to_csv(OUT/'evaluation.csv.gz',index=False)
    (OUT/'report.json').write_text(json.dumps(report,indent=2))
    testpositions=np.flatnonzero(masks['test'])
    for name,pos in [('high_score',testpositions[np.argmax(scores[winner][testpositions])]),('low_score',testpositions[np.argmin(scores[winner][testpositions])])]:
        (OUT/(name+'-request.json')).write_text(json.dumps(rows[pos],indent=2))
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--zip',required=True)
    build(parser.parse_args().zip)
