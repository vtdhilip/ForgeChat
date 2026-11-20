#!/bin/bash
set -e

# Deploy latest changes to production VPS
VPS_HOST="${VPS_HOST:-50.6.44.53}"
VPS_USER="${VPS_USER:-root}"
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'feat/fastapi-backend')}"

echo "=========================================================="
echo " Synaptic Chat: VPS Deployment (${BRANCH})"
echo "=========================================================="
echo "VPS Target: ${VPS_USER}@${VPS_HOST}"
echo "Branch:     ${BRANCH}"
echo ""

REMOTE_SCRIPT=$(cat << 'EOF'
set -e

BRANCH="${DEPLOY_BRANCH:-feat/fastapi-backend}"

echo "==> Locating project repository on VPS..."
REPO_DIR=""

# Try docker compose label first
BACKEND_CID=$(docker ps -qf "name=backend" | head -n 1)
if [ -n "$BACKEND_CID" ]; then
  REPO_DIR=$(docker inspect "$BACKEND_CID" --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}' 2>/dev/null || echo "")
fi

# Fallback search if not found from docker label
if [ -z "$REPO_DIR" ] || [ ! -d "$REPO_DIR/.git" ]; then
  for dir in /root/forgechat /root/ForgeChat /root/SynapticChat /root/synapticchat /home/*/forgechat /home/*/ForgeChat /var/www/forgechat; do
    if [ -d "$dir/.git" ]; then
      REPO_DIR="$dir"
      break
    fi
  done
fi

if [ -z "$REPO_DIR" ] || [ ! -d "$REPO_DIR/.git" ]; then
  echo "ERROR: Could not locate git repository directory on VPS."
  exit 1
fi

echo "==> Project directory found: ${REPO_DIR}"
cd "${REPO_DIR}"

echo "==> Fetching latest changes from origin..."
git fetch origin

echo "==> Stashing any local changes on VPS..."
git stash 2>/dev/null || true

echo "==> Checking out branch: ${BRANCH}..."
git checkout "${BRANCH}" 2>/dev/null || git checkout -b "${BRANCH}" "origin/${BRANCH}"
git pull origin "${BRANCH}"

echo "==> Rebuilding and restarting containers..."
if [ -f "docker-compose.prod.yml" ]; then
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
else
  docker compose up -d --build
fi

echo "==> Waiting for services to become healthy (10s)..."
sleep 10

echo "==> Container status:"
docker compose ps

echo "==> Deployment completed successfully!"
EOF
)

SSH_CMD="DEPLOY_BRANCH='${BRANCH}' bash -s"

if [ -n "$VPS_PASSWORD" ] && command -v sshpass >/dev/null 2>&1; then
  echo "Connecting via sshpass with \$VPS_PASSWORD..."
  sshpass -p "$VPS_PASSWORD" ssh -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" "$SSH_CMD" <<< "$REMOTE_SCRIPT"
else
  echo "Connecting via SSH (enter root password if prompted)..."
  ssh -o StrictHostKeyChecking=no "${VPS_USER}@${VPS_HOST}" "$SSH_CMD" <<< "$REMOTE_SCRIPT"
fi
