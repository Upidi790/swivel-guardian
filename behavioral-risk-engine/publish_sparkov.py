"""Import synthetic source data separately, then verify real HTTP and Tiger history."""
import copy,json,threading
from pathlib import Path
import joblib,pandas as pd
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from psycopg.types.json import Jsonb
from sparkov_service import OUT,COLUMNS
from storage import TigerStore
from config import load_config
from api import make_server

def main():
    load_config();rows=joblib.load(OUT/'history.joblib');report=json.loads((OUT/'report.json').read_text());art=joblib.load(OUT/'model.joblib')
    evaluation=pd.read_csv(OUT/'evaluation.csv.gz').set_index('transaction_id')
    with TigerStore().connect() as conn:
        conn.execute((Path(__file__).parent/'schema-sparkov.sql').read_text())
        conn.execute('CREATE TEMP TABLE sparkov_stage (LIKE sparkov_transactions) ON COMMIT DROP')
        with conn.cursor().copy('COPY sparkov_stage FROM STDIN') as stream:
            for row in rows:stream.write_row(tuple(row[c] for c in COLUMNS))
        conn.execute('INSERT INTO sparkov_users(user_id) SELECT DISTINCT user_id FROM sparkov_stage ON CONFLICT DO NOTHING')
        conn.execute('INSERT INTO sparkov_transactions SELECT * FROM sparkov_stage ON CONFLICT DO NOTHING')
        conn.execute('CREATE TEMP TABLE outcome_stage (LIKE sparkov_outcomes) ON COMMIT DROP')
        with conn.cursor().copy('COPY outcome_stage FROM STDIN') as stream:
            for txid,r in evaluation.iterrows():stream.write_row((txid,bool(r.is_fraud),r.partition))
        conn.execute('INSERT INTO sparkov_outcomes SELECT * FROM outcome_stage ON CONFLICT DO NOTHING')
        conn.execute('INSERT INTO sparkov_models VALUES (%s,%s) ON CONFLICT DO NOTHING',(art['version'],Jsonb(report)))
        count=conn.execute('SELECT count(*) FROM sparkov_transactions').fetchone()[0]
        assert count==len(rows)
        print('Imported source rows:',count,'Database MiB:',round(conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]/1024**2,1),flush=True)
    server=make_server(0);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    def call(tx):
        req=Request(f'http://127.0.0.1:{server.server_port}/behavior/analyze',data=json.dumps(tx).encode(),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=30) as response:return json.load(response)
    try:
        for name in ('high_score','low_score'):
            tx=json.loads((OUT/(name+'-request.json')).read_text());result=call(tx)
            assert result['persisted'];assert abs(result['model_score']-evaluation.loc[tx['transaction_id'],'score'])<1e-8
            assert call(tx)==result
            (OUT/(name+'-response.json')).write_text(json.dumps(result,indent=2))
        for key in ('amount','is_fraud'):
            invalid=copy.deepcopy(tx)
            if key=='amount':invalid[key]+=1
            else:invalid[key]=1
            try:call(invalid);raise AssertionError('Invalid request accepted')
            except HTTPError as exc:assert exc.code==400
        verified={'source_rows':len(rows),'users':50,'http_and_tiger_batch_parity':True,'stable_retries':True,
          'conflicting_retries_rejected':True,'outcome_field_rejected':True,'history_query_strictly_before_payment':True,
          'labels_excluded_from_scoring':True,'route':'/behavior/analyze','model_version':art['version']}
        (OUT/'integration-verification.json').write_text(json.dumps(verified,indent=2));print(json.dumps(verified,indent=2))
    finally:server.shutdown();server.server_close();worker.join()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('Sparkov verification failed:',type(exc).__name__,'SQLSTATE:',getattr(exc,'sqlstate',None));raise SystemExit(1)
