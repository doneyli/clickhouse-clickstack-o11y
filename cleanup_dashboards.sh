#!/usr/bin/env bash
# cleanup_dashboards.sh — Delete all HyperDX dashboards created during demos
#
# Usage:
#   ./cleanup_dashboards.sh          # Interactive: lists dashboards and asks for confirmation
#   ./cleanup_dashboards.sh --force   # Non-interactive: deletes all without asking

set -euo pipefail

API_URL="http://localhost:8000"

# Get auth token
TOKEN=$(docker exec hyperdx-local mongo --quiet --eval \
  'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)' 2>/dev/null)

if [[ -z "$TOKEN" ]]; then
  echo "ERROR: Could not retrieve auth token. Is the HyperDX container running?"
  echo "  Try: docker compose up -d"
  exit 1
fi

# Fetch all dashboards
DASHBOARDS=$(curl -s -H "Authorization: Bearer $TOKEN" "$API_URL/api/v1/dashboards")

# Parse dashboard IDs and names
COUNT=$(echo "$DASHBOARDS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('data',[])))" 2>/dev/null || echo "0")

if [[ "$COUNT" == "0" ]]; then
  echo "No dashboards found. Nothing to clean up."
  exit 0
fi

echo "Found $COUNT dashboard(s):"
echo ""
echo "$DASHBOARDS" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', [])
for i, d in enumerate(data, 1):
    print(f'  {i}. {d.get(\"name\", \"(unnamed)\")}  [id: {d[\"id\"]}]')
"
echo ""

# Check for --force flag
if [[ "${1:-}" != "--force" ]]; then
  read -p "Delete ALL $COUNT dashboard(s)? [y/N] " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# Delete each dashboard
echo ""
echo "$DASHBOARDS" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', [])
for d in data:
    print(d['id'])
" | while read -r id; do
  name=$(echo "$DASHBOARDS" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', [])
for d in data:
    if d['id'] == '$id':
        print(d.get('name', '(unnamed)'))
        break
")
  status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
    -H "Authorization: Bearer $TOKEN" \
    "$API_URL/api/v1/dashboards/$id")
  if [[ "$status" == "200" ]]; then
    echo "  Deleted: $name"
  else
    echo "  FAILED ($status): $name [id: $id]"
  fi
done

echo ""
echo "Cleanup complete."
