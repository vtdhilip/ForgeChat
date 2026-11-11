#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "Generating fresh JWT token for k6 test suite..."
TOKEN=$(docker exec synapticchat-backend python -c "
import jwt, datetime, json
from app.core.config import settings

data = {
    'id': 1,
    'username': 'admin',
    'displayName': 'Admin',
    'role': 'admin',
    'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)
}
print(jwt.encode(data, settings.JWT_SECRET, algorithm='HS256'))
")

echo "Running k6 full test suite against ${BASE_URL}..."
k6 run -e BASE_URL="${BASE_URL}" -e TOKEN="${TOKEN}" "${DIR}/tests/k6/full_suite.js"
