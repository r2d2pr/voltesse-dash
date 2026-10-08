-- =====================================================================
-- Voltesse Dash - PostgreSQL schema
-- Source: SRS Activity 4.3 (v1.1), section 3.4 Logical Database Requirements
--
-- Entities from the SRS: TECHNICIAN_USER, VEHICLE_SESSION, TELEMETRY_LOG, BACKUP_LOG.
-- Columns marked "extra" are NOT in the SRS table; they hold values the app already
-- records (nullable, so they can be dropped or promoted later without a redesign).
--
-- Safe to run more than once (IF NOT EXISTS / OR REPLACE), and it uses no
-- schema prefixes, so it follows the connection's search_path.
-- =====================================================================

-- ---------------------------------------------------------------------
-- TECHNICIAN_USER: authenticated Technician/Admin accounts only.
-- The Driver is unauthenticated and read-only, so has no row here.
-- Kept apart from telemetry (SRS 3.4) to reduce corruption risk.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS technician_user (
    technician_id  INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT        NOT NULL,
    username       TEXT        NOT NULL UNIQUE,
    password_hash  TEXT        NOT NULL,              -- salted hash only, never plain text
    role           TEXT        NOT NULL DEFAULT 'TECHNICIAN'
                   CHECK (role IN ('TECHNICIAN', 'ADMIN')),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at  TIMESTAMPTZ
);

-- ---------------------------------------------------------------------
-- VEHICLE_SESSION: one run, bench test, or simulated test.
-- Retention is session-based (SRS 3.4, PR-4), see prune_old_sessions().
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vehicle_session (
    session_id       INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    driver_identifier TEXT,
    start_timestamp  TIMESTAMPTZ NOT NULL DEFAULT now(),
    end_timestamp    TIMESTAMPTZ,
    session_notes    TEXT,
    source_type      TEXT        NOT NULL DEFAULT 'CAN_BUS'
                     CHECK (source_type IN ('CAN_BUS', 'OBD_II', 'SIMULATION', 'TEST', 'MIXED')),
    status           TEXT        NOT NULL DEFAULT 'ACTIVE'
                     CHECK (status IN ('ACTIVE', 'COMPLETED', 'INTERRUPTED')),
    -- extra: end-of-session summary the app already computes
    start_soc_percent    REAL,
    end_soc_percent      REAL,
    max_speed_mph        REAL,
    avg_speed_mph        REAL,
    total_distance_km    REAL,
    total_energy_kwh     REAL,
    CHECK (end_timestamp IS NULL OR end_timestamp >= start_timestamp)
);
CREATE INDEX IF NOT EXISTS idx_session_start ON vehicle_session (start_timestamp DESC);

-- ---------------------------------------------------------------------
-- TELEMETRY_LOG: time-stamped vehicle metrics.
-- Each row belongs to exactly one session (NOT NULL FK). Deleting a
-- session removes its readings, which is what retention pruning needs.
-- Metric columns are nullable because data is logged "when available" (FR-7).
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry_log (
    log_id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    session_id         INT         NOT NULL REFERENCES vehicle_session(session_id) ON DELETE CASCADE,
    "timestamp"        TIMESTAMPTZ NOT NULL,
    speed_mph          REAL CHECK (speed_mph >= 0),
    motor_rpm          INT  CHECK (motor_rpm >= 0),
    battery_percent    REAL CHECK (battery_percent BETWEEN 0 AND 100),
    motor_temperature  REAL,                    -- degrees Celsius
    power_draw_watts   REAL,                    -- negative while regenerating
    signal_status      TEXT,                    -- e.g. CAN ACTIVE, CAN OFFLINE, SIM RUNNING
    warning_state      JSONB NOT NULL DEFAULT '[]'::jsonb,   -- list of active warnings
    -- extra: other values the app already records
    battery_voltage_v  REAL,
    battery_current_a  REAL,
    battery_temp_c     REAL,
    inverter_temp_c    REAL,
    throttle_pct       REAL,
    brake_pct          REAL,
    drive_mode         TEXT,
    trip_distance_km   REAL,
    steering_angle     REAL,
    gear               TEXT,
    transmission_mode  TEXT
);
-- Matches how technicians read data: one session, in time order, short windows (PR-7).
CREATE INDEX IF NOT EXISTS idx_telemetry_session_time ON telemetry_log (session_id, "timestamp");

