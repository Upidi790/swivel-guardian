"""Stateless features from the current transaction only; no labels or future rows."""
import numpy as np
import pandas as pd

ANCHORS=[f'D{i}' for i in (1,2,3,4,5,6,7,8,10,11,12,13,14,15)]
NUMERIC=['amount_cents','relative_hour']+[c+'_anchor' for c in ANCHORS]
CATEGORICAL=['card_address_email','card_address_d1_proxy']

def transform(frame):
    result=frame.copy()
    days=pd.to_numeric(frame['TransactionDT'])/86400
    result['amount_cents']=(pd.to_numeric(frame['TransactionAmt'])*100).round()%100
    result['relative_hour']=(pd.to_numeric(frame['TransactionDT'])%86400)/3600
    for col in ANCHORS:
        result[col+'_anchor']=pd.to_numeric(frame[col])-days
    def text(col):return frame[col].fillna('__MISSING__').astype(str)
    result['card_address_email']=text('card1')+'|'+text('addr1')+'|'+text('P_emaildomain')
    # An anonymous grouping proxy, never a verified person or account identity.
    start=np.floor(days-pd.to_numeric(frame['D1'])).astype('Int64').astype('string').fillna('__MISSING__')
    result['card_address_d1_proxy']=text('card1')+'|'+text('addr1')+'|'+start
    return result
