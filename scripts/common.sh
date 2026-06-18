#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

usage_error() {
  echo "error: $*" >&2
  exit 2
}

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    usage_error "required command not found: ${cmd}"
  fi
}

resolve_firmware_dir() {
  local configured="${1:-}"
  local candidate=""

  if [[ -n "${configured}" ]]; then
    candidate="${configured}"
  elif [[ -n "${TREZOR_FIRMWARE_DIR:-}" ]]; then
    candidate="${TREZOR_FIRMWARE_DIR}"
  elif [[ -d "${REPO_ROOT}/../trezor-firmware" ]]; then
    candidate="${REPO_ROOT}/../trezor-firmware"
  fi

  if [[ -z "${candidate}" ]]; then
    usage_error "trezor-firmware repo not found. Pass --firmware-dir or set TREZOR_FIRMWARE_DIR."
  fi
  if [[ ! -f "${candidate}/Makefile" || ! -f "${candidate}/core/Makefile" ]]; then
    usage_error "not a trezor-firmware checkout: ${candidate}"
  fi

  (cd "${candidate}" && pwd -P)
}

resolve_trezorctl_bin() {
  local configured="${1:-auto}"
  local firmware_dir="${2:-}"

  if [[ -n "${configured}" && "${configured}" != "auto" ]]; then
    echo "${configured}"
    return
  fi
  if [[ -n "${TREZORCTL:-}" ]]; then
    echo "${TREZORCTL}"
    return
  fi
  if command -v trezorctl >/dev/null 2>&1; then
    command -v trezorctl
    return
  fi
  if [[ -n "${firmware_dir}" && -x "${firmware_dir}/.venv/bin/trezorctl" ]]; then
    echo "${firmware_dir}/.venv/bin/trezorctl"
    return
  fi

  usage_error "trezorctl not found. Run scripts/prepare_trezorctl.sh, set TREZORCTL, or pass --trezorctl."
}

run_cmd() {
  echo "+ $*"
  "$@"
}
