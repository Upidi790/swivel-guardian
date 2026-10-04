-- Run these queries in the Tiger Data SQL Editor after setup completes.
SELECT 'users' AS table_name, count(*) AS rows FROM users
UNION ALL SELECT 'recipients', count(*) FROM recipients
UNION ALL SELECT 'devices', count(*) FROM devices
UNION ALL SELECT 'transactions', count(*) FROM transactions
UNION ALL SELECT 'risk_events', count(*) FROM risk_events;

SELECT timestamp, transaction_id, user_id, amount, currency,
       recipient_id, transaction_type, successful
FROM transactions
ORDER BY timestamp DESC, transaction_id
LIMIT 20;

SELECT user_id, transaction_id,
       result->>'risk_score' AS risk_score,
       result->>'risk_level' AS risk_level,
       result->>'requires_intervention' AS requires_intervention,
       result->'signals' AS explanations
FROM risk_events
ORDER BY evaluated_at DESC
LIMIT 10;
