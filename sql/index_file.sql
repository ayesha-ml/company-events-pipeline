CREATE INDEX IF NOT EXISTS index_company_events_lookup
ON company_event_records(company_id, retrieved_at);

CREATE INDEX IF NOT EXISTS index_company_events_expiry
ON company_event_records(expires_at);

CREATE INDEX IF NOT EXISTS index_company_events_gin_consensus
ON company_event_records USING GIN (consensus_data);

CREATE INDEX IF NOT EXISTS index_company_events_gin_normalized
ON company_event_records USING GIN (normalized_data);
