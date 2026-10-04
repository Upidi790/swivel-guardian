import json
from sparkov_service import OUT

def main():
    r=json.loads((OUT/'report.json').read_text());scenarios=json.loads((OUT/'simulated-bank-scenarios.json').read_text())
    lines=['# Customer behavior demo: measured results','',
      f"The demo uses **{r['rows']:,} synthetic transactions across 50 simulated card/customer identifiers**. These customers were selected by identifier hash, without looking at fraud labels. The original full dataset is much larger.",
      '', 'The model compares a proposed payment with only earlier observations for that customer. Amount and category baselines use a rolling 90-day window. Merchant familiarity uses all available earlier observations. Simultaneous transactions cannot enter each other’s baselines.',
      '', '## Evaluation','',
      'The earliest 80% of the selected official training-file observations form the fitting period; the remaining 20% select the model and threshold. The selected customers’ official test-file observations form the later evaluation period. That test period was inspected during this implementation; it is not independent external validation.',
      '',f"Mature-history observations: {r['covered_rows']['train']:,} training, {r['covered_rows']['validation']:,} validation, {r['covered_rows']['test']:,} test. Test payments excluded for insufficient history: {r['cold_start_test_rows']}. At least 20 prior 90-day payments are required; cold starts return an explicit insufficient-history result.",
      '', 'Thresholds maximize validation recall subject to a 2% validation false-positive budget. This budget is not guaranteed on later data. Candidate selection uses validation recall, with lower false-positive rate as a tie-breaker.',
      '', '| Approach | Test precision | Fraud recall | Legitimate payments flagged | Fraud caught / missed | False alarms |','|---|---:|---:|---:|---:|---:|']
    for name,c in r['candidates'].items():
        m=c['test'];lines.append(f"| {name} | {m['precision']:.1%} | {m['recall']:.1%} | {m['false_positive_rate']:.2%} | {m['true_positives']} / {m['false_negatives']} | {m['false_positives']} |")
    chosen=r['candidates'][r['winner']]['test'];subset=r['unusual_legitimate_test'][r['winner']]
    lines+=['',f"Selected approach: **{r['winner']}**. The test contains only {chosen['fraud_rows']} fraud examples, so results have substantial sampling uncertainty. Overall accuracy is {chosen['accuracy']:.2%}; predicting every payment legitimate would score {1-chosen['fraud_rows']/chosen['rows']:.2%}, which illustrates why accuracy alone is misleading.",
      '',f"Among {subset['rows']} legitimate test payments with rule score at least 40 (our predeclared unusual-payment definition), the selected model flagged {subset['false_positives']} ({subset['false_positive_rate']:.1%}). These are dataset-legitimate payments; unusualness was defined by rules, not independent human review.",
      '', '## Explicit bank-transfer simulations','',
      'These 90 hand-authored cases use the original explainable transfer rules, not Sparkov fraud labels. They were not used to train or select the Sparkov model. Device/IP changes and newly registered recipients are deliberately simulated.',
      '', '| Scenario group | Cases | Investigation triggers |','|---|---:|---:|']
    for name,c in scenarios['summary'].items():lines.append(f"| {name} | {c['cases']} | {c['investigation_triggers']} |")
    lines+=['', 'The unusual-legitimate and scam-like cases are paired with identical observable payment behavior but different withheld interview context. They deliberately receive the same behavioral decisions. These counts verify demo behavior; they are not real-world scam precision or recall.',
      '', '## Scope and limitations','',
      '- Supported: personal amount median/percentile/z-score, category spending, merchant familiarity and first observation, source-clock timing, frequency, and merchant-to-home distance patterns.',
      '- Not supplied by Sparkov: bank-payee registration, device/IP histories, trusted recipients, account-opening date, payment success status, or victim answers. These remain unavailable or explicitly simulated.',
      '- Merchant location is not live device/customer location. Source-clock hour is not verified local time. First merchant observation is not payee registration.',
      '- Historical fraud labels never enter scoring, and earlier fraud-labeled observations are not silently removed from baselines.',
      '- These numbers cannot be directly compared with the IEEE-CIS results: the datasets, fraud rates, features, and populations differ.',
      '- The engine requests investigation; it does not authorize, block, or release payments.',
      '', 'Source: [Kaggle Sparkov dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection), [original synthetic generator](https://github.com/namebrandon/Sparkov_Data_Generation). Archive SHA256: `'+r['source_sha256']+'`.',
      '', 'The API and integration instructions are in `SPARKOV-GUIDE.md`.']
    (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
