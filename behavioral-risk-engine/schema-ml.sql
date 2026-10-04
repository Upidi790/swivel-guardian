CREATE TABLE IF NOT EXISTS ml_datasets (
  dataset_key TEXT PRIMARY KEY,
  source_name TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ieee_transactions (
  dataset_key TEXT NOT NULL REFERENCES ml_datasets(dataset_key),
  transaction_id BIGINT NOT NULL,
  relative_seconds BIGINT NOT NULL,
  split TEXT NOT NULL CHECK (split IN ('train','validation','test')),
  features JSONB NOT NULL,
  PRIMARY KEY (dataset_key, transaction_id)
);
CREATE TABLE IF NOT EXISTS ieee_outcomes (
  dataset_key TEXT NOT NULL,
  transaction_id BIGINT NOT NULL,
  is_fraud BOOLEAN NOT NULL,
  PRIMARY KEY (dataset_key, transaction_id),
  FOREIGN KEY (dataset_key, transaction_id) REFERENCES ieee_transactions(dataset_key, transaction_id)
);
CREATE TABLE IF NOT EXISTS ml_models (
  model_version TEXT PRIMARY KEY,
  dataset_key TEXT NOT NULL REFERENCES ml_datasets(dataset_key),
  report JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ml_predictions (
  dataset_key TEXT NOT NULL,
  transaction_id BIGINT NOT NULL,
  model_version TEXT NOT NULL REFERENCES ml_models(model_version),
  model_score DOUBLE PRECISION NOT NULL CHECK (model_score BETWEEN 0 AND 1),
  requires_intervention BOOLEAN NOT NULL,
  PRIMARY KEY (dataset_key, transaction_id, model_version),
  FOREIGN KEY (dataset_key, transaction_id) REFERENCES ieee_transactions(dataset_key, transaction_id)
);
CREATE TABLE IF NOT EXISTS ml_risk_events (
  transaction_id TEXT NOT NULL,
  model_version TEXT NOT NULL REFERENCES ml_models(model_version),
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  request JSONB NOT NULL,
  result JSONB NOT NULL,
  PRIMARY KEY (transaction_id, model_version)
);
CREATE INDEX IF NOT EXISTS ieee_transactions_time ON ieee_transactions(dataset_key, relative_seconds);
COMMENT ON TABLE ieee_transactions IS 'IEEE-CIS source records; TransactionDT is relative time, not a real date. No customer identities or currency inferred.';
COMMENT ON TABLE ieee_outcomes IS 'Ground truth for offline evaluation only; never feed into scoring or the investigation agent.';
