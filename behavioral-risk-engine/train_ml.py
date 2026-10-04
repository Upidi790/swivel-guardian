"""Train from the user's original Kaggle ZIP; no generated customer identities."""
import argparse
import hashlib
import json
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
import warnings
import zipfile
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve, confusion_matrix, precision_score, recall_score, f1_score, brier_score_loss
from ml_model import ARTIFACTS, FEATURES, NUMERIC, CATEGORICAL, normalize, fit_encoding, encode

def read_data(path):
    with zipfile.ZipFile(path) as archive:
        with archive.open('train_transaction.csv') as stream:
            tx = pd.read_csv(stream, usecols=['TransactionID','TransactionDT','isFraud'] + NUMERIC + CATEGORICAL[:-2],
                             dtype={col: 'string' for col in CATEGORICAL[:-2]})
        with archive.open('train_identity.csv') as stream:
            identity = pd.read_csv(stream, usecols=['TransactionID','DeviceType','DeviceInfo'], dtype={'DeviceType':'string','DeviceInfo':'string'})
    if tx.TransactionID.duplicated().any() or identity.TransactionID.duplicated().any():
        raise ValueError('Duplicate transaction identifiers')
    data = tx.merge(identity, how='left', on='TransactionID', validate='one_to_one').sort_values(['TransactionDT','TransactionID']).reset_index(drop=True)
    if not data.isFraud.isin([0, 1]).all() or data.TransactionDT.isna().any() or (data.TransactionAmt <= 0).any():
        raise ValueError('Invalid dataset labels, times, or amounts')
    return data

def split_masks(data):
    time = data.TransactionDT.to_numpy()
    a, b = time[int(len(time) * .7)], time[int(len(time) * .85)]
    return {'train': time < a, 'validation': (time >= a) & (time < b), 'test': time >= b}

def select_threshold(labels, scores, maximum_fpr=.02):
    fpr, tpr, thresholds = roc_curve(labels, scores, drop_intermediate=False)
    feasible = np.flatnonzero((fpr <= maximum_fpr) & np.isfinite(thresholds))
    if not len(feasible):
        return 1.000001  # No feasible positive trigger on validation.
    best = feasible[np.argmax(tpr[feasible])]
    return float(thresholds[best])

def evaluate(labels, scores, threshold):
    predicted = scores >= threshold
    tn, fp, fn, tp = confusion_matrix(labels, predicted, labels=[0,1]).ravel()
    return {'rows':len(labels), 'fraud_rows':int(np.sum(labels)), 'fraud_prevalence':float(np.mean(labels)),
            'average_precision':float(average_precision_score(labels, scores)), 'roc_auc':float(roc_auc_score(labels,scores)),
            'precision':float(precision_score(labels,predicted,zero_division=0)), 'recall':float(recall_score(labels,predicted)),
            'f1':float(f1_score(labels,predicted)), 'false_positive_rate':float(fp/(fp+tn)),
            'alert_rate':float(np.mean(predicted)), 'brier_score':float(brier_score_loss(labels,scores)),
            'true_positives':int(tp),'false_positives':int(fp),'true_negatives':int(tn),'false_negatives':int(fn)}

def main(path):
    ARTIFACTS.mkdir(exist_ok=True)
    print('Reading selected IEEE-CIS columns from original ZIP...', flush=True)
    data = read_data(path)
    frame = normalize(data)
    masks = split_masks(data)
    mapping = fit_encoding(frame.loc[masks['train']])
    matrix = encode(frame, mapping)
    labels = data.isFraud.to_numpy(dtype=int)
    print('Rows by time split:',{k:int(v.sum()) for k,v in masks.items()}, flush=True)
    model = HistGradientBoostingClassifier(max_iter=150, max_leaf_nodes=15, min_samples_leaf=50,
             learning_rate=.08, l2_regularization=2.0, early_stopping=False, random_state=42,
             categorical_features=[False]*len(NUMERIC)+[True]*len(CATEGORICAL))
    print('Training gradient-boosted trees (training partition only)...', flush=True)
    model.fit(matrix[masks['train']], labels[masks['train']])
    scores = model.predict_proba(matrix)[:,1]
    threshold = select_threshold(labels[masks['validation']],scores[masks['validation']])
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''): digest.update(chunk)
    model_version = 'ieee-hgb-v2-' + digest.hexdigest()[:12]
    reference_raw = {}
    for col in FEATURES:
        vals = frame.loc[masks['train'],col].dropna()
        reference_raw[col] = float(vals.median()) if col in NUMERIC else str(vals.mode().iloc[0])
    reference = encode(normalize(pd.DataFrame([reference_raw])),mapping)[0]
    artifact = {'model':model,'mapping':mapping,'threshold':threshold,'reference':reference,
                'reference_raw':reference_raw,'model_version':model_version, 'sklearn_version':sklearn.__version__}
    joblib.dump(artifact, ARTIFACTS / 'model.joblib')
    report = {'dataset':'IEEE-CIS labeled training files', 'source_zip_sha256':digest.hexdigest(),
              'model_version':model_version,'algorithm':'HistGradientBoostingClassifier', 'features':FEATURES,
              'training_parameters':model.get_params(), 'sklearn_version':sklearn.__version__,
              'threshold':threshold, 'threshold_policy':'Maximize validation recall subject to validation false positive rate <= 2%; fixed before test evaluation. This is a demo operating point, not a bank policy.',
              'partitions':{k:{'rows':int(mask.sum()),'min_relative_seconds':int(data.loc[mask,'TransactionDT'].min()),
                                 'max_relative_seconds':int(data.loc[mask,'TransactionDT'].max())} for k,mask in masks.items()},
              'validation':evaluate(labels[masks['validation']],scores[masks['validation']],threshold),
              'test':evaluate(labels[masks['test']],scores[masks['test']],threshold),
              'limitations':['Fraud labels do not establish victim deception or APP fraud.',
                             'One temporal holdout; no verified customer-group split or external validation.',
                             'Anonymized card fields are not unique customer ids; no personalized history inferred.',
                             'Device fields may be unavailable at a real integration point; verify availability before deployment.',
                             'Scores are not calibrated for bank transfers. No population or production performance claim.',
                             'Original competition test files have no labels and are not used for reported metrics.']}
    (ARTIFACTS/'evaluation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    # Compact local copy for database import. Preserve relative time, no invented date/currency/user.
    exported = frame.copy()
    for col in ('TransactionID','TransactionDT','isFraud'): exported[col]=data[col]
    exported['split'] = np.select([masks['train'],masks['validation']],['train','validation'],default='test')
    exported['model_score']=scores
    exported.to_csv(ARTIFACTS/'ieee-selected.csv.gz',index=False,compression='gzip')
    test_positions=np.flatnonzero(masks['test'])
    # Choose representative scored cases without consulting outcome labels.
    choices={'high_score':test_positions[np.argmax(scores[masks['test']])],
             'low_score':test_positions[np.argmin(scores[masks['test']])]}
    for name,pos in choices.items():
        fields={col:None if pd.isna(frame.iloc[pos][col]) else frame.iloc[pos][col] for col in FEATURES}
        payload={'dataset':'ieee_cis','transaction_id':str(int(data.iloc[pos].TransactionID)),'features':fields}
        (ARTIFACTS/(name+'-request.json')).write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps({'model_version':model_version,'threshold':threshold,'held_out_test':report['test']},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--zip',required=True)
    main(parser.parse_args().zip)
