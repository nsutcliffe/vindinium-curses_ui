# Vindinium Database Persistence

This setup provides a simple Vindinium server with MongoDB persistence that can be backed up to Git.

## Features

- **No Authentication**: MongoDB runs without authentication for simplicity
- **Persistent Data**: Database state is maintained between container restarts
- **Git Backup**: Database state can be backed up and committed to Git
- **Easy Restore**: Database can be restored from Git-backed backups

## Quick Start

1. **Start the application**:
   ```bash
   docker-compose up -d
   ```

2. **Access Vindinium**: Open http://localhost in your browser

3. **Backup database state**:
   ```bash
   ./backup-db.sh
   ```

4. **Commit to Git**:
   ```bash
   git add db-backup/
   git commit -m "Update database state"
   git push
   ```

## Database Management

### Backup Database
```bash
./backup-db.sh
```
This creates JSON exports of your MongoDB collections in `db-backup/latest/` and a timestamped backup.

### Restore Database
```bash
./restore-db.sh
```
This restores the database from the latest backup in `db-backup/latest/`.

### Reset Database
To completely reset the database:
```bash
docker-compose down
sudo rm -rf mongodb-data
mkdir mongodb-data
docker-compose up -d
```

## File Structure

- `docker-compose.yml` - Main Docker configuration
- `mongodb-data/` - Actual MongoDB data (excluded from Git)
- `db-backup/` - Database backups (included in Git)
- `backup-db.sh` - Script to backup database
- `restore-db.sh` - Script to restore database

## Git Workflow

The setup is designed so that:
1. `mongodb-data/` is excluded from Git (too large and binary)
2. `db-backup/` is included in Git for state persistence
3. You can share database state by committing backups to Git
4. Others can restore your database state using the restore script

This gives you the benefits of database persistence without the complexity of authentication or large binary files in Git.

