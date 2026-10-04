-- Source transactions: no manufactured customer ids or calendar timestamps.
SELECT transaction_id, relative_seconds, split,
       features->>'TransactionAmt' AS amount,
       features->>'ProductCD' AS product_code,
       features->>'DeviceType' AS device_type
FROM public.ieee_transactions
ORDER BY relative_seconds DESC, transaction_id
LIMIT 20;

-- Holdout scores. Labels are deliberately absent from the agent-facing data.
SELECT transaction_id, round((model_score*100)::numeric,2) AS risk_score,
       requires_intervention
FROM public.ml_predictions
WHERE model_version = 'ieee-hgb-v2-4cc646da09d0'
ORDER BY model_score DESC
LIMIT 20;

-- Evaluation counts only; never supply is_fraud to the investigation agent.
SELECT p.requires_intervention, o.is_fraud, count(*)
FROM public.ml_predictions p
JOIN public.ieee_outcomes o USING (dataset_key,transaction_id)
WHERE p.model_version = 'ieee-hgb-v2-4cc646da09d0'
GROUP BY p.requires_intervention,o.is_fraud;

SELECT transaction_id,result FROM public.ml_risk_events ORDER BY evaluated_at DESC LIMIT 5;
