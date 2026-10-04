import copy
import json
import math
import unittest
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import numpy as np
import pandas as pd
from benchmark_scorer import BenchmarkScorer, OUT

@unittest.skipUnless((OUT/'selected-model.joblib').exists(),'Run the benchmark first')
class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scorer=BenchmarkScorer()
        cls.payload=json.loads((OUT/'high_score-request.json').read_text(encoding='utf-8'))
    def test_inference_matches_benchmark(self):
        records={}
        for name in ('high_score','low_score'):
            payload=json.loads((OUT/(name+'-request.json')).read_text(encoding='utf-8'))
            records[int(payload['transaction_id'])]=(payload,self.scorer.analyze(payload))
        matched=0
        for chunk in pd.read_csv(OUT/'predictions.csv.gz',chunksize=20000):
            for row in chunk[chunk.transaction_id.isin(records)].itertuples():
                result=records[row.transaction_id][1]
                self.assertAlmostEqual(result['model_score'],row.model_score,places=7)
                matched+=1
        self.assertEqual(matched,2)
    def test_explanations_reconstruct_score(self):
        result=self.scorer.analyze(self.payload)
        reconstructed=1/(1+math.exp(-result['explanation_total_log_odds']))
        self.assertAlmostEqual(reconstructed,result['model_score'],places=7)
    def test_rejects_outcome_and_incomplete_schema(self):
        for key in ('isFraud','TransactionID','victim_answer'):
            p=copy.deepcopy(self.payload);p['features'][key]=1
            with self.assertRaises(ValueError):self.scorer.analyze(p)
        p=copy.deepcopy(self.payload);p['features'].pop('dist1')
        with self.assertRaises(ValueError):self.scorer.analyze(p)
    def test_explicit_missing_and_unknown_categories(self):
        p=copy.deepcopy(self.payload)
        p['features']['DeviceType']='previously_unseen_device'
        p['features']['dist1']=None
        result=self.scorer.analyze(p)
        self.assertTrue(np.isfinite(result['model_score']))
        self.assertIn('dist1',result['missing_features'])
    def test_invalid_input_values(self):
        for value in (float('nan'),float('inf'),True,0,-1):
            p=copy.deepcopy(self.payload);p['features']['TransactionAmt']=value
            with self.assertRaises(ValueError):self.scorer.analyze(p)
    def test_winner_selected_by_validation(self):
        report=json.loads((OUT/'comparison.json').read_text(encoding='utf-8'))
        selected=max((n for n,r in report['candidates'].items() if r['eligible']),key=lambda n:report['candidates'][n]['selection_max_f1']['average_precision'])
        self.assertEqual(report['winner'],selected)
        self.assertEqual(self.scorer.artifact['threshold'],report['candidates'][selected]['threshold_max_f1'])
    def test_v3_http_contract(self):
        from api import make_server
        from ml_service import MLService
        server=make_server(0)
        server.benchmark_ml_service=MLService(persist=False,scorer=self.scorer)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        endpoint=f'http://127.0.0.1:{server.server_port}/ml/v3/analyze'
        try:
            with urlopen(Request(endpoint,data=json.dumps(self.payload).encode(),headers={'Content-Type':'application/json'}),timeout=30) as response:
                result=json.load(response)
                self.assertEqual(result['model_version'],self.scorer.artifact['model_version'])
                self.assertIn('feature_contributions',result)
            invalid=copy.deepcopy(self.payload);invalid['features']['isFraud']=1
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(endpoint,data=json.dumps(invalid).encode()),timeout=30)
            self.assertEqual(error.exception.code,400)
        finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
