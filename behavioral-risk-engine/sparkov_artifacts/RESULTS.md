# Customer behavior demo: measured results

The demo uses **92,966 synthetic transactions across 50 simulated card/customer identifiers**. These customers were selected by identifier hash, without looking at fraud labels. The original full dataset is much larger.

The model compares a proposed payment with only earlier observations for that customer. Amount and category baselines use a rolling 90-day window. Merchant familiarity uses all available earlier observations. Simultaneous transactions cannot enter each other’s baselines.

## Evaluation

The earliest 80% of the selected official training-file observations form the fitting period; the remaining 20% select the model and threshold. The selected customers’ official test-file observations form the later evaluation period. That test period was inspected during this implementation; it is not independent external validation.

Mature-history observations: 51,242 training, 13,037 validation, 27,727 test. Test payments excluded for insufficient history: 0. At least 20 prior 90-day payments are required; cold starts return an explicit insufficient-history result.

Thresholds maximize validation recall subject to a 2% validation false-positive budget. This budget is not guaranteed on later data. Candidate selection uses validation recall, with lower false-positive rate as a tie-breaker.

| Approach | Test precision | Fraud recall | Legitimate payments flagged | Fraud caught / missed | False alarms |
|---|---:|---:|---:|---:|---:|
| rules | 7.6% | 14.0% | 0.57% | 13 / 80 | 158 |
| isolation_forest | 5.0% | 53.8% | 3.47% | 50 / 43 | 960 |
| behavioral_lightgbm | 16.3% | 78.5% | 1.36% | 73 / 20 | 375 |

Selected approach: **behavioral_lightgbm**. The test contains only 93 fraud examples, so results have substantial sampling uncertainty. Overall accuracy is 98.58%; predicting every payment legitimate would score 99.66%, which illustrates why accuracy alone is misleading.

Among 960 legitimate test payments with rule score at least 40 (our predeclared unusual-payment definition), the selected model flagged 192 (20.0%). These are dataset-legitimate payments; unusualness was defined by rules, not independent human review.

## Explicit bank-transfer simulations

These 90 hand-authored cases use the original explainable transfer rules, not Sparkov fraud labels. They were not used to train or select the Sparkov model. Device/IP changes and newly registered recipients are deliberately simulated.

| Scenario group | Cases | Investigation triggers |
|---|---:|---:|
| normal | 50 | 0 |
| unusual_legitimate | 20 | 10 |
| scam_like | 20 | 10 |

The unusual-legitimate and scam-like cases are paired with identical observable payment behavior but different withheld interview context. They deliberately receive the same behavioral decisions. These counts verify demo behavior; they are not real-world scam precision or recall.

## Scope and limitations

- Supported: personal amount median/percentile/z-score, category spending, merchant familiarity and first observation, source-clock timing, frequency, and merchant-to-home distance patterns.
- Not supplied by Sparkov: bank-payee registration, device/IP histories, trusted recipients, account-opening date, payment success status, or victim answers. These remain unavailable or explicitly simulated.
- Merchant location is not live device/customer location. Source-clock hour is not verified local time. First merchant observation is not payee registration.
- Historical fraud labels never enter scoring, and earlier fraud-labeled observations are not silently removed from baselines.
- These numbers cannot be directly compared with the IEEE-CIS results: the datasets, fraud rates, features, and populations differ.
- The engine requests investigation; it does not authorize, block, or release payments.

Source: [Kaggle Sparkov dataset](https://www.kaggle.com/datasets/kartik2112/fraud-detection), [original synthetic generator](https://github.com/namebrandon/Sparkov_Data_Generation). Archive SHA256: `4e32829b9ba5a6b17af707c513c15204011044df0e8971e431cedca3d8c0a8a1`.

The API and integration instructions are in `SPARKOV-GUIDE.md`.
