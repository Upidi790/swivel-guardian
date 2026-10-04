"""Persist only the selected candidate and predictions; activate after verification."""
import json
import pandas as pd
from psycopg.types.json import Jsonb
from config import load_config
from storage import TigerStore
from benchmark_scorer import OUT

def main():
    load_config()
    report=json.loads((OUT/'comparison.json').read_text(encoding='utf-8'))
    winner=report['winner']
    threshold=report['candidates'][winner]['threshold_max_f1']
    dataset='ieee_cis_'+report['source_zip_sha256'][:12]
    version=report['selected_model_version']
    with TigerStore().connect() as conn:
        conn.execute('INSERT INTO ml_models(model_version,dataset_key,report) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',(version,dataset,Jsonb(report)))
        conn.execute('CREATE TEMP TABLE benchmark_stage(transaction_id BIGINT, score DOUBLE PRECISION) ON COMMIT DROP')
        with conn.cursor().copy('COPY benchmark_stage FROM STDIN') as copy:
            for chunk in pd.read_csv(OUT/'predictions.csv.gz',chunksize=20000):
                for row in chunk.loc[chunk.split=='test',['transaction_id','model_score']].itertuples(index=False,name=None):
                    copy.write_row((int(row[0]),float(row[1])))
        conn.execute('INSERT INTO ml_predictions SELECT %s,transaction_id,%s,score,score >= %s FROM benchmark_stage ON CONFLICT DO NOTHING',(dataset,version,threshold))
    with TigerStore().connect() as conn:
        rows=conn.execute('SELECT p.requires_intervention,o.is_fraud,count(*) FROM ml_predictions p JOIN ieee_outcomes o USING(dataset_key,transaction_id) WHERE model_version=%s GROUP BY 1,2',(version,)).fetchall()
        actual={(bool(a),bool(b)):n for a,b,n in rows}
        r=report['candidates'][winner]['test_max_f1']
        expected={(True,True):r['true_positives'],(True,False):r['false_positives'],(False,True):r['false_negatives'],(False,False):r['true_negatives']}
        assert actual==expected
        print('Verified selected-model prediction rows:',sum(actual.values()),flush=True)
        print('Database MiB:',round(conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]/1024**2,1),flush=True)

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('Publish failed:',type(exc).__name__,'SQLSTATE:',getattr(exc,'sqlstate',None))
        raise SystemExit(1)
