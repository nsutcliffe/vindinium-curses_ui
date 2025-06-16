#!/bin/bash
# Vindinium Database Backup Script
# This script creates a backup of the MongoDB data that can be committed to Git

set -e

BACKUP_DIR="./db-backup"
DATE=$(date +"%Y%m%d_%H%M%S")

echo "Creating MongoDB backup..."

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Export MongoDB data to JSON files
docker exec mongodb mongodump --db vindinium --out /tmp/backup

# Check if backup was created (database might be empty)
if docker exec mongodb test -d /tmp/backup/vindinium; then
    docker cp mongodb:/tmp/backup/vindinium "$BACKUP_DIR/latest"
else
    echo "Database appears to be empty, creating empty backup structure"
    mkdir -p "$BACKUP_DIR/latest"
    echo "{}" > "$BACKUP_DIR/latest/empty_db.json"
fi

# Also create a timestamped backup
cp -r "$BACKUP_DIR/latest" "$BACKUP_DIR/backup_$DATE"

echo "Database backup completed in $BACKUP_DIR/latest"
echo "Timestamped backup saved as $BACKUP_DIR/backup_$DATE"
echo "You can now commit these files to Git to persist the database state."

