#!/bin/bash
set -e

BUCKET_NAME=${1:-"dojo-terraform-state"}
NAMESPACE=${2:-"<namespace>"}
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="dojo_backup_${DATE}.sql"

echo "=== Dojo Admin - MySQL Backup ==="
echo "Date: $DATE"
echo ""

# Create backup from MySQL pod
MYSQL_POD=$(kubectl get pods -n dojo -l app=mysql -o jsonpath='{.items[0].metadata.name}')

echo "Creating backup from pod: $MYSQL_POD"
kubectl exec -n dojo $MYSQL_POD -- mysqldump -u root -pchange-me-in-production dojo_db > /tmp/$BACKUP_FILE

# Compress backup
gzip /tmp/$BACKUP_FILE
BACKUP_FILE="${BACKUP_FILE}.gz"

echo "Uploading to Object Storage: ${BUCKET_NAME}"
oci os object put \
  --bucket-name $BUCKET_NAME \
  --namespace-name $NAMESPACE \
  --file /tmp/$BACKUP_FILE \
  --name "backups/${BACKUP_FILE}"

# Cleanup
rm /tmp/$BACKUP_FILE

echo ""
echo "=== Backup Complete ==="
echo "File: ${BACKUP_FILE}"
echo "Location: ${BUCKET_NAME}/backups/${BACKUP_FILE}"
