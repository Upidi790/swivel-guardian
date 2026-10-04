import copy,json,unittest
from datetime import datetime,timedelta
import joblib,pandas as pd
from behavior_features import from_history,CustomerState,validate
from sparkov_service import SparkovService,OUT

def payment(i=0,**changes):
    tx={'transaction_id':str(i),'user_id':'customer','timestamp':(datetime(2020,1,1,12)+timedelta(days=i)).isoformat(),
      'amount':100.,'merchant_id':'usual','category':'grocery','home_latitude':30.,'home_longitude':-98.,'merchant_latitude':30.1,'merchant_longitude':-98.1}
    tx.update(changes);return tx

class CausalityTests(unittest.TestCase):
    def test_future_current_simultaneous_and_other_customers_excluded(self):
        history=[payment(i,amount=100+i) for i in range(25)];tx=payment(26,amount=1000)
        expected=from_history(tx,history)
        pollution=[tx,payment(26,transaction_id='simultaneous',amount=1e8),payment(27,amount=1e9),payment(24,user_id='other',amount=1e10)]
        self.assertEqual(expected,from_history(tx,history+pollution))
    def test_prior_only_merchant_count_and_window(self):
        history=[payment(i) for i in range(25)];tx=payment(26,merchant_id='new')
        f,b,_=from_history(tx,history+[payment(27,merchant_id='new')])
        self.assertEqual(f['previous_merchant_transactions'],0);self.assertEqual(b['median_amount'],100)
        f,b,_=from_history(payment(200),history)
        self.assertEqual(b['history_count'],0);self.assertEqual(f['previous_merchant_transactions'],25)
    def test_labels_do_not_change_history_features(self):
        history=[payment(i) for i in range(25)];tx=payment(26)
        self.assertEqual(from_history(tx,history),from_history(tx,[dict(r,is_fraud=i%2) for i,r in enumerate(history)]))
        with self.assertRaises(ValueError):validate(dict(tx,is_fraud=1))
    def test_same_timestamp_state_rejected_until_batch_scored(self):
        state=CustomerState();state.observe(payment(0))
        with self.assertRaises(ValueError):state.describe(payment(0,transaction_id='second'))
    def test_bad_numbers_and_clock_rejected(self):
        for changes in ({'amount':True},{'amount':float('nan')},{'merchant_latitude':100},{'timestamp':'2020-01-01T00:00:00Z'}):
            with self.assertRaises(ValueError):validate(payment(**changes))
    def test_category_baseline_is_personal_and_past_only(self):
        history=[payment(i,amount=100 if i<10 else 1000,category='grocery' if i<10 else 'electronics') for i in range(30)]
        f,b,_=from_history(payment(31,amount=500,category='grocery'),history)
        self.assertEqual(b['category_median_amount'],100)
        self.assertEqual(f['amount_vs_category_median'],5)
        self.assertEqual(f['category_history_count'],10)

@unittest.skipUnless((OUT/'model.joblib').exists(),'Build Sparkov artifacts first')
class ArtifactTests(unittest.TestCase):
    def test_online_batch_parity(self):
        service=SparkovService();evaluation=pd.read_csv(OUT/'evaluation.csv.gz').set_index('transaction_id')
        for name in ('high_score','low_score'):
            tx=json.loads((OUT/(name+'-request.json')).read_text());r=service.analyze(tx)
            self.assertAlmostEqual(r['model_score'],evaluation.loc[tx['transaction_id'],'score'],places=8)
    def test_cold_start_abstains(self):
        r=SparkovService().score(payment(),[])
        self.assertEqual(r['decision'],'INSUFFICIENT_HISTORY');self.assertIsNone(r['requires_intervention'])
    def test_simulated_context_is_not_a_transaction_feature(self):
        cases=json.loads((OUT/'simulated-bank-scenarios.json').read_text())['cases']
        for i in range(20):
            legit=next(c for c in cases if c['transaction']['transaction_id']==f'sim-legitimate-{i}')
            scam=next(c for c in cases if c['transaction']['transaction_id']==f'sim-scam-{i}')
            self.assertEqual(legit['result']['risk_score'],scam['result']['risk_score'])
            self.assertEqual(legit['result']['features'],scam['result']['features'])

if __name__=='__main__':unittest.main()
