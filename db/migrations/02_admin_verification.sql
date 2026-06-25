-- db/migrations/02_admin_verification.sql

CREATE TABLE IF NOT EXISTS pending_registrations (
    email               TEXT        PRIMARY KEY,
    password_hash       TEXT        NOT NULL,
    scope               TEXT        NOT NULL DEFAULT 'public'
                                    CHECK (scope IN ('public','research','admin')),
    status              VARCHAR(50) NOT NULL DEFAULT 'pending_admin'
                                    CHECK (status IN ('pending_admin','pending_otp')),
    registration_info   JSONB,
    otp_hash            TEXT,
    otp_expires_at      TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Trigger: auto-update updated_at for pending_registrations
CREATE OR REPLACE FUNCTION update_pending_registrations_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS pending_registrations_updated_at ON pending_registrations;
CREATE TRIGGER pending_registrations_updated_at
    BEFORE UPDATE ON pending_registrations
    FOR EACH ROW EXECUTE FUNCTION update_pending_registrations_updated_at();

-- Grant privileges to the mospi_api_readonly role
GRANT SELECT, INSERT, UPDATE, DELETE ON pending_registrations TO mospi_api_readonly;
