#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8099}"
COLLECTION_ID="${2:-clownpeanuts-intel}"

require_bin() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    printf 'ERROR: required command not found: %s\n' "${name}" >&2
    exit 1
  fi
}

fetch() {
  local path="$1"
  curl -fsSL "${BASE_URL}${path}"
}

main() {
  require_bin curl

  printf 'Checking ClownPeanuts API health...\n'
  fetch "/health" >/dev/null

  printf 'Checking TAXII discovery...\n'
  fetch "/taxii2/" >/dev/null

  printf 'Checking TAXII API root...\n'
  fetch "/taxii2/api/" >/dev/null

  printf 'Checking TAXII collections...\n'
  fetch "/taxii2/api/collections" >/dev/null

  printf 'Checking TAXII manifest for %s...\n' "${COLLECTION_ID}"
  fetch "/taxii2/api/collections/${COLLECTION_ID}/manifest?limit=1" >/dev/null

  printf 'Checking TAXII objects for %s...\n' "${COLLECTION_ID}"
  fetch "/taxii2/api/collections/${COLLECTION_ID}/objects?limit=1" >/dev/null

  printf 'ClownPeanuts TAXII checks passed.\n'
}

main "$@"
