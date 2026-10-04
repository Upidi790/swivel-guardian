"""Readable retrospective operating-point comparison, including uncertainty."""
import argparse, json, math
from pathlib import Path
from ml_model import ARTIFACTS

def wilson(successes,total):
    z=1.96;p=successes/total;d=1+z*z/total
    center=(p+z*z/(2*total))/d
    half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [center-half,center+half]

def main(folder='recall-v4'):
    out=ARTIFACTS/folder
    r=json.loads((out/'comparison.json').read_text())
    old=json.loads((ARTIFACTS/'benchmark'/'comparison.json').read_text())
    winner=r['winner'];selected=r['candidates'][winner]
    lines=['# Expanded-feature fraud model results','',
      'This is a retrospective comparison on the same 88,581 chronological test payments used before. It is not a new independent evaluation. Model selection and thresholds use the separate validation period.',
      '',f'Validation-selected candidate: **{winner}**. Candidates use all 339 V-features ({r["protocol"]["feature_count"]} total model features). The earlier model retained only 80 V-features, ending at V123.',
      '', '| Model / operating point | Precision | Fraud recall | Legitimate payments flagged | Fraud caught | False alarms |',
      '|---|---:|---:|---:|---:|---:|']
    rows=[('Previous v3 balanced',old['candidates'][old['winner']]['test_max_f1'])]
    for name,result in r['candidates'].items():
        for policy,m in result['test'].items():rows.append((name+' / '+policy,m))
    for label,m in rows:
        lines.append(f"| {label} | {m['precision']:.1%} | {m['recall']:.1%} | {m['false_positive_rate']:.2%} | {m['true_positives']:,} | {m['false_positives']:,} |")
    lines+=['','## Interpretation','',
      'Recall90 and recall95 target those recall levels on validation, not on future data. Max_f1 balances precision and recall. Fpr2 targets at most 2% legitimate-payment flags on validation. None guarantees the same result later.',
      '','| Selected candidate policy | Test recall 95% Wilson interval | Test false-positive rate 95% Wilson interval |','|---|---:|---:|']
    for policy,m in selected['test'].items():
        recall=wilson(m['true_positives'],m['fraud_rows'])
        fpr=wilson(m['false_positives'],m['true_negatives']+m['false_positives'])
        lines.append(f'| {policy} | {recall[0]:.1%}–{recall[1]:.1%} | {fpr[0]:.2%}–{fpr[1]:.2%} |')
    lines+=['','These intervals describe binomial sampling uncertainty only; repeated model development on this test period and changes in transaction patterns introduce additional uncertainty.',
      '', '## Integration and limits','',
      'The selected model is saved in selected-model.joblib and can be loaded with BenchmarkScorer(artifact_path=...). Its balanced threshold is the validation maximum-F1 setting. After running finalize_recall.py, the optional /ml/candidate/analyze endpoint exposes both balanced and high-recall screening signals. See RECALL-GUIDE.md and integration-verification.json for integration status. The existing /ml/analyze default remains v3.',
      '', 'The IEEE-CIS data concerns payment fraud and contains proprietary anonymized features. It does not establish accuracy on bank-transfer scams involving a deceived payer. Do not fabricate missing V-features or treat model scores as calibrated scam probabilities. Customer interview responses must be evaluated separately and end-to-end performance measured on labeled scam cases.',
      '', 'The FCA APP synthetic dataset is more closely aligned with that scenario. Access is through the [FCA Digital Sandbox](https://www.fca.org.uk/firms/innovation/digital-sandbox); this run did not obtain that dataset.',
      '', 'Reproduce: `.venv\\Scripts\\python.exe improve_recall.py --zip <path-to-ieee-fraud-detection.zip>` then `.venv\\Scripts\\python.exe report_recall.py`.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'winner':winner,'selected_test':selected['test']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--folder',default='recall-v4')
    main(parser.parse_args().folder)
