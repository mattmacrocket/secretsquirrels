#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib/common.sh
source "${SCRIPT_DIR}/../scripts/lib/common.sh"

BASE_DIR_INPUT="${1:-/Users/matt/code}"
BASE_DIR="$(validate_base_dir "${BASE_DIR_INPUT}")"

check_repo() {
  local name="$1"
  local key_file="$2"
  local output_file="$3"
  local path="${BASE_DIR}/${name}"

  {
    printf 'Checking %s...\n' "${name}"

    if [[ ! -d "${path}/.git" ]]; then
      printf '  FAIL: missing git repo at %s\n' "${path}"
      exit 1
    fi

    if [[ -z "${key_file}" ]]; then
      printf '  FAIL: missing verification_key in config for %s\n' "${name}"
      exit 1
    fi

    if [[ ! -f "${path}/${key_file}" ]]; then
      printf '  FAIL: missing %s\n' "${key_file}"
      exit 1
    fi

    git -C "${path}" rev-parse --is-inside-work-tree >/dev/null
    printf '  OK\n'
  } > "${output_file}" 2>&1
}

temp_dir="$(mktemp -d)"
cleanup() {
  rm -rf "${temp_dir}"
}
trap cleanup EXIT

declare -a pids=()
declare -a names=()
declare -a output_files=()

while IFS='|' read -r name _repo_url verification_key; do
  [[ -z "${name}" ]] && continue

  output_file="${temp_dir}/${name}.log"
  check_repo "${name}" "${verification_key}" "${output_file}" &
  pids+=("$!")
  names+=("${name}")
  output_files+=("${output_file}")
done < <(load_runtime_projects)

if [[ ${#pids[@]} -eq 0 ]]; then
  die "No runtime projects found in ${PROJECTS_CONFIG}"
fi

failures=0
for i in "${!pids[@]}"; do
  if ! wait "${pids[$i]}"; then
    failures=$((failures + 1))
  fi
  cat "${output_files[$i]}"
done

if [[ ${failures} -gt 0 ]]; then
  printf 'Smoke check failed (%s issues).\n' "${failures}"
  exit 1
fi

printf 'Smoke check passed.\n'
