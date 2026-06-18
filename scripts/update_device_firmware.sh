#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"

FIRMWARE_DIR_ARG=""
FIRMWARE_BIN_ARG=""
TREZORCTL_ARG="auto"
DRY_RUN=0
YES=0

usage() {
  cat <<'USAGE'
Usage: scripts/update_device_firmware.sh [options]

Upload a built firmware image to a connected Trezor device.

This is intentionally opt-in. Without --yes or --dry-run, the script prints the
resolved command and exits without touching the device.

Options:
  --firmware-dir DIR       Path to trezor-firmware checkout.
  --firmware-bin FILE      Firmware image. Default: core/build/firmware/firmware.bin.
  --trezorctl PATH|auto    trezorctl executable, default auto.
  --dry-run                Run trezorctl firmware_update --dry-run only.
  --yes                    Actually upload firmware to the device.
  -h, --help               Show this help.

Device notes:
  Put the device into bootloader/update mode before uploading.
  Locally built development firmware may wipe or invalidate device state.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --firmware-dir)
      FIRMWARE_DIR_ARG="${2:-}"
      shift 2
      ;;
    --firmware-bin)
      FIRMWARE_BIN_ARG="${2:-}"
      shift 2
      ;;
    --trezorctl)
      TREZORCTL_ARG="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --yes)
      YES=1
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
TREZORCTL_BIN="$(resolve_trezorctl_bin "${TREZORCTL_ARG}" "${FIRMWARE_DIR}")"
FIRMWARE_BIN="${FIRMWARE_BIN_ARG:-${FIRMWARE_DIR}/core/build/firmware/firmware.bin}"

if [[ ! -f "${FIRMWARE_BIN}" ]]; then
  usage_error "firmware binary not found: ${FIRMWARE_BIN}. Run scripts/build_firmware.sh first."
fi

COMMAND=("${TREZORCTL_BIN}" firmware_update -s -f "${FIRMWARE_BIN}")
if [[ "${DRY_RUN}" -eq 1 ]]; then
  COMMAND=("${TREZORCTL_BIN}" firmware_update -s -n -f "${FIRMWARE_BIN}")
fi

echo "trezorctl:    ${TREZORCTL_BIN}"
echo "firmware bin: ${FIRMWARE_BIN}"
echo "command:"
printf '  %q' "${COMMAND[@]}"
echo

if [[ "${DRY_RUN}" -eq 1 ]]; then
  run_cmd "${COMMAND[@]}"
  exit 0
fi

if [[ "${YES}" -ne 1 ]]; then
  echo
  echo "Not uploading. Re-run with --yes after putting the device into bootloader/update mode."
  exit 2
fi

echo
echo "Uploading firmware. Confirm all prompts on the device."
run_cmd "${COMMAND[@]}"
