import copy
import json
import math
import unittest
import numpy as np
from benchmark_scorer import BenchmarkScorer
from ml_model import ARTIFACTS
from improve_recall import recall_threshold

OUT=ARTIFACTS/'recall-v4'

class ThresholdTests(unittest.TestCase):
    def test_recall_threshold_handles_tied_scores(self):
        y=np.array([1,0,1,0,1,0,1,0,1,0])
        p=np.array([.9,.8,.8,.7,.6,.5,.4,.3,.2,.1])
        threshold=recall_threshold(y,p,.8)
        self.assertEqual(threshold,.4)
        self.assertGreaterEqual(np.sum((p>=threshold)&(y==1))/sum(y),.8)

@unittest.skipUnless((OUT/'comparison.json').exists(),'Train expanded-feature candidates first')
class RecallArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((OUT/'comparison.json').read_text())
        cls.scorer=BenchmarkScorer(OUT/'selected-model.joblib')
        cls.payload=json.loads((OUT/'high_score-request.json').read_text())
    def test_winner_uses_validation_only(self):
        candidates=self.report['candidates']
        winner=min(candidates,key=lambda n:candidates[n]['validation']['recall90']['false_positive_rate'])
        self.assertEqual(winner,self.report['winner'])
        for candidate in candidates.values():
            self.assertGreaterEqual(candidate['validation']['recall90']['recall'],.90)
            self.assertGreaterEqual(candidate['validation']['recall95']['recall'],.95)
    def test_batch_and_online_predictions_match(self):
        scores=np.load(OUT/(self.report['winner']+'-scores.npy'))
        # Selection starts before the final 15%; final test is the last 88,581 rows.
        test=scores[-self.report['protocol']['test_rows']:]
        for name,expected in [('high_score',np.max(test)),('low_score',np.min(test))]:
            payload=json.loads((OUT/(name+'-request.json')).read_text())
            result=self.scorer.analyze(payload)
            self.assertAlmostEqual(result['model_score'],expected,places=7)
            self.assertAlmostEqual(1/(1+math.exp(-result['explanation_total_log_odds'])),expected,places=7)
    def test_all_v_groups_present_without_outcomes(self):
        fields=self.scorer.artifact['required_features']
        self.assertTrue(all('V'+str(i) in fields for i in range(1,340)))
        self.assertNotIn('isFraud',fields)
        self.assertNotIn('TransactionID',fields)
        p=copy.deepcopy(self.payload);p['features']['isFraud']=1
        with self.assertRaises(ValueError):self.scorer.analyze(p)
        p=copy.deepcopy(self.payload);del p['features']['V258']
        with self.assertRaises(ValueError):self.scorer.analyze(p)

if __name__=='__main__':unittest.main()
