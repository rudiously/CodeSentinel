#!/usr/bin/env bash
set -euo pipefail
api_url="${CODESENTINEL_API_URL:-http://127.0.0.1:8000}"
for attempt in $(seq 1 60); do
  if curl --fail --silent --max-time 2 "$api_url/health" >/dev/null; then exit 0; fi
  sleep 1
done
printf 'ERROR: API did not become healthy\n' >&2
exit 1
