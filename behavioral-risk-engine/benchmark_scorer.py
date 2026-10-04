"""Inference for the validation-selected benchmark winner."""
import math
import joblib
import numpy as np
import pandas as pd
from scipy import sparse
from ml_model import ARTIFACTS

OUT=ARTIFACTS/'benchmark'
COMBINATIONS={'card1_addr1':['card1','addr1'],'card1_card2':['card1','card2'],'email_pair':['P_emaildomain','R_emaildomain']}

def prepare(fields,artifact):
    names=artifact['numeric']+artifact['categorical']
    values=dict(fields)
    for name,parts in COMBINATIONS.items():
        if name in names:
            values[name]='|'.join('__MISSING__' if values.get(p) is None else str(values[p]) for p in parts)
    frame=pd.DataFrame([values])
    if artifact.get('temporal_features'):
        from temporal_features import transform
        frame=transform(frame)
    frame=frame.reindex(columns=names)
    for col in artifact['numeric']:
        frame[col]=pd.to_numeric(frame[col],errors='coerce').astype(np.float32)
    for col in artifact['categorical']:
        frame[col]=frame[col].fillna('__MISSING__').astype(str)
    if artifact['algorithm']=='LGBMClassifier':
        for col in artifact['categorical']:
            frame[col]=pd.Categorical(frame[col],categories=artifact['vocab'][col])
        return frame
    numeric=frame[artifact['numeric']].to_numpy(dtype=np.float32)
    numeric=np.sign(numeric)*np.log1p(np.abs(numeric))
    numeric=np.clip(numeric,artifact['low'],artifact['high'])
    numeric=artifact['scaler'].transform(artifact['imputer'].transform(numeric)).astype(np.float32)
    return sparse.hstack([sparse.csr_matrix(numeric),artifact['encoder'].transform(frame[artifact['categorical']])],format='csr',dtype=np.float32)

class BenchmarkScorer:
    def __init__(self, artifact_path=None):
        self.artifact=joblib.load(artifact_path or OUT/'selected-model.joblib')
    def validate(self,payload):
        if not isinstance(payload,dict) or set(payload)!={'dataset','transaction_id','features'} or payload.get('dataset')!='ieee_cis':
            raise ValueError('Expected dataset=ieee_cis, transaction_id and features')
        txid=payload['transaction_id']
        if not isinstance(txid,str) or not txid or len(txid)>128: raise ValueError('Invalid transaction_id')
        fields=payload['features']
        if not isinstance(fields,dict): raise ValueError('features must be an object')
        # The richer model requires an explicit schema: omitted fields cannot
        # silently masquerade as source-data missing values. Nulls are supported.
        if set(fields)!=set(self.artifact['required_features']):
            raise ValueError('Provide exactly the selected model feature schema; use its generated example')
        for col in self.artifact['required_features']:
            value=fields[col]
            if value is None: continue
            if col in self.artifact['numeric'] or col=='TransactionDT':
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or abs(value)>np.finfo(np.float32).max: raise ValueError('Invalid numeric feature')
            elif not isinstance(value,str) or len(value)>512: raise ValueError('Invalid categorical feature')
        if fields.get('TransactionAmt') is None or fields['TransactionAmt']<=0: raise ValueError('Amount must be positive')
        if self.artifact.get('temporal_features') and (fields.get('TransactionDT') is None or fields['TransactionDT']<0):
            raise ValueError('TransactionDT must be a nonnegative source-relative time')
        return prepare(fields,self.artifact)
    def analyze(self,payload):
        matrix=self.validate(payload)
        art=self.artifact
        p=float(art['model'].predict_proba(matrix)[0,1])
        if art['algorithm']=='LGBMClassifier':
            contributions=art['model'].booster_.predict(matrix,pred_contrib=True)[0]
            base=float(contributions[-1])
            names=art['numeric']+art['categorical']
            effects=[{'feature':name,'log_odds_contribution':float(contributions[i])} for i,name in enumerate(names)]
            method='LightGBM native TreeSHAP contributions to raw log odds; contributions plus base reconstruct the raw score. Associations, not causal reasons or proof of scam.'
        else:
            contributions=matrix.multiply(art['model'].coef_[0]).toarray()[0]
            base=float(art['model'].intercept_[0])
            numeric_names=list(art['imputer'].get_feature_names_out(art['numeric']))
            names=numeric_names+list(art['encoder'].get_feature_names_out(art['categorical']))
            effects=[{'feature':name,'log_odds_contribution':float(contributions[i])} for i,name in enumerate(names)]
            method='Exact linear feature contributions to log odds; contributions plus intercept reconstruct the raw score. Associations, not causal reasons.'
        effects.sort(key=lambda e:abs(e['log_odds_contribution']),reverse=True)
        threshold=art['threshold']
        return {'transaction_id':payload['transaction_id'],'dataset':'ieee_cis','model_version':art['model_version'],
                'model_type':art['algorithm'],'risk_score':round(100*p,3),'model_score':p,
                'score_kind':'uncalibrated_dataset_fraud_model_output','intervention_threshold':round(100*threshold,6),
                'threshold_policy':'Maximum F1 on model-selection validation period',
                'requires_intervention':bool(p>=threshold),'decision':'INVESTIGATE' if p>=threshold else 'NO_MODEL_TRIGGER',
                'feature_contributions':effects[:8],'explanation_base_log_odds':base,
                'explanation_total_log_odds':base+float(np.sum(contributions[:-1] if art['algorithm']=='LGBMClassifier' else contributions)),
                'explanation_method':method,'missing_features':[k for k,v in payload['features'].items() if v is None],
                'limitations':['Retrospective IEEE-CIS fraud benchmark; not an independently validated bank-transfer scam detector.',
                               'Richer anonymized source features require a compatible upstream feature provider. Do not invent them for real payments.',
                               'A low score is not proof of safety. No verified customer history or victim interview enters this model.'],
                'agent_guidance':'Combine with separately collected customer answers; do not infer identities, personal habits or scam certainty from anonymized feature contributions.'}
