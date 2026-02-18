#!/usr/bin/env bash
# cleanup_dashboards.sh — Delete all ClickStack dashboards created during demos
#
# Usage:
#   ./cleanup_dashboards.sh          # Interactive: lists dashboards and asks for confirmation
#   ./cleanup_dashboards.sh --force   # Non-interactive: deletes all without asking

set -euo pipefail

API_URL="http://localhost:8000"

# Fetch all dashboards (no auth needed for ClickStack local mode)
DASHBOARDS=$(curl -s "$API_URL/dashboards")

# Parse dashboard count
COUNT=$(echo "$DASHBOARDS" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")

if [[ "$COUNT" == "0" ]]; then
  echo "No dashboards found. Nothing to clean up."
  exit 0
fi

echo "Found $COUNT dashboard(s):"
echo ""
echo "$DASHBOARDS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
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
data = json.load(sys.stdin)
for d in data:
    print(d['id'])
" | while read -r id; do
  name=$(echo "$DASHBOARDS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for d in data:
    if d['id'] == '$id':
        print(d.get('name', '(unnamed)'))
        break
")
  status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$API_URL/dashboards/$id")
  if [[ "$status" == "204" || "$status" == "200" ]]; then
    echo "  Deleted: $name"
  else
    echo "  FAILED ($status): $name [id: $id]"
  fi
done

echo ""
echo "Cleanup complete."
