"""Explainable behavioral triage. Scores are NOT fraud probabilities."""
from datetime import datetime, timedelta
import math
import statistics as stats

VERSION = 'rules-1.0'

def timestamp(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.utcoffset() is None:
        raise ValueError('Timestamps must include a timezone')
    return dt

def validate(tx):
    for key in ('transaction_id', 'user_id', 'recipient_id', 'transaction_type', 'currency'):
        if not isinstance(tx.get(key), str) or not tx[key].strip():
            raise ValueError(f'{key} must be a nonempty string')
    amount = tx.get('amount')
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
        raise ValueError('amount must be a finite positive number')
    now = timestamp(tx['timestamp'])
    if tx.get('recipient_first_seen') and timestamp(tx['recipient_first_seen']) > now:
        raise ValueError('recipient_first_seen cannot be in the future')
    return now

def percentile(values, q):
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)

def analyze_transaction(user_id, transaction, history):
    now = validate(transaction)
    if user_id != transaction['user_id']:
        raise ValueError('user_id mismatch')
    # Strictly prior events only. Exclude the current id, other users, failed
    # payments and unlike currencies/rails from the amount baseline.
    prior = [t for t in history if t['user_id'] == user_id
             and t['transaction_id'] != transaction['transaction_id']
             and timestamp(t['timestamp']) < now]
    settled = [t for t in prior if t.get('successful') is True]
    comparable = [t for t in settled if t['currency'] == transaction['currency']
                  and t['transaction_type'] == transaction['transaction_type']
                  and timestamp(t['timestamp']) >= now - timedelta(days=90)]
    amounts = [t['amount'] for t in comparable]
    sufficient = len(amounts) >= 20
    median = stats.median(amounts) if amounts else None
    p95 = percentile(amounts, .95) if amounts else None
    mean = stats.mean(amounts) if amounts else None
    sd = stats.pstdev(amounts) if len(amounts) > 1 else 0
    recipient_count = sum(t['recipient_id'] == transaction['recipient_id'] for t in settled)
    first_seen = transaction.get('recipient_first_seen')
    age_minutes = (now - timestamp(first_seen)).total_seconds() / 60 if first_seen else None
    device, region = transaction.get('device_id'), transaction.get('ip_region')
    known_devices = {t.get('device_id') for t in settled if t.get('device_id')}
    known_regions = {t.get('ip_region') for t in settled if t.get('ip_region')}
    recent = sum(timestamp(t['timestamp']) >= now - timedelta(hours=1) for t in prior)
    # Typical prior one-hour count, sampled at historical event times.
    ordered_times = sorted(timestamp(t['timestamp']) for t in prior
                           if timestamp(t['timestamp']) >= now - timedelta(days=90))
    counts, left = [], 0
    for i, moment in enumerate(ordered_times):
        while ordered_times[left] < moment - timedelta(hours=1):
            left += 1
        counts.append(i - left)
    frequency_limit = max(3, math.ceil(percentile(counts, .95)) + 1) if counts else 3
    features = {
        'amount_percentile': sum(a <= transaction['amount'] for a in amounts) / len(amounts) if amounts else None,
        'amount_z_score': (transaction['amount'] - mean) / sd if sd else None,
        'amount_vs_median': transaction['amount'] / median if median else None,
        'recipient_novelty': recipient_count == 0,
        'days_since_recipient_first_seen': age_minutes / 1440 if age_minutes is not None else None,
        'previous_transactions_to_recipient': recipient_count,
        'device_novelty': device not in known_devices if device and known_devices else None,
        'location_novelty': region not in known_regions if region and known_regions else None,
        'transactions_in_previous_hour': recent,
        'frequency_trigger_count': frequency_limit,
        'time_since_previous_transaction_seconds': (now - max(timestamp(t['timestamp']) for t in prior)).total_seconds() if prior else None,
        'unusual_time_of_day': None,  # Requires the customer's timezone; never assume UTC is local.
    }
    signals = []
    def add(condition, kind, points, explanation):
        if condition:
            signals.append({'type': kind, 'points': points, 'severity': points / 25, 'explanation': explanation})
    add(recipient_count == 0, 'NEW_RECIPIENT', 25, 'No successful prior payment to this recipient is available.')
    add(sufficient and transaction['amount'] > p95, 'AMOUNT_ANOMALY', 25,
        f'Amount {transaction["amount"]:.2f} exceeds the comparable 90-day 95th percentile {p95 or 0:.2f}.')
    add(recipient_count == 0 and age_minutes is not None and age_minutes < 30,
        'RECENT_RECIPIENT', 15, 'This new recipient was added less than 30 minutes before payment.')
    add(features['device_novelty'] is True, 'NEW_DEVICE', 15, 'Device is absent from successful prior payments.')
    add(features['location_novelty'] is True, 'UNUSUAL_REGION', 10, 'Approximate IP region differs from prior payments; travel or VPN use can explain this.')
    add(recent >= frequency_limit, 'PAYMENT_FREQUENCY', 10, 'Recent payment attempts exceed the historical frequency threshold.')
    score = sum(s['points'] for s in signals)
    warnings = []
    if not sufficient:
        warnings.append('Fewer than 20 comparable payments; amount anomaly scoring is disabled.')
    for key in ('device_id', 'ip_region', 'recipient_first_seen'):
        if not transaction.get(key):
            warnings.append(f'{key} unavailable; missing data does not imply normal behavior.')
    return {'transaction_id': transaction['transaction_id'], 'model_version': VERSION,
            'risk_score': score, 'risk_level': 'HIGH' if score >= 65 else 'MEDIUM' if score >= 40 else 'LOW',
            'requires_intervention': score >= 40, 'decision': 'INVESTIGATE' if score >= 40 else 'NO_BEHAVIORAL_TRIGGER',
            'signals': signals, 'features': features, 'data_quality_warnings': warnings,
            'baseline': {'history_count': len(amounts), 'median_transfer': median, 'p95_transfer': p95,
                         'previous_recipient_transactions': recipient_count},
            'notice': 'Behavioral anomaly score, not a fraud probability or payment authorization.'}
