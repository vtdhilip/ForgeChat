#!/bin/bash
set -e

# Sync database from production VPS to local Docker PostgreSQL container
VPS_HOST="50.6.44.53"
VPS_USER="root"
LOCAL_CONTAINER="synapticchat-forgecrm-db-1"

echo "=========================================================="
echo " Synaptic Chat: Production VPS -> Local Docker DB Sync"
echo "=========================================================="
echo "VPS: ${VPS_USER}@${VPS_HOST}"
echo "Local DB Container: ${LOCAL_CONTAINER}"
echo ""

if [ -n "$VPS_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
  echo "[1/3] Streaming database dump from VPS using sshpass..."
  sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" \
    "docker exec \$(docker ps -qf name=db) pg_dump -U postgres -d postgres --clean --if-exists" \
    | docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres
else
  echo "[1/3] Streaming database dump from VPS (enter root password if prompted)..."
  ssh -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" \
    "docker exec \$(docker ps -qf name=db) pg_dump -U postgres -d postgres --clean --if-exists" \
    | docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres
fi

echo "[2/3] Applying multi-tenancy migrations (059 through 062)..."
docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres -f /app/db/migrations/059_multi_tenancy.sql 2>/dev/null || \
  docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres < db/migrations/059_multi_tenancy.sql

docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres -f /app/db/migrations/060_agent_close_summary.sql 2>/dev/null || \
  docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres < db/migrations/060_agent_close_summary.sql

docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres -f /app/db/migrations/061_contact_agent_close_pending.sql 2>/dev/null || \
  docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres < db/migrations/061_contact_agent_close_pending.sql

docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres -f /app/db/migrations/062_contact_agent_paused.sql 2>/dev/null || \
  docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres < db/migrations/062_contact_agent_paused.sql

echo "[3/3] Verifying local multi-tenant tables and row counts..."
docker exec -i "$LOCAL_CONTAINER" psql -U postgres -d postgres -c "
SELECT 'organizations' AS entity, count(*) FROM coexistence.organizations
UNION ALL
SELECT 'users', count(*) FROM coexistence.forgecrm_users
UNION ALL
SELECT 'contacts', count(*) FROM coexistence.contacts
UNION ALL
SELECT 'chat_history', count(*) FROM coexistence.chat_history
UNION ALL
SELECT 'whatsapp_accounts', count(*) FROM coexistence.whatsapp_accounts
UNION ALL
SELECT 'orders', count(*) FROM coexistence.orders;
"

echo ""
echo "Database sync and multi-tenancy migration completed successfully!"
