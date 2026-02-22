#!/usr/bin/env bash
set -euo pipefail

API_BASE="${1:-http://127.0.0.1:8199}"
TOKEN="${CONTROLPANE_API_AUTH_TOKEN:-}"

request() {
  local path="$1"
  local url="${API_BASE%/}${path}"
  local body_file
  body_file="$(mktemp)"

  local -a curl_cmd
  if [[ -n "${TOKEN}" ]]; then
    curl_cmd=(curl -sS -H "Authorization: Bearer ${TOKEN}" -o "${body_file}" -w "%{http_code}" "${url}")
  else
    curl_cmd=(curl -sS -o "${body_file}" -w "%{http_code}" "${url}")
  fi

  local code
  code="$("${curl_cmd[@]}")"
  if [[ "${code}" != "200" ]]; then
    echo "FAIL ${path} -> HTTP ${code}" >&2
    echo "---- response ----" >&2
    cat "${body_file}" >&2
    rm -f "${body_file}"
    return 1
  fi

  echo "OK   ${path}"
  rm -f "${body_file}"
}

echo "Control-plane smoke against ${API_BASE}"
request "/health"
request "/overview/summary"
request "/sentry/summary"
request "/sentry/findings?limit=1"
request "/orchestration/summary"

echo "Control-plane smoke passed."
