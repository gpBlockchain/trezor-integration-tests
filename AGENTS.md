# Trezor CKB Integration Test Agent Guide

This repository is the standalone CKB integration test project for Trezor.
Preserve the migrated pytest cases, case files, and CCC fixture factory. Do not
replace them with a separate manually written registry.

## Source Files

- `docs/ckb_test_case_analysis_zh.md`: primary case matrix.
- `docs/ckb_test_case_analysis.md`: English case matrix.
- `docs/ckb_tx_fixture_todo_zh.md`: fixture generation and status tracking.
- `docs/ckb_test_run_log_zh.md`: execution evidence.
- `docs/ckb_trezor_test_findings.md`: current findings and unsupported behavior.
- `ckb-pytest/tests/*.py`: pytest cases.
- `ckb-pytest/cases.*.json`: replayable on-chain cases.
- `scripts/*.sh`: local environment, trezorctl, firmware build, and firmware update helpers.
- `tx-factory-ccc/src/*.ts`: fixture builders.
- `tx-factory-ccc/test/*.ts`: fixture builder tests.

## Required Change Order

For new or changed CKB behavior:

1. Update `docs/ckb_test_case_analysis_zh.md`.
2. Update `docs/ckb_tx_fixture_todo_zh.md`.
3. Add or adjust pytest cases under `ckb-pytest/tests/`.
4. Add or adjust CCC fixture recipes under `tx-factory-ccc/src/`.
5. Run focused verification.
6. Update `docs/ckb_test_run_log_zh.md` and `docs/ckb_trezor_test_findings.md` when needed.

## Safety Rules

- Never commit `.env.local`, mnemonics, private keys, seed backups, device PINs, passphrases, or private RPC credentials.
- Do not run real-device, network, manual UI, or slow tests unless explicitly requested.
- Do not submit on-chain transactions without explicit approval.
- Do not upload firmware to hardware unless the user explicitly asks for device update.
- Firmware upload scripts must keep an explicit `--yes` or dry-run gate.
- Keep generated artifacts in ignored paths such as `runs/` or `generated/`.
- Keep case IDs stable. Function names should include the case ID when possible.

## Test Execution

Offline Python checks:

```bash
cd ckb-pytest
python3.9 -m pytest -q test_ckb_onchain_compare.py
```

Fixture factory checks:

```bash
cd tx-factory-ccc
npm test -- test/ckb_tx_factory.test.ts
npm run build
```

Firmware helper checks:

```bash
bash -n scripts/*.sh
scripts/update_device_firmware.sh --help
```

Real-device replay must use explicit flags:

```bash
cd ckb-pytest
python3.9 -m pytest -s <nodeid> \
  --run-device \
  --run-onchain \
  --trezor-transport webusb:000:1
```

## Current Important Limit

`CKB-TX-054 top-level-header-dep` is the focused regression entry for
current-transaction `header_deps`. `CKB-TX-053 dao-withdraw1` remains a DAO
scenario entry and should only be unskipped after the focused headerDep case and
DAO expectations are both revalidated.
