CREATE OR REPLACE FUNCTION purge_expired_records()
RETURNS integer AS $$
DECLARE
    deleted_count integer;
BEGIN
    DELETE FROM company_event_records
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
