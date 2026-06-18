#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"

FIRMWARE_DIR_ARG=""
SKIP_SUBMODULES=0
WRITE_PYTEST_LOCAL=0

usage() {
  cat <<'USAGE'
Usage: scripts/prepare_trezorctl.sh [options]

Prepare source-built trezorctl from a trezor-firmware checkout.

Options:
  --firmware-dir DIR       Path to trezor-firmware checkout.
  --skip-submodules        Do not run git submodule update.
  --write-pytest-local     Write ckb-pytest/pytest.local.json if it does not exist.
  -h, --help               Show this help.

Environment:
  TREZOR_FIRMWARE_DIR      Default firmware checkout path.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --firmware-dir)
      FIRMWARE_DIR_ARG="${2:-}"
      shift 2
      ;;
    --skip-submodules)
      SKIP_SUBMODULES=1
      shift
      ;;
    --write-pytest-local)
      WRITE_PYTEST_LOCAL=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage_error "unknown argument: $1"
      ;;
  esac
done

FIRMWARE_DIR="$(resolve_firmware_dir "${FIRMWARE_DIR_ARG}")"
require_cmd uv
require_cmd git

if [[ "${SKIP_SUBMODULES}" -eq 0 ]]; then
  run_cmd git -C "${FIRMWARE_DIR}" submodule update --init --recursive
fi

run_cmd uv --directory "${FIRMWARE_DIR}" sync

TREZORCTL_BIN="${FIRMWARE_DIR}/.venv/bin/trezorctl"
if [[ ! -x "${TREZORCTL_BIN}" ]]; then
  usage_error "trezorctl was not created at ${TREZORCTL_BIN}"
fi

run_cmd "${TREZORCTL_BIN}" --help >/dev/null

if [[ "${WRITE_PYTEST_LOCAL}" -eq 1 ]]; then
  LOCAL_CONFIG="${REPO_ROOT}/ckb-pytest/pytest.local.json"
  if [[ -e "${LOCAL_CONFIG}" ]]; then
    echo "pytest.local.json already exists, keeping it unchanged: ${LOCAL_CONFIG}"
  else
    cat > "${LOCAL_CONFIG}" <<JSON
{
  "run_device": true,
  "run_onchain": true,
  "trezor_transport": "webusb:000:1",
  "trezorctl": "${TREZORCTL_BIN}",
  "onchain_case_file": "cases.testnet.hardware.json",
  "ckb_rpc_url": "http://testnet.ckb.dev",
  "artifact_dir": "runs/pytest-local",
  "env": {
    "NO_PROXY": "*",
    "no_proxy": "*"
  }
}
JSON
    echo "wrote ${LOCAL_CONFIG}"
  fi
fi

echo
echo "trezorctl is ready:"
echo "  ${TREZORCTL_BIN}"
echo
echo "For this shell:"
echo "  export TREZORCTL='${TREZORCTL_BIN}'"