-- ---------------------------------------------------------------------
-- BACKUP_LOG: scheduled (every 5 days, PR-5) and manual backups.
-- initiated_by is NULL for scheduled backups started by the system.
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS backup_log (
    backup_id         INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    backup_timestamp  TIMESTAMPTZ NOT NULL DEFAULT now(),
    backup_type       TEXT NOT NULL CHECK (backup_type IN ('SCHEDULED', 'MANUAL')),
    backup_status     TEXT NOT NULL DEFAULT 'STARTED'
                      CHECK (backup_status IN ('STARTED', 'SUCCESS', 'FAILED')),
    file_reference    TEXT,
    initiated_by      INT REFERENCES technician_user(technician_id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_backup_time ON backup_log (backup_timestamp DESC);

-- ---------------------------------------------------------------------
-- Retention (SRS PR-4: at least 15 days OR the most recent 15-20 sessions).
-- Deletes a session only if it is BOTH outside the newest keep_sessions AND
-- older than keep_days. keep_days = 0 gives pure session-based retention.
-- Sessions still ACTIVE are never deleted. Returns how many were deleted.
-- The final N and day values are to be approved by the team (PR-4).
-- ---------------------------------------------------------------------
CREATE OR REPLACE FUNCTION prune_old_sessions(keep_sessions INT DEFAULT 20, keep_days INT DEFAULT 0)
RETURNS INT
LANGUAGE plpgsql AS $$
DECLARE
    deleted INT;
BEGIN
    IF keep_sessions < 1 THEN
        RAISE EXCEPTION 'keep_sessions must be at least 1';
    END IF;

    WITH ranked AS (
        SELECT session_id,
               start_timestamp,
               status,
               row_number() OVER (ORDER BY start_timestamp DESC, session_id DESC) AS rn
        FROM vehicle_session
    )
    DELETE FROM vehicle_session
    WHERE session_id IN (
        SELECT session_id FROM ranked
        WHERE rn > keep_sessions
          AND status <> 'ACTIVE'
          AND start_timestamp < now() - make_interval(days => keep_days)
    );
    GET DIAGNOSTICS deleted = ROW_COUNT;
    RETURN deleted;
END;
$$;

-- ---------------------------------------------------------------------
-- Technician troubleshooting metrics (team-defined). Each view reads
-- telemetry_log and is ready for charts in the Technician/Admin dashboard.
-- ---------------------------------------------------------------------

-- 1) Energy efficiency at different speeds: watt-hours per mile, 10 mph buckets.
CREATE OR REPLACE VIEW v_efficiency_by_speed AS
SELECT session_id,
       (floor(speed_mph / 10) * 10)::INT AS speed_bucket_mph,
       round((avg(power_draw_watts) / NULLIF(avg(speed_mph), 0))::numeric, 2) AS wh_per_mile
FROM telemetry_log
WHERE speed_mph > 0
GROUP BY session_id, speed_bucket_mph;

-- 2) Power drawn at different motor temperatures, 5 degree buckets.
CREATE OR REPLACE VIEW v_power_by_temperature AS
SELECT session_id,
       (floor(motor_temperature / 5) * 5)::INT AS temperature_bucket_c,
       round(avg(power_draw_watts)::numeric, 1) AS avg_power_watts
FROM telemetry_log
WHERE motor_temperature IS NOT NULL
GROUP BY session_id, temperature_bucket_c;

-- 3) Battery consumption over distance (uses the extra trip_distance_km column).
CREATE OR REPLACE VIEW v_battery_over_distance AS
SELECT session_id, trip_distance_km, battery_percent
FROM telemetry_log
WHERE trip_distance_km IS NOT NULL AND battery_percent IS NOT NULL
ORDER BY session_id, trip_distance_km;

-- 4) Power drawn at different RPMs, 500 rpm buckets.
CREATE OR REPLACE VIEW v_power_by_rpm AS
SELECT session_id,
       (floor(motor_rpm / 500) * 500)::INT AS rpm_bucket,
       round(avg(power_draw_watts)::numeric, 1) AS avg_power_watts
FROM telemetry_log
WHERE motor_rpm IS NOT NULL
GROUP BY session_id, rpm_bucket;

-- 5) Temperature rise over time: seconds since the session started.
CREATE OR REPLACE VIEW v_temperature_over_time AS
SELECT t.session_id,
       extract(epoch FROM (t."timestamp" - s.start_timestamp))::INT AS seconds_into_session,
       t.motor_temperature
FROM telemetry_log t
JOIN vehicle_session s USING (session_id)
WHERE t.motor_temperature IS NOT NULL
ORDER BY t.session_id, t."timestamp";
