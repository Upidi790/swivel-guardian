"""Score requests, persist results, and keep evaluation labels out of the agent path."""
from psycopg.types.json import Jsonb
from ml_model import MLScorer, validate_request
from storage import TigerStore

class MLService:
    def __init__(self, persist=False, scorer=None):
        self.scorer=scorer or MLScorer()
        self.persist=persist
    def analyze(self,payload):
        if hasattr(self.scorer,'validate'):
            self.scorer.validate(payload)
        else:
            validate_request(payload)
        if not self.persist:
            result=self.scorer.analyze(payload)
            result['persisted']=False
            return result
        model_version=self.scorer.artifact['model_version']
        with TigerStore().connect() as conn:
            # Serialize concurrent retries; no outcome labels queried here.
            conn.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))',(model_version+':'+payload['transaction_id'],))
            old=conn.execute('SELECT request,result FROM ml_risk_events WHERE transaction_id=%s AND model_version=%s',
                             (payload['transaction_id'],model_version)).fetchone()
            if old:
                if old[0]!=payload: raise ValueError('Transaction id already used with different features')
                return old[1]
            result=self.scorer.analyze(payload)
            result['persisted']=True
            conn.execute('INSERT INTO ml_risk_events(transaction_id,model_version,request,result) VALUES (%s,%s,%s,%s)',
                         (payload['transaction_id'],model_version,Jsonb(payload),Jsonb(result)))
            return result
