CREATE TABLE IF NOT EXISTS sparkov_users(user_id TEXT PRIMARY KEY, provenance TEXT NOT NULL DEFAULT 'Sparkov synthetic customer/card proxy');
CREATE TABLE IF NOT EXISTS sparkov_transactions(
 transaction_id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES sparkov_users(user_id),
 event_time TIMESTAMP WITHOUT TIME ZONE NOT NULL,amount DOUBLE PRECISION NOT NULL CHECK(amount>0),
 merchant_id TEXT NOT NULL,category TEXT NOT NULL,home_latitude DOUBLE PRECISION NOT NULL,
 home_longitude DOUBLE PRECISION NOT NULL,merchant_latitude DOUBLE PRECISION NOT NULL,merchant_longitude DOUBLE PRECISION NOT NULL);
CREATE INDEX IF NOT EXISTS sparkov_history_idx ON sparkov_transactions(user_id,event_time);
CREATE TABLE IF NOT EXISTS sparkov_outcomes(transaction_id TEXT PRIMARY KEY REFERENCES sparkov_transactions(transaction_id),is_fraud BOOLEAN NOT NULL,partition TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sparkov_models(model_version TEXT PRIMARY KEY,report JSONB NOT NULL);
CREATE TABLE IF NOT EXISTS sparkov_risk_events(transaction_id TEXT NOT NULL,model_version TEXT NOT NULL REFERENCES sparkov_models(model_version),evaluated_at TIMESTAMPTZ NOT NULL,request JSONB NOT NULL,result JSONB NOT NULL,PRIMARY KEY(transaction_id,model_version));
COMMENT ON TABLE sparkov_transactions IS 'Synthetic card transactions. No real bank-payee, device, IP, or settlement-status claims. Timestamps are source-clock values.';
COMMENT ON TABLE sparkov_outcomes IS 'Offline evaluation labels only; never queried by behavioral scoring.';
