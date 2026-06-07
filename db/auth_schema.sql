-- db/auth_schema.sql
-- Auth-related tables managed by Member 2.
-- Member 1 runs this alongside their survey data schema.
-- Apply with: psql $DATABASE_URL -f db/auth_schema.sql

-- ── USERS ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id         TEXT        PRIMARY KEY,
    password_hash   TEXT        NOT NULL,           -- Argon2id hash only
    scope           TEXT        NOT NULL DEFAULT 'public'
                                CHECK (scope IN ('public','research','admin')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    email           TEXT        UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_users_email    ON users (email);
CREATE INDEX IF NOT EXISTS idx_users_active   ON users (is_active);

-- Trigger: auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();


-- ── API KEYS ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS api_keys (
    key_id      TEXT        PRIMARY KEY,
    user_id     TEXT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    key_hash    TEXT        NOT NULL UNIQUE,   -- SHA3-256 only, never raw
    scope       TEXT        NOT NULL DEFAULT 'public'
                            CHECK (scope IN ('public','research')),
    description TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE,
    last_used_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user    ON api_keys (user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash    ON api_keys (key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_active  ON api_keys (revoked, expires_at);


-- ── REFRESH TOKENS ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    jti         TEXT        PRIMARY KEY,
    user_id     TEXT        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked     BOOLEAN     NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user    ON refresh_tokens (user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active  ON refresh_tokens (revoked, expires_at);

-- Auto-purge expired refresh tokens (run as a nightly cron)
-- DELETE FROM refresh_tokens WHERE expires_at < NOW() - INTERVAL '1 day';


-- ── READ-ONLY API ROLE ────────────────────────────────────────────────────────
-- Create a DB role that can only SELECT from survey tables.
-- The API connects as this role — even if SQL injection bypasses our checks,
-- the DB role cannot write, drop, or read the users table.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mospi_api_readonly') THEN
        CREATE ROLE mospi_api_readonly LOGIN PASSWORD 'change-in-production';
    END IF;
END
$$;

-- Grant SELECT on survey tables only
GRANT SELECT ON plfs_person     TO mospi_api_readonly;
GRANT SELECT ON plfs_household  TO mospi_api_readonly;
GRANT SELECT ON hces_household  TO mospi_api_readonly;
GRANT SELECT ON hces_person     TO mospi_api_readonly;
GRANT SELECT ON nsso_rounds     TO mospi_api_readonly;

-- Grant SELECT + INSERT on auth tables (for login, token storage)
GRANT SELECT, INSERT, UPDATE ON users          TO mospi_api_readonly;
GRANT SELECT, INSERT, UPDATE ON api_keys       TO mospi_api_readonly;
GRANT SELECT, INSERT, UPDATE ON refresh_tokens TO mospi_api_readonly;

-- Explicitly deny everything else
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM mospi_api_readonly;
-- Re-grant only what's needed above

-- ── SEED DATA (dev/test only — remove in production) ─────────────────────────
-- Insert a test admin user — password must be set via hash_password() in Python
-- DO NOT use this in production. Create users via the admin CLI.
INSERT INTO users (user_id, password_hash, scope, is_active, email)
VALUES (
    'admin',
    '$argon2id$v=19$m=65536,t=3,p=4$REPLACE_WITH_REAL_HASH',
    'admin',
    TRUE,
    'admin@mospi.gov.in'
)
ON CONFLICT (user_id) DO NOTHING;
