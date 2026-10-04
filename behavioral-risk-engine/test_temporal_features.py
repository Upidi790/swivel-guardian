import unittest
import pandas as pd
from temporal_features import transform, ANCHORS, NUMERIC, CATEGORICAL

class TemporalTests(unittest.TestCase):
    def sample(self):
        return {'TransactionDT':864000,'TransactionAmt':12.34,'card1':'a','addr1':'b','P_emaildomain':'c',**{c:3.0 for c in ANCHORS}}
    def test_anchor_stable_when_clock_and_elapsed_days_advance(self):
        first=self.sample();later=dict(first,TransactionDT=950400,**{c:4.0 for c in ANCHORS})
        x=transform(pd.DataFrame([first,later]))
        self.assertEqual(x.D1_anchor.iloc[0],x.D1_anchor.iloc[1])
        self.assertEqual(x.card_address_d1_proxy.iloc[0],x.card_address_d1_proxy.iloc[1])
        self.assertEqual(x.amount_cents.iloc[0],34)
    def test_future_rows_and_labels_do_not_change_features(self):
        first=self.sample();future=dict(first,TransactionDT=9999999,TransactionAmt=999999)
        alone=transform(pd.DataFrame([first]))
        batch=transform(pd.DataFrame([dict(first,isFraud=1),dict(future,isFraud=0)]))
        pd.testing.assert_series_equal(alone[NUMERIC+CATEGORICAL].iloc[0],batch[NUMERIC+CATEGORICAL].iloc[0])
    def test_missing_elapsed_time_supported(self):
        x=transform(pd.DataFrame([dict(self.sample(),D1=None)]))
        self.assertTrue(pd.isna(x.D1_anchor.iloc[0]))
        self.assertFalse(pd.isna(x.card_address_d1_proxy.iloc[0]))

if __name__=='__main__':unittest.main()
