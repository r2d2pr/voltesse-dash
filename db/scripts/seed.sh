#!/usr/bin/env bash
# Loads the fake sample data into the local Docker database.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

docker exec -i voltesse-db psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" < seed.sql
echo "Sample data loaded."
