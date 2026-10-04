"""IEEE-CIS transaction-fraud benchmark; not an APP scam detector."""
from pathlib import Path
import math
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
import joblib
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / 'ml_artifacts'
NUMERIC = ['TransactionAmt', 'dist1', 'dist2']
CATEGORICAL = ['ProductCD', 'card1', 'card2', 'card3', 'card4', 'card5', 'card6',
               'addr1', 'addr2', 'P_emaildomain', 'R_emaildomain', 'DeviceType', 'DeviceInfo']
FEATURES = NUMERIC + CATEGORICAL

def normalize(frame):
    result = frame.reindex(columns=FEATURES).copy()
    for col in NUMERIC:
        result[col] = pd.to_numeric(result[col], errors='coerce').astype(float)
    for col in CATEGORICAL:
        result[col] = pd.Series([None if pd.isna(v) else str(v) for v in result[col]], index=result.index, dtype=object)
    return result

def fit_encoding(frame):
    # Top categories learned only from training data. Codes are marked categorical
    # to the model: card codes are neither customer ids nor ordered quantities.
    return {col: {value: i for i, value in enumerate(frame[col].dropna().value_counts().head(250).index)}
            for col in CATEGORICAL}

def encode(frame, mapping):
    matrix = np.full((len(frame), len(FEATURES)), np.nan, dtype=np.float64)
    for i, col in enumerate(NUMERIC):
        values = frame[col].to_numpy(dtype=float)
        matrix[:, i] = np.log1p(np.maximum(values, 0))
    for i, col in enumerate(CATEGORICAL, start=len(NUMERIC)):
        matrix[:, i] = frame[col].map(lambda v: np.nan if pd.isna(v) else mapping[col].get(v, 250)).to_numpy(dtype=float)
    return matrix

def validate_request(payload):
    if not isinstance(payload, dict) or payload.get('dataset') != 'ieee_cis':
        raise ValueError('dataset must be ieee_cis')
    if set(payload) - {'dataset', 'transaction_id', 'features'}:
        raise ValueError('Only dataset, transaction_id, and features are accepted')
    fields = payload.get('features')
    if not isinstance(fields, dict):
        raise ValueError('features must be an object')
    unknown = set(fields) - set(FEATURES)
    if unknown:
        raise ValueError('Unknown feature fields (outcomes and interview answers are not model inputs)')
    amount = fields.get('TransactionAmt')
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount <= 0:
        raise ValueError('TransactionAmt must be finite and positive')
    if not isinstance(fields.get('ProductCD'), str) or not fields['ProductCD']:
        raise ValueError('ProductCD is required; generic bank transfers cannot be scored by this benchmark')
    for col in ('dist1', 'dist2'):
        value = fields.get(col)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError(col + ' must be null or finite and nonnegative')
    for col in CATEGORICAL:
        value = fields.get(col)
        if value is not None and (not isinstance(value, str) or len(value) > 512):
            raise ValueError(col + ' must be a string or null')
    txid = payload.get('transaction_id')
    if not isinstance(txid, str) or not txid or len(txid) > 128:
        raise ValueError('transaction_id must be a nonempty string of at most 128 characters')
    return normalize(pd.DataFrame([fields]))

class MLScorer:
    def __init__(self, path=None):
        # Load only artifacts trained locally by train_ml.py; joblib files can execute code.
        self.artifact = joblib.load(path or ARTIFACTS / 'model.joblib')
    def analyze(self, payload):
        frame = validate_request(payload)
        artifact = self.artifact
        matrix = encode(frame, artifact['mapping'])
        score = float(artifact['model'].predict_proba(matrix)[0, 1])
        # Finite-difference model sensitivity, not causal explanations or SHAP.
        variants = np.repeat(matrix, len(FEATURES), axis=0)
        for i in range(len(FEATURES)):
            variants[i, i] = artifact['reference'][i]
        replaced = artifact['model'].predict_proba(variants)[:, 1]
        effects = [{'feature': col, 'score_change_on_reference_replacement': round(float(score - replaced[i]), 6),
                    'observed': payload['features'].get(col),
                    'reference': artifact['reference_raw'][col]}
                   for i, col in enumerate(FEATURES)]
        effects.sort(key=lambda e: abs(e['score_change_on_reference_replacement']), reverse=True)
        threshold = artifact['threshold']
        warnings = ['Trained on IEEE-CIS online-payment fraud, not validated for authorized-transfer scams.',
                    'No verified customer/payee history is available; this is not a personalized behavioral baseline.',
                    'Model score is not a calibrated probability of social engineering.']
        missing = [col for col in FEATURES if payload['features'].get(col) is None]
        unknown = [col for col in CATEGORICAL if payload['features'].get(col) is not None and payload['features'][col] not in artifact['mapping'][col]]
        return {'transaction_id': payload['transaction_id'], 'dataset': 'ieee_cis', 'model_version': artifact['model_version'],
                'model_type': 'HistGradientBoostingClassifier', 'risk_score': round(score * 100, 3),
                'score_kind': 'uncalibrated_dataset_fraud_model_output',
                'intervention_threshold': round(threshold * 100, 6),
                'requires_intervention': bool(score >= threshold),
                'decision': 'INVESTIGATE' if score >= threshold else 'NO_MODEL_TRIGGER',
                'feature_sensitivities': effects[:5],
                'explanation_method': 'Replace one feature with a training reference, recompute score. Positive change means the original value increased score relative to that reference. Not causation; correlated or implausible replacements can mislead.',
                'missing_features': missing, 'rare_or_unseen_categories': unknown,
                'limitations': warnings,
                'agent_guidance': 'Use as one triage signal alongside the customer interview. Do not assert a scam, invent customer history, or claim funds are held. Escalation and payment actions require separate bank policy.'}
