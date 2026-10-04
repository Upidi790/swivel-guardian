-- Current selected model: keep versions separate when exploring results.
SELECT transaction_id,
       round((model_score*100)::numeric,2) AS risk_score,
       requires_intervention
FROM public.ml_predictions
WHERE model_version='ieee-benchmark-v3-lightgbm_rich-4cc646da09d0'
ORDER BY model_score DESC
LIMIT 20;

-- Offline evaluation only: do not supply is_fraud to the agent.
SELECT p.requires_intervention, o.is_fraud, count(*)
FROM public.ml_predictions p
JOIN public.ieee_outcomes o USING(dataset_key,transaction_id)
WHERE p.model_version='ieee-benchmark-v3-lightgbm_rich-4cc646da09d0'
GROUP BY 1,2;

SELECT report->'candidates' AS comparison
FROM public.ml_models
WHERE model_version='ieee-benchmark-v3-lightgbm_rich-4cc646da09d0';
