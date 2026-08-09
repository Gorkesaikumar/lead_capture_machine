#!/bin/bash

# Exit on any error
set -e

echo "========================================"
echo "V4 Studio - Media Volume Backup Script"
echo "========================================"

# Configuration
VOLUME_NAME="v4-studio_media_volume"
BACKUP_DIR="$(pwd)/backups/media"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/v4_studio_media_$TIMESTAMP.tar.gz"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Started at: $(date)"
echo "Target: $BACKUP_FILE"

# Run a transient Alpine container to archive the Docker volume
# -v mounts the target volume to /media
# -v mounts the host backup dir to /backup
echo "Archiving persistent media volume ($VOLUME_NAME)..."
docker run --rm \
    -v "$VOLUME_NAME:/media:ro" \
    -v "$BACKUP_DIR:/backup" \
    alpine \
    tar -czf "/backup/$(basename "$BACKUP_FILE")" -C /media .

# Verify backup exists and is not empty
if [ -s "$BACKUP_FILE" ]; then
    echo "SUCCESS: Media volume archived."
else
    echo "ERROR: Backup file is empty or failed to create."
    exit 1
fi

# Verify tarball integrity
echo "Verifying backup integrity..."
if tar -tzf "$BACKUP_FILE" >/dev/null; then
    echo "SUCCESS: Backup integrity verified."
else
    echo "ERROR: Backup integrity check failed. The file may be corrupt."
    # Remove the corrupted file
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Apply retention policy
echo "Applying retention policy (keeping last $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "v4_studio_media_*.tar.gz" -type f -mtime +$RETENTION_DAYS -exec rm -f {} \;
echo "Old backups cleaned up."

# Print size
FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup completed successfully. Size: $FILE_SIZE"
echo "Finished at: $(date)"
echo "========================================"
