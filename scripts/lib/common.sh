#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd -P)"
PROJECTS_CONFIG="${PROJECTS_CONFIG:-${REPO_ROOT}/config/projects.yaml}"

log() {
  printf '%s\n' "$*"
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

trim_spaces() {
  local value="$1"
  value="${value#${value%%[![:space:]]*}}"
  value="${value%${value##*[![:space:]]}}"
  printf '%s\n' "${value}"
}

path_within_root() {
  local path="$1"
  local root="$2"
  [[ "${path}" == "${root}" || "${path}" == "${root}/"* ]]
}

canonicalize_path() {
  local input_path="$1"
  local absolute_path="${input_path}"
  local parent=""
  local name=""

  if [[ "${absolute_path}" != /* ]]; then
    absolute_path="$(pwd -P)/${absolute_path}"
  fi

  parent="$(dirname "${absolute_path}")"
  name="$(basename "${absolute_path}")"

  mkdir -p "${parent}"
  parent="$(cd "${parent}" && pwd -P)"
  printf '%s/%s\n' "${parent}" "${name}"
}

default_allowed_roots() {
  local roots="/Users/matt/code"
  if [[ -n "${RUNNER_TEMP:-}" ]]; then
    roots="${roots},${RUNNER_TEMP}"
  fi
  printf '%s\n' "${roots}"
}

validate_base_dir() {
  local raw_base_dir="$1"
  local allowed_roots="${ALLOWED_BASE_ROOTS:-$(default_allowed_roots)}"
  local resolved_base_dir=""

  resolved_base_dir="$(canonicalize_path "${raw_base_dir}")"
  mkdir -p "${resolved_base_dir}"
  resolved_base_dir="$(cd "${resolved_base_dir}" && pwd -P)"

  local allowed="false"
  local root=""
  IFS=',' read -r -a root_list <<< "${allowed_roots}"
  for root in "${root_list[@]}"; do
    root="$(trim_spaces "${root}")"
    [[ -z "${root}" ]] && continue

    local resolved_root=""
    resolved_root="$(canonicalize_path "${root}")"
    mkdir -p "${resolved_root}"
    resolved_root="$(cd "${resolved_root}" && pwd -P)"

    if path_within_root "${resolved_base_dir}" "${resolved_root}"; then
      allowed="true"
      break
    fi
  done

  if [[ "${allowed}" != "true" ]]; then
    die "BASE_DIR '${resolved_base_dir}' is outside ALLOWED_BASE_ROOTS='${allowed_roots}'"
  fi

  printf '%s\n' "${resolved_base_dir}"
}

owner_allowed() {
  local owner="$1"
  local allowed_orgs="${ALLOWED_GITHUB_ORGS:-mattmacrocket}"
  local org=""

  IFS=',' read -r -a org_list <<< "${allowed_orgs}"
  for org in "${org_list[@]}"; do
    org="$(trim_spaces "${org}")"
    if [[ "${owner}" == "${org}" ]]; then
      return 0
    fi
  done

  return 1
}

parse_repo_url() {
  local repo_url="$1"

  if [[ "${repo_url}" =~ ^ssh://git@github\.com/([^/]+)/([^/]+)\.git$ ]]; then
    printf '%s|%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "${repo_url}" =~ ^git@github\.com:([^/]+)/([^/]+)\.git$ ]]; then
    printf '%s|%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  if [[ "${repo_url}" =~ ^https://([^@/]+@)?github\.com/([^/]+)/([^/]+)\.git$ ]]; then
    printf '%s|%s\n' "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
    return 0
  fi

  if [[ "${repo_url}" =~ ^https://github\.com/([^/]+)/([^/]+)\.git$ ]]; then
    printf '%s|%s\n' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}"
    return 0
  fi

  return 1
}

repo_url_for_protocol() {
  local repo_url="$1"
  local clone_protocol="$2"
  local parsed=""
  local owner=""
  local repo_name=""

  parsed="$(parse_repo_url "${repo_url}")" || die "Unsupported repository URL format: ${repo_url}"
  owner="${parsed%%|*}"
  repo_name="${parsed##*|}"

  if ! owner_allowed "${owner}"; then
    die "Repository owner '${owner}' is not in ALLOWED_GITHUB_ORGS='${ALLOWED_GITHUB_ORGS:-mattmacrocket}'"
  fi

  if [[ "${clone_protocol}" == "https" ]]; then
    printf 'https://github.com/%s/%s.git\n' "${owner}" "${repo_name}"
    return 0
  fi

  printf 'git@github.com:%s/%s.git\n' "${owner}" "${repo_name}"
}

load_runtime_projects() {
  [[ -f "${PROJECTS_CONFIG}" ]] || die "Missing config file: ${PROJECTS_CONFIG}"

  awk '
    function flush_project() {
      if (in_project && role == "runtime") {
        if (name == "" || repo == "") {
          printf "ERROR: invalid runtime project in %s\n", FILENAME > "/dev/stderr"
          exit 2
        }
        print name "|" repo "|" verification_key
      }
    }

    /^[[:space:]]*-[[:space:]]+name:[[:space:]]*/ {
      flush_project()
      in_project = 1
      name = $3
      repo = ""
      role = ""
      verification_key = ""
      next
    }

    /^[^[:space:]].*:[[:space:]]*$/ {
      flush_project()
      in_project = 0
      next
    }

    in_project && /^[[:space:]]*repo:[[:space:]]*/ {
      repo = $2
      next
    }

    in_project && /^[[:space:]]*role:[[:space:]]*/ {
      role = $2
      next
    }

    in_project && /^[[:space:]]*verification_key:[[:space:]]*/ {
      verification_key = $2
      next
    }

    END {
      flush_project()
    }
  ' "${PROJECTS_CONFIG}"
}

setup_clone_protocol() {
  local protocol="${CLONE_PROTOCOL:-}"

  if [[ -z "${protocol}" ]]; then
    if [[ "${CI:-}" == "true" || "${GITHUB_ACTIONS:-}" == "true" ]]; then
      protocol="https"
    else
      protocol="ssh"
    fi
  fi

  if [[ "${protocol}" != "ssh" && "${protocol}" != "https" ]]; then
    die "Invalid CLONE_PROTOCOL '${protocol}'. Use 'ssh' or 'https'."
  fi

  printf '%s\n' "${protocol}"
}

find_timeout_bin() {
  if command -v timeout >/dev/null 2>&1; then
    printf 'timeout\n'
    return
  fi

  if command -v gtimeout >/dev/null 2>&1; then
    printf 'gtimeout\n'
    return
  fi

  printf '\n'
}

run_with_timeout() {
  local seconds="$1"
  shift

  local timeout_bin=""
  timeout_bin="$(find_timeout_bin)"

  if [[ -n "${timeout_bin}" ]]; then
    "${timeout_bin}" --foreground "${seconds}" "$@"
    return
  fi

  "$@"
}

setup_askpass() {
  local clone_protocol="$1"

  if [[ "${clone_protocol}" != "https" ]]; then
    printf '\n'
    return
  fi

  if [[ -z "${GH_ACCESS_TOKEN:-${GITHUB_TOKEN:-}}" ]]; then
    printf '\n'
    return
  fi

  local askpass_script=""
  askpass_script="$(mktemp)"
  cat > "${askpass_script}" <<'ASKPASS'
#!/usr/bin/env bash
case "$1" in
  *Username*)
    printf '%s\n' "x-access-token"
    ;;
  *Password*)
    printf '%s\n' "${GH_ACCESS_TOKEN:-${GITHUB_TOKEN:-}}"
    ;;
  *)
    printf '\n'
    ;;
esac
ASKPASS
  chmod 700 "${askpass_script}"
  printf '%s\n' "${askpass_script}"
}

git_run() {
  local timeout_seconds="$1"
  local askpass_script="$2"
  shift 2

  if [[ -n "${askpass_script}" ]]; then
    GIT_TERMINAL_PROMPT=0 GIT_ASKPASS="${askpass_script}" run_with_timeout "${timeout_seconds}" git "$@"
    return
  fi

  run_with_timeout "${timeout_seconds}" git "$@"
}
