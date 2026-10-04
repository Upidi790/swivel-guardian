"""Data-integrity and inference checks for completed balancing experiments."""
import json, unittest
import numpy as np
import pandas as pd
from ml_model import ARTIFACTS
from train_ml import split_masks
from benchmark_scorer import BenchmarkScorer

OUT=ARTIFACTS/'balance-v6'

@unittest.skipUnless((OUT/'comparison.json').exists(),'Run balancing experiment first')
class BalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=json.loads((OUT/'comparison.json').read_text())
        cls.data=pd.read_csv(ARTIFACTS/'ieee-selected.csv.gz',usecols=['TransactionDT','isFraud'])
        cls.masks=split_masks(cls.data)
    def test_original_evaluation_distribution_preserved(self):
        labels=self.data.isFraud.to_numpy()
        for result in self.report['candidates'].values():
            for metric in result['test'].values():
                self.assertEqual(metric['rows'],int(self.masks['test'].sum()))
                self.assertEqual(metric['fraud_rows'],int(labels[self.masks['test']].sum()))
    def test_all_real_training_fraud_retained(self):
        fraud=int(self.data.loc[self.masks['train'],'isFraud'].sum())
        candidates=self.report['candidates']
        for name in ('balanced_loss','undersampled_4to1','recent_weighted'):
            self.assertEqual(candidates[name]['training_fraud_rows'],fraud)
        self.assertEqual(candidates['undersampled_4to1']['training_rows'],5*fraud)
        expected=(int(self.masks['train'].sum())-fraud)/fraud
        self.assertAlmostEqual(candidates['balanced_loss']['fraud_loss_weight'],expected)
    def test_selection_uses_validation(self):
        winner=min(self.report['candidates'],key=lambda n:self.report['candidates'][n]['validation']['recall90']['false_positive_rate'])
        self.assertEqual(winner,self.report['winner'])
    def test_selected_model_roundtrip(self):
        scorer=BenchmarkScorer(OUT/'selected-model.joblib')
        scores=np.load(OUT/(self.report['winner']+'-scores.npy'))[self.masks['test']]
        for label,expected in [('high_score',scores.max()),('low_score',scores.min())]:
            request=json.loads((OUT/(label+'-request.json')).read_text())
            self.assertAlmostEqual(scorer.analyze(request)['model_score'],expected,places=7)

if __name__=='__main__':unittest.main()
