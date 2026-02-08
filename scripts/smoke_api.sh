#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"

echo "Health:"
curl -s "$BASE_URL/healthz" | cat

echo "\nProfile:"
curl -s "$BASE_URL/api/user/profile" | cat

echo "\nDocs list:"
curl -s "$BASE_URL/api/documents/list" | cat
