"""Generate repeatable synthetic histories and evaluate frozen holdout cases."""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from engine import analyze_transaction

ROOT = Path(__file__).parent

def generate():
    rng = random.Random(7241)
    now = datetime(2026, 10, 3, 18, tzinfo=timezone.utc)
    users, history, cases = [], [], []
    for i in range(30):
        uid = f'user_{i:03d}'
        region = ['San Antonio', 'Chicago', 'Phoenix'][i % 3]
        recipients = [f'{uid}_payee_{j}' for j in range(5)]
        users.append({'user_id': uid, 'display_name': f'Demo Customer {i + 1}',
                      'known_recipients': recipients, 'trusted_recipients': recipients[:2],
                      'known_devices': [f'{uid}_phone'], 'normal_locations': [region],
                      'account_opened': (now - timedelta(days=400)).isoformat()})
        scale = rng.uniform(70, 250)
        for j in range(100):
            history.append({'transaction_id': f'{uid}_hist_{j}', 'user_id': uid,
                            'timestamp': (now - timedelta(hours=(100 - j) * 18)).isoformat(),
                            'amount': round(rng.lognormvariate(0, .35) * scale, 2),
                            'currency': 'USD', 'recipient_id': recipients[j % 5],
                            'recipient_type': ['family', 'utility', 'merchant', 'family', 'rent'][j % 5],
                            'recipient_first_seen': (now - timedelta(days=300)).isoformat(),
                            'device_id': f'{uid}_phone', 'ip_region': region,
                            'transaction_type': 'transfer', 'successful': True})
    labels = ['normal'] * 50 + ['unusual_legitimate'] * 20 + ['scam_like'] * 20
    for k, label in enumerate(labels):
        user = users[k % 30]
        base = next(t for t in reversed(history) if t['user_id'] == user['user_id'])
        tx = dict(base, transaction_id=f'case_{k:03d}', timestamp=now.isoformat(), successful=False)
        if label != 'normal':
            tx.update(amount=round(base['amount'] * rng.uniform(6, 15), 2),
                      recipient_id=f'new_payee_{k}', recipient_first_seen=(now - timedelta(minutes=2)).isoformat())
            if k % 3 == 0:
                tx.update(device_id='new_phone', ip_region='New region')
        if label == 'scam_like' and k % 4 == 0:
            # Deliberate hard negatives for anomaly detection: scams can look normal.
            tx = dict(base, transaction_id=f'case_{k:03d}', timestamp=now.isoformat(), successful=False)
        story = ('Routine payment' if label == 'normal' else
                 ['First rent payment', 'Laptop purchase', 'Tuition', 'New family recipient', 'Vacation'][k % 5]
                 if label == 'unusual_legitimate' else
                 ['Bank impersonation: move money to protect it', 'Government impersonation', 'Fake computer support'][k % 3])
        cases.append({'transaction': tx, 'scenario_label': label, 'scenario': story,
                      'behaviorally_unusual': label != 'normal' and not (label == 'scam_like' and k % 4 == 0)})
    return {'users': users, 'transactions': history, 'cases': cases}

def metrics(truth, predicted):
    tp = sum(t and p for t, p in zip(truth, predicted))
    fp = sum(not t and p for t, p in zip(truth, predicted))
    fn = sum(t and not p for t, p in zip(truth, predicted))
    tn = len(truth) - tp - fp - fn
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {'tp': tp, 'fp': fp, 'tn': tn, 'fn': fn, 'precision': precision,
            'recall': recall, 'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0}

def evaluate(data):
    predictions = [analyze_transaction(c['transaction']['user_id'], c['transaction'], data['transactions'])['requires_intervention'] for c in data['cases']]
    return {'behavioral_triage': metrics([c['behaviorally_unusual'] for c in data['cases']], predictions),
            'scam_label_diagnostic_only': metrics([c['scenario_label'] == 'scam_like' for c in data['cases']], predictions),
            'interventions_by_group': {label: {'count': sum(c['scenario_label'] == label for c in data['cases']),
                'triggered': sum(p for c, p in zip(data['cases'], predictions) if c['scenario_label'] == label)}
                for label in ('normal', 'unusual_legitimate', 'scam_like')},
            'limitation': 'Hand-designed synthetic holdouts demonstrate behavior, not real-world detection accuracy. No scenario labels or narratives are passed to the engine.'}

if __name__ == '__main__':
    data = generate()
    (ROOT / 'data.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    report = evaluate(data)
    (ROOT / 'evaluation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    example = data['cases'][50]['transaction']
    (ROOT / 'example-request.json').write_text(json.dumps(example, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
