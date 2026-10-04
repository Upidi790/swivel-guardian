"""Behavioral demo API with Tiger-backed strictly earlier history and audit records."""
from pathlib import Path
import bisect,json
import joblib,numpy as np,pandas as pd
from psycopg.types.json import Jsonb
from behavior_features import validate,from_history,NUMERIC
from storage import TigerStore

OUT=Path(__file__).parent/'sparkov_artifacts'
COLUMNS=['transaction_id','user_id','timestamp','amount','merchant_id','category','home_latitude','home_longitude','merchant_latitude','merchant_longitude']
class SparkovService:
    def __init__(self,persist=False):
        self.persist=persist;self.artifact=joblib.load(OUT/'model.joblib');self.histories=None
    def score(self,tx,history):
        features,baseline,signals=from_history(tx,history)
        art=self.artifact;mature=baseline['history_count']>=20
        raw=None;percentile=None;trigger=None
        if mature:
            x=art['imputer'].transform(pd.DataFrame([features])[NUMERIC])
            if art['winner']=='rules':raw=float(sum(s['points'] for s in signals))
            elif art['winner']=='isolation_forest':raw=float(-art['model'].score_samples(x)[0])
            else:raw=float(art['model'].predict_proba(x)[0,1])
            percentile=100*bisect.bisect_right(art['reference_scores'],raw)/len(art['reference_scores'])
            trigger=bool(raw>=art['threshold'])
        return {'transaction_id':tx['transaction_id'],'user_id':tx['user_id'],'model_version':art['version'],
          'source':'sparkov_synthetic','model_type':art['winner'],'model_score':raw,'model_threshold':art['threshold'],
          'risk_score':percentile,'score_kind':'Percentile of model anomaly/fraud score among training observations; not a scam probability.',
          'requires_intervention':trigger,'decision':'INSUFFICIENT_HISTORY' if not mature else 'INVESTIGATE' if trigger else 'NO_BEHAVIORAL_TRIGGER',
          'risk_level':'INSUFFICIENT_DATA' if not mature else 'HIGH' if trigger else 'LOW',
          'baseline':baseline,'features':features,'signals':signals,'rule_score':sum(s['points'] for s in signals),
          'explanation_kind':'Signals describe observed baseline deviations; they are not exact model attributions or proof of fraud.',
          'unavailable_features':['device_novelty','ip_region_novelty','bank_recipient_registration_age','trusted_bank_recipients','account_opening_age','payment_success_status','victim_answers'],
          'limitations':['Synthetic card transactions; not validated on real authorized-payment scams.','Merchant geography is not live customer location.','Source-clock hours are not verified customer-local hours.','Merchant first observation is not bank-payee registration.'],
          'agent_guidance':'Use deviations to ask contextual questions. Do not automatically hold a payment or infer safety from a low score. An insufficient-history result requires an explicit fallback.'}
    def analyze(self,tx):
        validate(tx)
        if not self.persist:
            if self.histories is None:
                self.histories={}
                for row in joblib.load(OUT/'history.joblib'):self.histories.setdefault(row['user_id'],[]).append(row)
            result=self.score(tx,self.histories.get(tx['user_id'],[]));result['persisted']=False;return result
        with TigerStore().connect() as conn:
            version=self.artifact['version']
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(version+':'+tx['transaction_id'],))
            old=conn.execute('SELECT request,result FROM sparkov_risk_events WHERE transaction_id=%s AND model_version=%s',(tx['transaction_id'],version)).fetchone()
            if old:
                if old[0]!=tx:raise ValueError('Conflicting retry')
                return old[1]
            records=conn.execute('SELECT transaction_id,user_id,event_time,amount,merchant_id,category,home_latitude,home_longitude,merchant_latitude,merchant_longitude FROM sparkov_transactions WHERE user_id=%s AND event_time<%s AND transaction_id<>%s ORDER BY event_time,transaction_id',(tx['user_id'],tx['timestamp'],tx['transaction_id'])).fetchall()
            history=[]
            for record in records:
                row=dict(zip(COLUMNS,record));row['timestamp']=row['timestamp'].isoformat();history.append(row)
            result=self.score(tx,history);result['persisted']=True
            conn.execute('INSERT INTO sparkov_risk_events VALUES (%s,%s,now(),%s,%s)',(tx['transaction_id'],version,Jsonb(tx),Jsonb(result)))
            return result
