#!/bin/bash
# Vindinium Database Restore Script
# This script restores MongoDB data from Git-backed backup files

set -e

BACKUP_DIR="./db-backup/latest"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "Error: Backup directory $BACKUP_DIR not found."
    echo "Please run backup-db.sh first or ensure the backup files exist."
    exit 1
fi

echo "Restoring MongoDB from backup..."

# Copy backup to container
docker cp "$BACKUP_DIR" mongodb:/tmp/restore

# Restore the database
docker exec mongodb mongorestore --db vindinium --drop /tmp/restore

echo "Database restore completed successfully!"

