#!/bin/bash

# Exit on any error
set -e

echo "========================================"
echo "V4 Studio - Database Backup Script"
echo "========================================"

# Configuration
CONTAINER_NAME="v4_studio_postgres_prod"
DB_USER="v4_studio_user"
DB_NAME="v4_studio"
BACKUP_DIR="$(pwd)/backups/db"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/v4_studio_db_$TIMESTAMP.sql.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Started at: $(date)"
echo "Target: $BACKUP_FILE"

# Ensure container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: Container $CONTAINER_NAME is not running."
    exit 1
fi

# Execute pg_dump and pipe directly into gzip on the host
echo "Dumping and compressing database..."
docker exec -t $CONTAINER_NAME pg_dump -U $DB_USER -d $DB_NAME -c -O | gzip > "$BACKUP_FILE"

# Verify backup integrity
echo "Verifying backup integrity..."
if gzip -t "$BACKUP_FILE"; then
    echo "SUCCESS: Backup integrity verified."
else
    echo "ERROR: Backup integrity check failed. The file may be corrupt."
    # Remove the corrupted file
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Apply retention policy
echo "Applying retention policy (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "v4_studio_db_*.sql.gz" -type f -mtime +$RETENTION_DAYS -exec rm -f {} \;
echo "Old backups cleaned up."

# Print size
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup completed successfully. Size: $FILE_SIZE"
echo "Finished at: $(date)"
echo "========================================"
