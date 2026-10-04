"""Bulk-load selected source fields and held-out predictions into Tiger Data."""
import json
import argparse
from pathlib import Path
import pandas as pd
from psycopg.types.json import Jsonb
from config import load_config
from storage import TigerStore, ROOT
from ml_model import ARTIFACTS, FEATURES, CATEGORICAL

def main(predictions_only=False):
    load_config()
    report=json.loads((ARTIFACTS/'evaluation.json').read_text(encoding='utf-8'))
    dataset='ieee_cis_'+report['source_zip_sha256'][:12]
    with TigerStore().connect() as conn:
        conn.execute((ROOT/'schema-ml.sql').read_text(encoding='utf-8'))
        size=conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]
        print('Existing database MiB:',round(size/1024**2,1),flush=True)
        if size > 400*1024**2 and not predictions_only:
            raise RuntimeError('Database already exceeds 400 MiB; review space before bulk import.')
        conn.execute('INSERT INTO ml_datasets(dataset_key,source_name,source_sha256) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                     (dataset,'IEEE-CIS Fraud Detection Kaggle labeled training files',report['source_zip_sha256']))
        conn.execute('INSERT INTO ml_models(model_version,dataset_key,report) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING',
                     (report['model_version'],dataset,Jsonb(report)))
        conn.execute('CREATE TEMP TABLE ieee_stage (transaction_id BIGINT, relative_seconds BIGINT, split TEXT, features JSONB, is_fraud BOOLEAN, model_score DOUBLE PRECISION) ON COMMIT DROP')
        count=0
        with conn.cursor().copy('COPY ieee_stage FROM STDIN') as copy:
            for chunk in pd.read_csv(ARTIFACTS/'ieee-selected.csv.gz',chunksize=20000,dtype={c:'string' for c in CATEGORICAL}):
                if predictions_only:
                    chunk=chunk[chunk['split']=='test']
                for row in chunk.to_dict('records'):
                    fields={col:None if pd.isna(row[col]) else row[col] for col in FEATURES}
                    copy.write_row((int(row['TransactionID']),int(row['TransactionDT']),row['split'],Jsonb(fields),bool(row['isFraud']),float(row['model_score'])))
                count+=len(chunk)
                if count and count%100000==0: print('Staged rows:',count,flush=True)
        if not predictions_only:
            conn.execute('INSERT INTO ieee_transactions SELECT %s,transaction_id,relative_seconds,split,features FROM ieee_stage ON CONFLICT DO NOTHING',(dataset,))
            conn.execute('INSERT INTO ieee_outcomes SELECT %s,transaction_id,is_fraud FROM ieee_stage ON CONFLICT DO NOTHING',(dataset,))
        conn.execute("INSERT INTO ml_predictions SELECT %s,transaction_id,%s,model_score,model_score >= %s FROM ieee_stage WHERE split='test' ON CONFLICT DO NOTHING",(dataset,report['model_version'],report['threshold']))
    with TigerStore().connect() as conn:
        for table in ('ieee_transactions','ieee_outcomes','ml_predictions'):
            print(table,conn.execute('SELECT count(*) FROM '+table+' WHERE dataset_key=%s',(dataset,)).fetchone()[0],flush=True)
        print('Database MiB after import:',round(conn.execute('SELECT pg_database_size(current_database())').fetchone()[0]/1024**2,1),flush=True)
    print('Import committed.',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--predictions-only',action='store_true')
    try: main(parser.parse_args().predictions_only)
    except Exception as exc:
        print('Import failed:',type(exc).__name__,'SQLSTATE:',getattr(exc,'sqlstate',None),flush=True)
        if getattr(exc,'diag',None): print(exc.diag.message_primary,flush=True)
        raise SystemExit(1)
