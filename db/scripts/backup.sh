#!/usr/bin/env bash
# Makes a portable plain-SQL backup in ./backups (works across PostgreSQL versions).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

mkdir -p backups
FILE="backups/voltesse_$(date +%Y%m%d_%H%M%S).sql"
docker exec voltesse-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-privileges > "$FILE"
echo "Backup saved: $FILE"
