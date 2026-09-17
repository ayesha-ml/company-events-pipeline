CREATE TABLE IF NOT EXISTS company_event_records (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(64) NOT NULL,
    source_id VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL,
    normalized_data JSONB NOT NULL,
    consensus_data JSONB NOT NULL,
    audit_metadata JSONB NOT NULL,
    retrieved_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
