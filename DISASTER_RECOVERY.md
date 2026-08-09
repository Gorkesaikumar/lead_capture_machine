# V4 Studio - Disaster Recovery & Backup Strategy

This document outlines the backup, retention, and disaster recovery procedures for V4 Studio in a production environment.

## 1. Backup Architecture

Our backup strategy completely isolates backup artifacts from the running Docker containers and their volumes. Backups are pushed to the host machine's filesystem, ensuring that if a Docker volume is accidentally deleted or corrupted, the data is not lost.

- **Storage Location**: By default, backups are saved to `d:\v4-studio\backups/` (or the equivalent `pwd/backups` directory on your Linux host). 
  - Database: `backups/db/`
  - Media: `backups/media/`
- **Compression**: All backups are heavily compressed (`.sql.gz` for databases, `.tar.gz` for media volumes) to conserve disk space.
- **Integrity Validation**: Scripts automatically run integrity checks (e.g. `gzip -t`) against the created backup file. If corruption is detected, the script fails safely.
- **Retention Policy**: 7 Days. Scripts automatically identify and purge backup files older than 7 days.

---

## 2. Automated Backups (Cron)

To enforce the daily backup requirement, you must configure a `cron` job on your production host machine.

Open your crontab on the host server:
```bash
crontab -e
```

Add the following entries to run backups daily at 2:00 AM and 2:30 AM:
```bash
# Run PostgreSQL Backup at 2:00 AM daily
0 2 * * * cd /path/to/v4-studio && bash scripts/backup_database.sh >> /var/log/v4_db_backup.log 2>&1

# Run Media Backup at 2:30 AM daily
30 2 * * * cd /path/to/v4-studio && bash scripts/backup_media.sh >> /var/log/v4_media_backup.log 2>&1
```

---

## 3. Database Restoration Procedure

> [!WARNING]
> Database restoration is destructive. Running this procedure will cleanly wipe the existing database schema and replace it entirely with the snapshot contained in the backup file.

To restore a specific backup snapshot:

1. Ensure the PostgreSQL container is running:
   ```bash
   docker-compose -f docker-compose.production.yml up -d db
   ```
2. Execute the restore script, passing the path to the backup file:
   ```bash
   bash scripts/restore_database.sh backups/db/v4_studio_db_20260810_120000.sql.gz
   ```
3. Type `YES` when prompted to confirm the destructive operation.
4. (Optional) Restart the Django web containers to clear any cached connections:
   ```bash
   docker-compose -f docker-compose.production.yml restart web celery_worker celery_beat
   ```

---

## 4. Media Restoration Procedure

To restore the persistent media volume (which contains all customer-uploaded images):

1. Stop the application containers so no files are being written to the volume:
   ```bash
   docker-compose -f docker-compose.production.yml stop web celery_worker
   ```
2. Run a transient Alpine container to unpack the tarball back into the named volume:
   ```bash
   # Replace the filename with your actual backup file
   BACKUP_FILE="v4_studio_media_20260810_120000.tar.gz"
   
   docker run --rm \
       -v v4-studio_media_volume:/media \
       -v $(pwd)/backups/media:/backup \
       alpine \
       tar -xzf /backup/$BACKUP_FILE -C /media
   ```
3. Restart the containers:
   ```bash
   docker-compose -f docker-compose.production.yml start web celery_worker
   ```

---

## 5. Total Server Loss (Disaster Recovery)

In the event of complete server failure where you only possess offsite backups:

1. Provision a new server and install Docker and Docker Compose.
2. Clone the `v4-studio` repository and setup your `.env.production` file.
3. Boot the environment so Docker creates the empty volumes:
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```
4. Transfer your backup files (`.sql.gz` and `.tar.gz`) to the new server.
5. Restore the Database using the steps in **Section 3**.
6. Restore the Media volume using the steps in **Section 4**.
7. Restart all containers and verify system integrity.
