import copy
import json
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import numpy as np
import pandas as pd
from ml_model import ARTIFACTS,MLScorer,FEATURES,normalize,encode,fit_encoding
from train_ml import select_threshold,split_masks

class MLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scorer=MLScorer()
        cls.payload=json.loads((ARTIFACTS/'high_score-request.json').read_text(encoding='utf-8'))
    def test_score_matches_trained_model(self):
        matrix=encode(normalize(pd.DataFrame([self.payload['features']])),self.scorer.artifact['mapping'])
        expected=float(self.scorer.artifact['model'].predict_proba(matrix)[0,1])
        result=self.scorer.analyze(self.payload)
        self.assertAlmostEqual(result['risk_score'],expected*100,places=3)
        self.assertEqual(result['requires_intervention'],expected>=self.scorer.artifact['threshold'])
    def test_rejects_label_leakage_and_conversation(self):
        for key in ('isFraud','victim_answer','user_id'):
            payload=copy.deepcopy(self.payload)
            payload['features'][key]=1
            with self.assertRaises(ValueError): self.scorer.analyze(payload)
        with self.assertRaises(ValueError): self.scorer.analyze(dict(self.payload,isFraud=1))
    def test_missing_values_and_new_categories(self):
        payload=copy.deepcopy(self.payload)
        payload['features']={'TransactionAmt':2000,'ProductCD':'unseen_product'}
        result=self.scorer.analyze(payload)
        self.assertIn('DeviceType',result['missing_features'])
        self.assertIn('ProductCD',result['rare_or_unseen_categories'])
        self.assertTrue(np.isfinite(result['risk_score']))
    def test_missing_category_remains_nan(self):
        frame=normalize(pd.DataFrame([{'TransactionAmt':10,'ProductCD':'W','DeviceType':'mobile'},
                                      {'TransactionAmt':20,'ProductCD':'W','DeviceType':None}]))
        matrix=encode(frame,fit_encoding(frame))
        self.assertTrue(np.isnan(matrix[1,FEATURES.index('DeviceType')]))
    def test_invalid_amounts_and_datasets(self):
        for amount in (0,-1,True,float('inf'),float('nan'),'2000'):
            payload=copy.deepcopy(self.payload)
            payload['features']['TransactionAmt']=amount
            with self.assertRaises(ValueError): self.scorer.analyze(payload)
        with self.assertRaises(ValueError): self.scorer.analyze(dict(self.payload,dataset='bank_transfer'))
    def test_temporal_split_keeps_ties_together(self):
        data=pd.DataFrame({'TransactionDT':np.repeat(np.arange(20),3)})
        masks=split_masks(data)
        self.assertLess(data.loc[masks['train'],'TransactionDT'].max(),data.loc[masks['validation'],'TransactionDT'].min())
        self.assertLess(data.loc[masks['validation'],'TransactionDT'].max(),data.loc[masks['test'],'TransactionDT'].min())
    def test_threshold_obeys_validation_budget(self):
        labels=np.array([0]*100+[1]*10)
        scores=np.linspace(.001,.9,110)
        threshold=select_threshold(labels,scores)
        self.assertLessEqual(np.mean(scores[labels==0]>=threshold),.02)
    def test_sensitivity_recomputes_model(self):
        result=self.scorer.analyze(self.payload)
        matrix=encode(normalize(pd.DataFrame([self.payload['features']])),self.scorer.artifact['mapping'])
        base=self.scorer.artifact['model'].predict_proba(matrix)[0,1]
        for effect in result['feature_sensitivities']:
            index=FEATURES.index(effect['feature'])
            changed=matrix.copy()
            changed[0,index]=self.scorer.artifact['reference'][index]
            expected=base-self.scorer.artifact['model'].predict_proba(changed)[0,1]
            self.assertAlmostEqual(expected,effect['score_change_on_reference_replacement'],places=6)
    def test_http_ml_route(self):
        from api import make_server
        from ml_service import MLService
        server=make_server(0)
        server.ml_service=MLService(persist=False)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            endpoint=f'http://127.0.0.1:{server.server_port}/ml/analyze'
            with urlopen(Request(endpoint,data=json.dumps(self.payload).encode(),headers={'Content-Type':'application/json'}),timeout=20) as response:
                result=json.load(response)
                self.assertIn('feature_sensitivities',result)
                self.assertFalse(result['persisted'])
            invalid=copy.deepcopy(self.payload)
            invalid['features']['isFraud']=1
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(endpoint,data=json.dumps(invalid).encode()),timeout=20)
            self.assertEqual(caught.exception.code,400)
        finally:
            server.shutdown(); server.server_close(); thread.join()

if __name__=='__main__': unittest.main()
