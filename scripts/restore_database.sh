#!/bin/bash

# Exit on any error
set -e

echo "========================================"
echo "V4 Studio - Database Restore Script"
echo "========================================"

# Check arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path_to_backup_file.sql.gz>"
    echo "Example: $0 ./backups/db/v4_studio_db_20260810_120000.sql.gz"
    exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="v4_studio_postgres_prod"
DB_USER="v4_studio_user"
DB_NAME="v4_studio"

# Check if file exists
if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file '$BACKUP_FILE' does not exist."
    exit 1
fi

# Ensure container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: Container $CONTAINER_NAME is not running. Please start it using docker-compose."
    exit 1
fi

echo "WARNING: DESTRUCTIVE ACTION"
echo "You are about to restore the database from '$BACKUP_FILE'."
echo "This will overwrite all existing data in the '$DB_NAME' database!"
read -p "Are you absolutely sure you want to proceed? (Type 'YES' to confirm): " CONFIRM

if [ "$CONFIRM" != "YES" ]; then
    echo "Restore aborted."
    exit 0
fi

echo "Started at: $(date)"
echo "Restoring database..."

# Since our backup script uses pg_dump -c (clean), the SQL file contains DROP TABLE commands.
# We unzip and stream it directly into psql.
gunzip -c "$BACKUP_FILE" | docker exec -i $CONTAINER_NAME psql -U $DB_USER -d $DB_NAME

echo "SUCCESS: Database restored from $BACKUP_FILE"
echo "Finished at: $(date)"
echo "========================================"
