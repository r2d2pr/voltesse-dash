# Voltesse Dash - Database (PostgreSQL)

Schema, sample data and tools for the Voltesse Dash PostgreSQL database.
The schema follows the SRS (Activity 4.3, v1.1, section 3.4 Logical Database Requirements).

| File | Purpose |
|------|---------|
| `schema.sql` | Tables, indexes, retention function and technician metric views. The app runs it automatically at startup (it is safe to run repeatedly). |
| `seed.sql` | Fake sample data (3 sessions, 1800 readings) for trying queries. |
| `docker-compose.yml`, `.env.example` | Local PostgreSQL in Docker. |
| `scripts/` | `seed.sh`, `backup.sh`, `migrate_to_pi.sh`. |

## Tables (from the SRS)

| Table | Holds |
|-------|-------|
| `technician_user` | Technician/Admin accounts (salted password hash, role). The Driver is unauthenticated, so has no row. |
| `vehicle_session` | One run, bench test or simulated test: driver, start/end time, notes, source type, status. |
| `telemetry_log` | Time-stamped readings, each belonging to exactly one session: speed (mph), RPM, battery %, motor temperature, power draw (watts), signal status, warnings. |
| `backup_log` | Scheduled and manual backups. |

`vehicle_session` and `telemetry_log` also have a few **extra nullable columns** for values the app already records (battery voltage/current, inverter temperature, throttle, brake, gear, trip distance and so on, plus session summary fields). They are not in the SRS table and should be listed in the SDD, or removed if the team prefers the SRS columns only.

Technician troubleshooting metrics are views: `v_efficiency_by_speed`, `v_power_by_temperature`, `v_battery_over_distance`, `v_power_by_rpm`, `v_temperature_over_time`.

Retention: `SELECT prune_old_sessions(20, 0);` deletes sessions outside the newest 20 (and older than 0 days). Active sessions are never deleted. The app calls it at startup (`--keep-sessions`). PR-4 allows "15 days or 15-20 sessions", so the team still has to approve the final numbers.

## Run it locally (Docker, recommended)

Docker gives everyone the same PostgreSQL version and setup with one command. If you can't use Docker, see [Without Docker](#without-docker-fallback) below.

1. Install Docker Desktop and open it once (on Windows it needs WSL 2).
2. From this folder:

   ```
   cp .env.example .env        # then change the password if you like
   chmod +x scripts/*.sh
   docker compose up -d
   ./scripts/seed.sh           # optional sample data
   ```

   Windows (PowerShell):

   ```
   Copy-Item .env.example .env
   docker compose up -d
   Get-Content seed.sql | docker exec -i voltesse-db psql -U voltesse -d voltesse_dash   # optional sample data
   ```

3. Point the app at it:

   ```
   export VOLTESSE_DB_URL=postgresql://voltesse:voltesse@localhost:5432/voltesse_dash
   python main.py --windowed --mode SIMULATION
   ```

   Windows (PowerShell): `$env:VOLTESSE_DB_URL="postgresql://voltesse:voltesse@localhost:5432/voltesse_dash"`

Look inside the database: `docker exec -it voltesse-db psql -U voltesse -d voltesse_dash` (then `\dt`, `\dv`, `SELECT * FROM vehicle_session;`).

The container also creates a `voltesse_test` database the unit tests use. If your Docker volume already existed before this, create it once with:
`docker exec voltesse-db psql -U voltesse -c "CREATE DATABASE voltesse_test;"`

Everyday: `docker compose stop` / `docker compose start`, `./scripts/backup.sh` (saved in `backups/`), and `docker compose down -v` to wipe everything.

The port is bound to `127.0.0.1`, so only your own computer can reach it.

## Without Docker (fallback)

Install PostgreSQL 16 directly, then create the same user and databases the container would. The app creates the tables itself on first run.

1. Install and start PostgreSQL:
   - macOS: `brew install postgresql@16 && brew services start postgresql@16`
   - Windows: the installer from postgresql.org (EDB). Keep port 5432 and remember the `postgres` password it asks for. Its tools are in `C:\Program Files\PostgreSQL\16\bin`.
   - Raspberry Pi / Linux: `sudo apt install postgresql`
2. Open `psql` as the admin user:
   - macOS: `psql -d postgres` (Homebrew's `psql` is in `/opt/homebrew/opt/postgresql@16/bin`)
   - Windows: `psql -U postgres`
   - Pi / Linux: `sudo -u postgres psql`
3. Run:

   ```
   CREATE ROLE voltesse LOGIN PASSWORD 'voltesse';
   CREATE DATABASE voltesse_dash OWNER voltesse;
   CREATE DATABASE voltesse_test OWNER voltesse;
   ```

4. Set `VOLTESSE_DB_URL` as in step 3 above and start the app. Optional sample data:
   `psql postgresql://voltesse:voltesse@localhost:5432/voltesse_dash -f schema.sql -f seed.sql`

`scripts/seed.sh` and `scripts/backup.sh` only work with the Docker container. Without Docker, use `psql -f seed.sql` (above) and `pg_dump` directly. A Homebrew install lets local programs connect without a password; that is fine for development but not for the Pi.

## Moving to the Raspberry Pi

1. On the Pi: `sudo apt install postgresql`, then create the user and an empty database (steps are at the top of `scripts/migrate_to_pi.sh`).
2. The Pi's PostgreSQL major version must be the same as, or newer than, `PG_VERSION` in `.env` (check with `apt-cache policy postgresql`). If the Pi has an older one, set `PG_VERSION` to match before starting the local container.
3. Run `./scripts/migrate_to_pi.sh pi@raspberrypi.local`.
4. On the Pi, set `VOLTESSE_DB_URL` to the Pi's local database. The app and the database both run on the Pi (SRS 3.1.2), so the host stays `localhost` there.

## Security notes

- Never commit `.env` or a URL containing a password. The app logs the database URL with the password hidden.
- `password_hash` must hold a salted hash (bcrypt/argon2) created by the back-end. The value in `seed.sql` is a placeholder.
- Do not expose port 5432 outside the Pi. Remote Technician access goes through the VPN layer and the authenticated back-end (SRS 3.1.3).
