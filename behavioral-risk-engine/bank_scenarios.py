"""Explicit simulations, separate from Sparkov training and measured fraud results."""
import json
from datetime import datetime,timedelta
from engine import analyze_transaction
from sparkov_service import OUT

def main():
    now=datetime(2026,1,1,12);history=[]
    for i in range(60):
        history.append({'transaction_id':f'sim-history-{i}','user_id':'sim-user','timestamp':(now-timedelta(days=60-i)).isoformat()+'Z',
          'amount':100.+i%10*5,'recipient_id':'known-family','transaction_type':'bank_transfer','currency':'USD',
          'device_id':'usual-phone','ip_region':'home-region','successful':True})
    base={'user_id':'sim-user','timestamp':now.isoformat()+'Z','amount':120.,'recipient_id':'known-family',
      'transaction_type':'bank_transfer','currency':'USD','device_id':'usual-phone','ip_region':'home-region',
      'recipient_first_seen':(now-timedelta(days=60)).isoformat()+'Z'}
    cases=[]
    for i in range(50):cases.append(('normal',dict(base,transaction_id=f'sim-normal-{i}',amount=100+i%10*5),'Routine family payment.'))
    for i in range(20):
        tx=dict(base,amount=2000.)
        if i<10:tx.update(recipient_id='new-payee',recipient_first_seen=(now-timedelta(minutes=2)).isoformat()+'Z')
        if 5<=i<10:tx.update(device_id='new-phone',ip_region='travel-region')
        # Identical observable behavior, different contexts withheld from the engine.
        cases.append(('unusual_legitimate',dict(tx,transaction_id=f'sim-legitimate-{i}'),'A planned large payment that the customer independently verified.'))
        cases.append(('scam_like',dict(tx,transaction_id=f'sim-scam-{i}'),'Someone pressured the customer to send money and keep the reason secret.'))
    results=[]
    for label,tx,context in cases:
        result=analyze_transaction(tx['user_id'],tx,history)
        results.append({'scenario_label':label,'simulated_victim_context_not_sent_to_engine':context,'transaction':tx,'result':result})
    counts={label:{'cases':sum(r['scenario_label']==label for r in results),
                   'investigation_triggers':sum(r['scenario_label']==label and r['result']['requires_intervention'] for r in results)} for label in ('normal','unusual_legitimate','scam_like')}
    artifact={'provenance':'Hand-authored simulated bank-transfer scenarios. Not real customers, not Sparkov labels, not real-world performance evidence.',
              'purpose':'Test feature handling and show that behavior-identical legitimate/scam cases require interview context.',
              'history':history,'summary':counts,'cases':results}
    (OUT/'simulated-bank-scenarios.json').write_text(json.dumps(artifact,indent=2))
    print(json.dumps(counts,indent=2))

if __name__=='__main__':main()
