import json
from benchmark_scorer import OUT

report=json.loads((OUT/'comparison.json').read_text(encoding='utf-8'))
winner=report['winner']
rows=['# Model comparison results','',f"Selected model: **{winner}**. Selection used validation average precision, before new test metrics were calculated.",'',
      'All test numbers below use the same 88,581 later transactions. This test was inspected previously, so these are retrospective benchmark results, not independent validation.','',
      '| Model | Precision | Recall | F1 | False-positive rate | Average precision |',
      '|---|---:|---:|---:|---:|---:|']
def row(name,m):
    return f"| {name} | {m['precision']:.1%} | {m['recall']:.1%} | {m['f1']:.3f} | {m['false_positive_rate']:.2%} | {m['average_precision']:.3f} |"
rows.append(row('Earlier 16-field model (original threshold)',report['previous_model']))
for name,result in report['candidates'].items():rows.append(row(name,result['test_max_f1']))
rows+=['','New candidate thresholds maximize F1 on the selection partition. The earlier row keeps its original threshold, selected under a 2% validation false-positive budget.',
       '', '## Comparison under a 2% validation false-positive budget','',
       '| Model | Precision | Recall | F1 | Test false-positive rate | Average precision |',
       '|---|---:|---:|---:|---:|---:|']
rows.append(row('Earlier 16-field model',report['previous_model']))
for name,result in report['candidates'].items():rows.append(row(name,result['test_fpr2']))
rows+=['','A validation budget does not guarantee the same rate on later data. The earlier threshold used the whole old validation interval; new thresholds use only its latter half, with the first half reserved for early stopping.',
       '', '## Scope','',
       'LightGBM is still gradient boosting. These results distinguish an algorithm family from a particular implementation, feature set, and threshold. The selected model is the best of the tested candidates under the stated validation criterion, not a universal best model.',
       '', 'The richer model uses 175 inputs, including anonymized source aggregates. Those fields need a compatible pre-payment feature provider before this can be used in a bank app. This result does not validate authorized-payment scam detection.',
       '', 'See `BENCHMARK-GUIDE.md` for API usage, evaluation design, source-field requirements, and reproduction commands.']
(OUT/'RESULTS.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
print('\n'.join(rows[:12]))
