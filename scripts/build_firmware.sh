#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"

FIRMWARE_DIR_ARG=""
TREZOR_MODEL="${TREZOR_MODEL:-T3W1}"
BITCOIN_ONLY="${BITCOIN_ONLY:-0}"
PYOPT="${PYOPT:-1}"
SKIP_SUBMODULES=0
TARGET="build_firmware"

usage() {
  cat <<'USAGE'
Usage: scripts/build_firmware.sh [options]

Build Trezor Core firmware from a trezor-firmware checkout.

Options:
  --firmware-dir DIR       Path to trezor-firmware checkout.
  --model MODEL            TREZOR_MODEL, default T3W1.
  --bitcoin-only 0|1       BITCOIN_ONLY, default 0.
  --debug                  Build with PYOPT=0.
  --target TARGET          Make target, default build_firmware.
  --skip-submodules        Do not run git submodule update.
  -h, --help               Show this help.

Examples:
  scripts/build_firmware.sh --model T3W1 --debug
  scripts/build_firmware.sh --firmware-dir ../trezor-firmware --model T3T1
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --firmware-dir)
      FIRMWARE_DIR_ARG="${2:-}"
      shift 2
      ;;
    --model)
      TREZOR_MODEL="${2:-}"
      shift 2
      ;;
    --bitcoin-only)
      BITCOIN_ONLY="${2:-}"
      shift 2
      ;;
    --debug)
      PYOPT=0
      shift
      ;;
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --skip-submodules)
      SKIP_SUBMODULES=1
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
run_cmd uv --directory "${FIRMWARE_DIR}" run make -C core "${TARGET}" \
  TREZOR_MODEL="${TREZOR_MODEL}" \
  BITCOIN_ONLY="${BITCOIN_ONLY}" \
  PYOPT="${PYOPT}"

FIRMWARE_BIN="${FIRMWARE_DIR}/core/build/firmware/firmware.bin"
if [[ "${TARGET}" == "build_firmware" && ! -f "${FIRMWARE_BIN}" ]]; then
  usage_error "firmware binary not found after build: ${FIRMWARE_BIN}"
fi

echo
echo "firmware build finished"
echo "  firmware dir: ${FIRMWARE_DIR}"
echo "  model:        ${TREZOR_MODEL}"
echo "  artifact:     ${FIRMWARE_BIN}"
