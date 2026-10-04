"""Integration check: counts, held-out metrics, persistent HTTP scoring and retries."""
import copy
import json
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from config import load_config
from storage import TigerStore
from ml_model import ARTIFACTS
from api import make_server

def main():
    load_config()
    report=json.loads((ARTIFACTS/'evaluation.json').read_text(encoding='utf-8'))
    version=report['model_version']
    dataset='ieee_cis_'+report['source_zip_sha256'][:12]
    with TigerStore().connect() as conn:
        count=conn.execute('SELECT count(*) FROM ieee_transactions WHERE dataset_key=%s',(dataset,)).fetchone()[0]
        assert count==sum(p['rows'] for p in report['partitions'].values())
        groups=conn.execute('SELECT p.requires_intervention,o.is_fraud,count(*) FROM ml_predictions p JOIN ieee_outcomes o USING(dataset_key,transaction_id) WHERE p.model_version=%s GROUP BY 1,2',(version,)).fetchall()
        actual={(predicted,label):n for predicted,label,n in groups}
        expected={(True,True):report['test']['true_positives'],(True,False):report['test']['false_positives'],
                  (False,True):report['test']['false_negatives'],(False,False):report['test']['true_negatives']}
        assert actual==expected,(actual,expected)
    server=make_server(0)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    def call(payload):
        request=Request(f'http://127.0.0.1:{server.server_port}/ml/v2/analyze',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=30) as response: return json.load(response)
    results={}
    try:
        for name in ('high_score','low_score'):
            payload=json.loads((ARTIFACTS/(name+'-request.json')).read_text(encoding='utf-8'))
            result=call(payload)
            assert result['persisted'] and result['model_version']==version
            assert call(payload)==result
            results[name]={'risk_score':result['risk_score'],'requires_intervention':result['requires_intervention']}
            (ARTIFACTS/(name+'-response.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
        conflict=copy.deepcopy(payload)
        conflict['features']['TransactionAmt']+=1
        try:
            call(conflict)
            raise AssertionError('Conflicting retry was accepted')
        except HTTPError as error:
            assert error.code==400
    finally:
        server.shutdown();server.server_close();thread.join()
    verification={'model_version':version,'source_rows':count,'test_prediction_rows':sum(actual.values()),
                  'database_confusion_matrix_matches_report':True,'http_persistence_verified':True,
                  'identical_retries_verified':True,'conflicting_retry_rejected':True,'examples':results}
    (ARTIFACTS/'database-verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    print(json.dumps(verification,indent=2))

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('Integration check failed:',type(exc).__name__,'SQLSTATE:',getattr(exc,'sqlstate',None))
        raise SystemExit(1)
