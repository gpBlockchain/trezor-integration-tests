#!/usr/bin/env bash

set -euo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/common.sh"

PYTHON_BIN="${PYTHON_BIN:-python3.9}"
TRANSPORT="${TREZOR_TRANSPORT:-webusb:000:1}"
TREZORCTL_ARG="${TREZORCTL:-auto}"
RPC_URL="${CKB_RPC_URL:-http://testnet.ckb.dev}"
CASE_FILE="${ONCHAIN_CASE_FILE:-cases.testnet.hardware.json}"
ARTIFACT_DIR="${ARTIFACT_DIR:-runs/pytest-regression}"
INCLUDE_SLOW=0
TARGETS=("tests")
EXTRA_ARGS=()

usage() {
  cat <<'USAGE'
Usage: scripts/run_regression.sh [options] [-- pytest-args...]

Run the CKB Trezor pytest regression suite with the committed hardware case file.
By default this runs normal generated fixtures and skips slow/manual boundary cases.

Options:
  --transport VALUE        Trezor transport, default webusb:000:1.
  --trezorctl PATH|auto    trezorctl executable, default auto.
  --rpc-url URL            CKB RPC URL, default http://testnet.ckb.dev.
  --case-file FILE         On-chain case file, default cases.testnet.hardware.json.
  --artifact-dir DIR       Artifact dir under ckb-pytest, default runs/pytest-regression.
  --include-slow           Also allow pytest slow marker cases.
  --target TARGET          Pytest target, default tests. Can be repeated.
  -h, --help               Show this help.

Examples:
  scripts/run_regression.sh
  scripts/run_regression.sh --transport auto
  scripts/run_regression.sh --include-slow --target tests/test_boundary.py
  scripts/run_regression.sh -- -k 'not mainnet'
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --transport)
      TRANSPORT="${2:-}"
      shift 2
      ;;
    --trezorctl)
      TREZORCTL_ARG="${2:-}"
      shift 2
      ;;
    --rpc-url)
      RPC_URL="${2:-}"
      shift 2
      ;;
    --case-file)
      CASE_FILE="${2:-}"
      shift 2
      ;;
    --artifact-dir)
      ARTIFACT_DIR="${2:-}"
      shift 2
      ;;
    --include-slow)
      INCLUDE_SLOW=1
      shift
      ;;
    --target)
      if [[ "${#TARGETS[@]}" -eq 1 && "${TARGETS[0]}" == "tests" ]]; then
        TARGETS=()
      fi
      TARGETS+=("${2:-}")
      shift 2
      ;;
    --)
      shift
      EXTRA_ARGS+=("$@")
      break
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

require_cmd "${PYTHON_BIN}"

PYTEST_ARGS=(
  -s
  "${TARGETS[@]}"
  --run-device
  --run-onchain
  --trezor-transport "${TRANSPORT}"
  --trezorctl "${TREZORCTL_ARG}"
  --onchain-case-file "${CASE_FILE}"
  --ckb-rpc-url "${RPC_URL}"
  --artifact-dir "${ARTIFACT_DIR}"
  --trezorctl-debug
)

if [[ "${INCLUDE_SLOW}" -eq 1 ]]; then
  PYTEST_ARGS+=(--run-slow)
else
  PYTEST_ARGS+=(-m "not slow")
fi

PYTEST_ARGS+=("${EXTRA_ARGS[@]}")

echo "CKB pytest regression"
echo "  transport:    ${TRANSPORT}"
echo "  trezorctl:    ${TREZORCTL_ARG}"
echo "  rpc url:      ${RPC_URL}"
echo "  case file:    ${CASE_FILE}"
echo "  artifact dir: ${ARTIFACT_DIR}"
echo "  include slow: ${INCLUDE_SLOW}"
echo

cd "${REPO_ROOT}/ckb-pytest"
NO_PROXY="${NO_PROXY:-*}" no_proxy="${no_proxy:-*}" run_cmd \
  "${PYTHON_BIN}" -m pytest "${PYTEST_ARGS[@]}"
