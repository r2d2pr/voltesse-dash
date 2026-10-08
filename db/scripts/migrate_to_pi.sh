#!/usr/bin/env bash
# Moves your local database to the Raspberry Pi once SSH works.
#
# Usage:  ./scripts/migrate_to_pi.sh pi@raspberrypi.local
#
# Before running, on the Pi:
#   1. sudo apt install postgresql
#   2. sudo -u postgres createuser --pwprompt voltesse
#   3. sudo -u postgres createdb -O voltesse voltesse_dash
# This script then copies the schema + data into that empty database.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

TARGET="${1:?Usage: $0 user@host}"
DB_USER="${PI_DB_USER:-$POSTGRES_USER}"
DB_NAME="${PI_DB_NAME:-$POSTGRES_DB}"

./scripts/backup.sh
LATEST=$(ls -t backups/*.sql | head -n 1)

echo "Copying $LATEST to $TARGET ..."
scp "$LATEST" "$TARGET:/tmp/voltesse_restore.sql"

echo "Restoring on the Pi (you may be asked for the database password) ..."
ssh -t "$TARGET" "psql -h localhost -U $DB_USER -d $DB_NAME -v ON_ERROR_STOP=1 -f /tmp/voltesse_restore.sql && rm /tmp/voltesse_restore.sql"

echo "Done. Point your app's connection settings at the Pi."
