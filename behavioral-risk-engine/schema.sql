-- Run in a dedicated demo database. Requires TimescaleDB (included in Tiger Data).
CREATE TABLE IF NOT EXISTS users (
  user_id TEXT PRIMARY KEY,
  profile JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS recipients (
  user_id TEXT NOT NULL REFERENCES users(user_id),
  recipient_id TEXT NOT NULL,
  first_seen TIMESTAMPTZ NOT NULL,
  recipient_type TEXT NOT NULL,
  trusted BOOLEAN NOT NULL DEFAULT FALSE,
  PRIMARY KEY (user_id, recipient_id)
);
CREATE TABLE IF NOT EXISTS devices (
  user_id TEXT NOT NULL REFERENCES users(user_id),
  device_id TEXT NOT NULL,
  PRIMARY KEY (user_id, device_id)
);
CREATE TABLE IF NOT EXISTS transactions (
  timestamp TIMESTAMPTZ NOT NULL,
  transaction_id TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
  currency TEXT NOT NULL,
  recipient_id TEXT NOT NULL,
  transaction_type TEXT NOT NULL,
  successful BOOLEAN NOT NULL,
  payload JSONB NOT NULL,
  PRIMARY KEY (timestamp, transaction_id)
);
SELECT create_hypertable('transactions', by_range('timestamp'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS transactions_user_time ON transactions(user_id, timestamp DESC);
CREATE TABLE IF NOT EXISTS risk_events (
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  user_id TEXT NOT NULL REFERENCES users(user_id),
  transaction_id TEXT NOT NULL,
  model_version TEXT NOT NULL,
  request JSONB NOT NULL,
  result JSONB NOT NULL,
  PRIMARY KEY (user_id, transaction_id, model_version)
);

-- Example rolling baseline query (bind user, currency, rail, and payment time).
-- SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY amount) AS median,
--        percentile_cont(0.95) WITHIN GROUP (ORDER BY amount) AS p95,
--        avg(amount), count(*)
-- FROM transactions
-- WHERE user_id = %s AND currency = %s AND transaction_type = %s
--   AND successful AND timestamp < %s AND timestamp >= %s::timestamptz - INTERVAL '90 days';
