#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

BASE_DIR_INPUT="${1:-/Users/matt/code}"
BASE_DIR="$(validate_base_dir "${BASE_DIR_INPUT}")"
CLONE_PROTOCOL="$(setup_clone_protocol)"
ASKPASS_SCRIPT="$(setup_askpass "${CLONE_PROTOCOL}")"

GIT_CLONE_TIMEOUT_SEC="${GIT_CLONE_TIMEOUT_SEC:-300}"
GIT_FETCH_TIMEOUT_SEC="${GIT_FETCH_TIMEOUT_SEC:-120}"
GIT_PULL_TIMEOUT_SEC="${GIT_PULL_TIMEOUT_SEC:-120}"

cleanup() {
  if [[ -n "${ASKPASS_SCRIPT}" && -f "${ASKPASS_SCRIPT}" ]]; then
    rm -f "${ASKPASS_SCRIPT}"
  fi
}
trap cleanup EXIT

if [[ -z "$(find_timeout_bin)" ]]; then
  printf 'WARN: timeout utility not found; git operations will run without hard time limits.\n' >&2
fi

clone_or_update() {
  local name="$1"
  local repo_config_url="$2"
  local target_path="${BASE_DIR}/${name}"
  local expected_repo_url=""

  expected_repo_url="$(repo_url_for_protocol "${repo_config_url}" "${CLONE_PROTOCOL}")"

  if [[ -d "${target_path}/.git" ]]; then
    log "[update] ${name}"

    local current_remote=""
    current_remote="$(git -C "${target_path}" remote get-url origin 2>/dev/null || true)"
    if [[ -n "${current_remote}" ]]; then
      local expected_slug=""
      local current_slug=""

      expected_slug="$(parse_repo_url "${expected_repo_url}" | cut -d'|' -f1-2)" || die "Unable to parse expected URL for ${name}"
      current_slug="$(parse_repo_url "${current_remote}" | cut -d'|' -f1-2)" || die "Unable to parse current origin URL for ${name}: ${current_remote}"

      if [[ "${expected_slug}" != "${current_slug}" ]]; then
        die "Repository mismatch at ${target_path}; expected ${expected_slug}, found ${current_slug}"
      fi
    fi

    git_run "${GIT_FETCH_TIMEOUT_SEC}" "${ASKPASS_SCRIPT}" -C "${target_path}" fetch --all --prune
    git_run "${GIT_PULL_TIMEOUT_SEC}" "${ASKPASS_SCRIPT}" -C "${target_path}" pull --ff-only
    return
  fi

  log "[clone] ${name}"
  git_run "${GIT_CLONE_TIMEOUT_SEC}" "${ASKPASS_SCRIPT}" clone "${expected_repo_url}" "${target_path}"
}

declare -a pids=()
declare -a names=()

while IFS='|' read -r name repo_url _verification_key; do
  [[ -z "${name}" ]] && continue
  clone_or_update "${name}" "${repo_url}" &
  pids+=("$!")
  names+=("${name}")
done < <(load_runtime_projects)

if [[ ${#pids[@]} -eq 0 ]]; then
  die "No runtime projects found in ${PROJECTS_CONFIG}"
fi

failures=0
for i in "${!pids[@]}"; do
  if ! wait "${pids[$i]}"; then
    printf '[fail] %s\n' "${names[$i]}" >&2
    failures=$((failures + 1))
  fi
done

if [[ ${failures} -gt 0 ]]; then
  die "Bootstrap failed (${failures} project operations failed)."
fi

log "Bootstrap complete."
