-- Fake sample data so you can test queries before real CAN data exists.
-- Load with: ./db/scripts/seed.sh
-- (Do not load into a database you care about: it adds three fake sessions.)

BEGIN;

-- Placeholder account. Replace the hash with a real salted bcrypt/argon2 hash from the back-end.
INSERT INTO technician_user (name, username, password_hash, role)
VALUES ('Demo Technician', 'tech_demo', 'REPLACE_WITH_REAL_HASH', 'TECHNICIAN')
ON CONFLICT (username) DO NOTHING;

-- Three simulated sessions, one hour apart, each lasting 10 minutes.
INSERT INTO vehicle_session
    (driver_identifier, start_timestamp, end_timestamp, session_notes, source_type, status, start_soc_percent, end_soc_percent)
SELECT 'demo_driver',
       now() - (n || ' hours')::interval,
       now() - (n || ' hours')::interval + interval '10 minutes',
       'Sample session ' || n || ' (fake data)',
       'SIMULATION', 'COMPLETED', 100 - n, 88 - n
FROM generate_series(1, 3) AS n;

-- One reading per second for each of those sessions (600 rows each).
INSERT INTO telemetry_log
    (session_id, "timestamp", speed_mph, motor_rpm, battery_percent, motor_temperature,
     power_draw_watts, signal_status, warning_state, trip_distance_km, drive_mode, gear, transmission_mode)
SELECT s.session_id,
       s.start_timestamp + (t || ' seconds')::interval,
       v.speed,
       (v.speed * 70)::INT,
       s.start_soc_percent - (t / 600.0) * 12,               -- battery drains over the run
       40 + (t / 600.0) * 35 + random() * 2,                 -- motor heats up
       v.speed * 250 + random() * 800,                       -- power roughly follows speed
       'SIM RUNNING',
       CASE WHEN t > 540 THEN '["HIGH MOTOR TEMP"]'::jsonb ELSE '[]'::jsonb END,
       (sum(v.speed) OVER (PARTITION BY s.session_id ORDER BY t)) * 1.609344 / 3600.0,
       'DRIVE', 'D3', 'AUTO'
FROM vehicle_session s
CROSS JOIN generate_series(0, 599) AS t
CROSS JOIN LATERAL (
    SELECT greatest(0, 40 + 25 * sin(t / 40.0) + random() * 3) AS speed
) v
WHERE s.driver_identifier = 'demo_driver';

INSERT INTO backup_log (backup_type, backup_status, file_reference, initiated_by)
VALUES ('SCHEDULED', 'SUCCESS', '/var/backups/voltesse/sample_scheduled.sql', NULL),
       ('MANUAL', 'SUCCESS', '/var/backups/voltesse/sample_manual.sql',
        (SELECT technician_id FROM technician_user WHERE username = 'tech_demo'));

COMMIT;
