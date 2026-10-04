"""Report whether balancing helps, without changing evaluation prevalence."""
import json
from ml_model import ARTIFACTS

def main():
    out=ARTIFACTS/'balance-v6'
    report=json.loads((out/'comparison.json').read_text())
    candidates=report['candidates']
    names={'temporal_baseline':'Previous temporal model','balanced_loss':'Equal class influence','undersampled_4to1':'4:1 legitimate/fraud sample','recent_weighted':'Recent payments weighted more'}
    lines=['# Training-only balancing results','',
      'All experiments retain the original chronological validation and test populations. No synthetic transactions were created. The training partition contains 413,378 payments, including 14,538 fraud examples. The later test contains 88,581 payments, including 3,083 fraud examples.',
      '',f"Validation-selected candidate: **{names[report['winner']]}**. Selection minimizes the false-positive rate at 90% validation recall. This does not guarantee 90% recall on later data.",
      '', '## Balanced operating point','',
      '| Training approach | Test precision | Test recall | Legitimate payments flagged | Test F1 |','|---|---:|---:|---:|---:|']
    for name,result in candidates.items():
        m=result['test']['max_f1']
        lines.append(f"| {names[name]} | {m['precision']:.1%} | {m['recall']:.1%} | {m['false_positive_rate']:.2%} | {m['f1']:.3f} |")
    lines+=['','## High-recall operating points','',
      '| Training approach | Validation recall target | Test precision | Test recall | Legitimate payments flagged |','|---|---:|---:|---:|---:|']
    for name,result in candidates.items():
        for policy,target in [('recall90','90%'),('recall95','95%')]:
            m=result['test'][policy]
            lines.append(f"| {names[name]} | {target} | {m['precision']:.1%} | {m['recall']:.1%} | {m['false_positive_rate']:.2%} |")
    lines+=['','## What was tested','',
      '- Equal class influence: retained all training rows and increased fraud loss weight to approximately 27.43, giving the two classes equal aggregate loss weight.',
      '- Undersampling: retained all 14,538 training fraud rows and randomly selected 58,152 legitimate rows, for 72,690 total training rows. Seed 42.',
      '- Recency weighting: retained all training rows, reduced weights with a 30-day half-life, and assigned fraud loss weight 4.',
      '- All candidates use the same 452-feature schema, chronological partitions, and validation-only threshold procedure. Maximum 1,800 trees with early stopping; learning rate 0.035.',
      '', '## Limits','',
      'This is the same previously inspected retrospective test period, not fresh independent validation. Repeated experimentation can overfit evaluation results. Scores from weighted models are not calibrated fraud probabilities.',
      '','Balancing changes how the learner treats examples; it does not create new information about fraud. These experiments do not establish that synthetic augmentation would or would not help. Generating realistic extra fraud requires preserving the relationships between anonymized fields and avoiding duplicates or leakage into evaluation.',
      '', 'IEEE-CIS payment fraud is not a labeled bank-transfer scam/interview dataset. A successful model here still requires evaluation on the intended application.',
      '', 'Reproduce with `python improve_recall.py --zip <downloaded-zip> --balance`, then `python report_balance.py`.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Validation-selected candidate:',report['winner'])
    for name,result in candidates.items():
        print(name,json.dumps({policy:{k:m[k] for k in ('precision','recall','false_positive_rate','f1')} for policy,m in result['test'].items()}))

if __name__=='__main__':main()
