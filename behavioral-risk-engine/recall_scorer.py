"""Experimental candidate with separate balanced and high-recall screening signals."""
from benchmark_scorer import BenchmarkScorer
from ml_model import ARTIFACTS

class RecallScorer(BenchmarkScorer):
    def __init__(self):
        super().__init__(ARTIFACTS/'recall-selected'/'selected-model.joblib')

    def analyze(self,payload):
        result=super().analyze(payload)
        threshold=self.artifact['thresholds']['recall95']
        result['experimental']=True
        result['screening_requires_interview']=result['model_score']>=threshold
        result['screening_threshold']=100*threshold
        result['screening_policy']='95% recall target on validation; future recall is not guaranteed. Review measured false-positive rate before use.'
        result['agent_guidance']='Experimental screening signal only. Combine with separately collected answers; do not automatically block payments or assume a low score proves safety.'
        return result
