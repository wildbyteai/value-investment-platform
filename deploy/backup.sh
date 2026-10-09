#!/bin/bash
# Daily database backup:  0 3 * * * /opt/vip/deploy/backup.sh >> /var/log/vip-backup.log 2>&1
# Keeps 14 days locally. COPY THE FILES OFF THIS MACHINE (rsync/object storage) — a backup on the
# same disk does not survive losing the server. Dumps contain business data: keep them private.
set -euo pipefail
cd "$(dirname "$0")"
DIR=${VIP_BACKUP_DIR:-/var/backups/vip}
KEEP_DAYS=${VIP_BACKUP_KEEP_DAYS:-14}
umask 077
mkdir -p "$DIR"
FILE="$DIR/vip-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T db pg_dump -U postgres -d vip -Fc > "$FILE.part"
mv "$FILE.part" "$FILE"
find "$DIR" -name 'vip-*.dump' -mtime +"$KEEP_DAYS" -delete
echo "$(date -Is) backup ok: $FILE ($(du -h "$FILE" | cut -f1))"
# Restore into an empty database:
#   docker compose exec -T db pg_restore -U postgres -d vip --clean --if-exists < vip-YYYYMMDD-HHMMSS.dump
