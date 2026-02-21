#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
STACK_DIR="${REPO_ROOT}/harness/opencti"
COMPOSE_FILE="${STACK_DIR}/docker-compose.yml"
ENV_EXAMPLE="${STACK_DIR}/opencti.env.example"
ENV_FILE="${STACK_DIR}/.env"

usage() {
  cat <<'USAGE'
Usage: ./scripts/opencti/start_stack.sh <command>

Commands:
  phase1   Start OpenCTI core + MITRE connector
  phase2   Start/enable ClownPeanuts TAXII2 connector profile
  down     Stop and remove stack resources
  ps       Show container status
  logs     Tail stack logs
USAGE
}

require_bin() {
  local name="$1"
  if ! command -v "${name}" >/dev/null 2>&1; then
    printf 'ERROR: required command not found: %s\n' "${name}" >&2
    exit 1
  fi
}

ensure_docker_compose() {
  if docker compose version >/dev/null 2>&1; then
    return 0
  fi
  printf 'ERROR: docker compose is required.\n' >&2
  exit 1
}

uuid_lower() {
  uuidgen | tr '[:upper:]' '[:lower:]'
}

random_token() {
  openssl rand -hex 24
}

read_env_value() {
  local key="$1"
  local value=""
  value="$(awk -F'=' -v k="${key}" '$1==k {print substr($0, index($0, "=") + 1)}' "${ENV_FILE}" | tail -n 1)"
  printf '%s\n' "${value}"
}

set_env_value() {
  local key="$1"
  local value="$2"

  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
    rm -f "${ENV_FILE}.bak"
    return 0
  fi

  printf '%s=%s\n' "${key}" "${value}" >> "${ENV_FILE}"
}

ensure_env_file() {
  if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
  fi

  local key=""
  for key in \
    OPENCTI_ADMIN_PASSWORD \
    OPENCTI_ADMIN_TOKEN \
    OPENCTI_HEALTHCHECK_ACCESS_KEY \
    MINIO_ROOT_PASSWORD \
    RABBITMQ_DEFAULT_PASS \
    CONNECTOR_OPENCTI_ID \
    CONNECTOR_MITRE_ID \
    CONNECTOR_TAXII2_ID; do
    local current=""
    current="$(read_env_value "${key}")"
    if [[ -n "${current}" ]]; then
      continue
    fi

    case "${key}" in
      CONNECTOR_OPENCTI_ID|CONNECTOR_MITRE_ID|CONNECTOR_TAXII2_ID|OPENCTI_ADMIN_TOKEN)
        set_env_value "${key}" "$(uuid_lower)"
        ;;
      *)
        set_env_value "${key}" "$(random_token)"
        ;;
    esac
  done
}

compose() {
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" "$@"
}

print_access_details() {
  local port=""
  local email=""
  local password=""
  local token=""

  port="$(read_env_value OPENCTI_PORT)"
  email="$(read_env_value OPENCTI_ADMIN_EMAIL)"
  password="$(read_env_value OPENCTI_ADMIN_PASSWORD)"
  token="$(read_env_value OPENCTI_ADMIN_TOKEN)"

  printf 'OpenCTI URL: http://localhost:%s\n' "${port}"
  printf 'OpenCTI admin email: %s\n' "${email}"
  printf 'OpenCTI admin password: %s\n' "${password}"
  printf 'OpenCTI admin token: %s\n' "${token}"
}

main() {
  local command="${1:-phase1}"

  require_bin docker
  require_bin uuidgen
  require_bin openssl
  ensure_docker_compose
  ensure_env_file

  case "${command}" in
    phase1)
      compose up -d redis elasticsearch minio rabbitmq opencti worker connector-opencti connector-mitre
      print_access_details
      ;;
    phase2)
      compose up -d redis elasticsearch minio rabbitmq opencti worker connector-opencti connector-mitre
      compose --profile clownpeanuts up -d connector-taxii2
      print_access_details
      ;;
    down)
      compose --profile clownpeanuts down
      ;;
    ps)
      compose --profile clownpeanuts ps
      ;;
    logs)
      compose --profile clownpeanuts logs -f --tail=200
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
