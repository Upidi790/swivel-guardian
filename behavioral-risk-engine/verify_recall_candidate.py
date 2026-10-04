"""Publish candidate metrics/predictions and verify real HTTP/Tiger persistence."""
import copy,json,threading
import numpy as np
import pandas as pd
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from psycopg.types.json import Jsonb
from config import load_config
from storage import TigerStore
from recall_scorer import RecallScorer
from ml_model import ARTIFACTS
from api import make_server

def main():
    load_config();out=ARTIFACTS/'recall-selected'
    report=json.loads((out/'selection.json').read_text())
    scorer=RecallScorer();art=scorer.artifact
    folder,name=report['selected'].split('/')
    metrics=report['candidates'][report['selected']]['test']['max_f1']
    n=metrics['rows']
    scores=np.load(ARTIFACTS/folder/(name+'-scores.npy'))[-n:]
    ids=pd.read_csv(ARTIFACTS/'ieee-selected.csv.gz',usecols=['TransactionID']).TransactionID.to_numpy()[-n:]
    assert len(scores)==n and np.isfinite(scores).all()
    with TigerStore().connect() as conn:
        conn.execute('INSERT INTO ml_models(model_version,dataset_key,report) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(art['model_version'],art['dataset_key'],Jsonb(report)))
        conn.execute('CREATE TEMP TABLE recall_stage(transaction_id BIGINT, score DOUBLE PRECISION) ON COMMIT DROP')
        with conn.cursor().copy('COPY recall_stage FROM STDIN') as stream:
            for txid,score in zip(ids,scores):stream.write_row((int(txid),float(score)))
        conn.execute('INSERT INTO ml_predictions SELECT %s,transaction_id,%s,score,score >= %s FROM recall_stage ON CONFLICT DO NOTHING',(art['dataset_key'],art['model_version'],art['threshold']))
        rows=conn.execute('SELECT p.requires_intervention,o.is_fraud,count(*) FROM ml_predictions p JOIN ieee_outcomes o USING(dataset_key,transaction_id) WHERE model_version=%s GROUP BY 1,2',(art['model_version'],)).fetchall()
        actual={(bool(a),bool(b)):count for a,b,count in rows}
        expected={(True,True):metrics['true_positives'],(True,False):metrics['false_positives'],(False,True):metrics['false_negatives'],(False,False):metrics['true_negatives']}
        assert actual==expected
    server=make_server(0)
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def call(payload):
        request=Request(f'http://127.0.0.1:{server.server_port}/ml/candidate/analyze',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=30) as response:return json.load(response)
    try:
        for label,expected_score in [('high_score',max(scores)),('low_score',min(scores))]:
            payload=json.loads((out/(label+'-request.json')).read_text())
            result=call(payload)
            assert result['persisted'] and abs(result['model_score']-expected_score)<1e-7
            assert call(payload)==result
            (out/(label+'-response.json')).write_text(json.dumps(result,indent=2))
        for kind in ('conflict','label'):
            bad=copy.deepcopy(payload)
            if kind=='conflict':bad['features']['TransactionAmt']+=1
            else:bad['features']['isFraud']=1
            try:call(bad);raise AssertionError('Invalid request accepted')
            except HTTPError as exc:assert exc.code==400
        verified={'model_version':art['model_version'],'prediction_rows':n,'database_confusion_matches':True,
                  'http_predictions_match_batch':True,'retry_idempotency':True,'invalid_requests_rejected':True,
                  'default_api_changed':False}
        (out/'integration-verification.json').write_text(json.dumps(verified,indent=2))
        print(json.dumps(verified,indent=2))
    finally:server.shutdown();server.server_close();worker.join()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Candidate verification failed:',type(exc).__name__,'SQLSTATE:',getattr(exc,'sqlstate',None))
        raise SystemExit(1)
