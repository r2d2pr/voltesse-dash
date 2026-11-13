-- Additive migration. Apply after the existing db/schema.sql. No driver tables changed.
CREATE TABLE IF NOT EXISTS web_auth_session (
    token_hash TEXT PRIMARY KEY,
    technician_id INT NOT NULL REFERENCES technician_user(technician_id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS web_auth_session_expiry ON web_auth_session(expires_at);
CREATE TABLE IF NOT EXISTS web_login_throttle (
    bucket TEXT PRIMARY KEY,
    attempts INT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS technician_preferences (
    technician_id INT PRIMARY KEY REFERENCES technician_user(technician_id) ON DELETE CASCADE,
    warning_temp INT NOT NULL DEFAULT 160 CHECK (warning_temp BETWEEN 100 AND 250),
    warning_battery INT NOT NULL DEFAULT 20 CHECK (warning_battery BETWEEN 5 AND 40),
    palette TEXT NOT NULL DEFAULT 'mint'
);
ALTER TABLE technician_preferences DROP CONSTRAINT IF EXISTS technician_preferences_warning_temp_check;
ALTER TABLE technician_preferences ADD CONSTRAINT technician_preferences_warning_temp_check CHECK (warning_temp BETWEEN 100 AND 250);
ALTER TABLE technician_preferences ALTER COLUMN warning_temp SET DEFAULT 160;
ALTER TABLE technician_preferences ADD COLUMN IF NOT EXISTS palette TEXT NOT NULL DEFAULT 'mint';
