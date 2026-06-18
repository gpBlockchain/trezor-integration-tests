# Trezor CKB Integration Tests

This repository contains the standalone CKB integration test project for Trezor.
It keeps the test documents, pytest device/on-chain replay framework, committed
case files, and CCC fixture factory in one place.

## What Lives Here

```text
docs/
  ckb_test_case_analysis_zh.md      # primary case matrix and expected behavior
  ckb_test_case_analysis.md         # English case matrix
  ckb_test_run_log_zh.md            # execution results and evidence
  ckb_trezor_test_findings.md       # current hardware findings and limits
  ckb_tx_fixture_todo_zh.md         # fixture status and regeneration notes
ckb-pytest/
  onchain_compare/                  # Python helper package
  tests/                            # pytest cases, named by case ID
  cases.*.json                      # replayable on-chain case files
scripts/
  prepare_trezorctl.sh              # prepare source-built trezorctl
  build_firmware.sh                 # build Trezor Core firmware
  update_device_firmware.sh         # explicit opt-in firmware upload helper
  run_regression.sh                 # one-command device regression runner
tx-factory-ccc/
  src/                              # CCC fixture generation/submission code
  test/                             # TypeScript unit tests
```

The source of truth for case IDs and expected behavior is
`docs/ckb_test_case_analysis_zh.md`. When adding or changing a case, update the
documents first, then tests and fixtures.

## Quick Checks

Offline Python helper tests:

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest
python3.9 -m pytest -q test_ckb_onchain_compare.py
```

CCC fixture factory checks:

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/tx-factory-ccc
npm install
npm test -- test/ckb_tx_factory.test.ts
npm run build
```

## Firmware Tooling

This repository is independent from `trezor-firmware`, so firmware operations
take a firmware checkout path from `--firmware-dir` or `TREZOR_FIRMWARE_DIR`.
If the checkout is a sibling directory named `trezor-firmware`, the scripts use
it automatically.

Prepare source-built `trezorctl`:

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests

scripts/prepare_trezorctl.sh \
  --firmware-dir /Users/guopenglin/gp-trezor/trezor-firmware \
  --write-pytest-local
```

Build firmware:

```bash
scripts/build_firmware.sh \
  --firmware-dir /Users/guopenglin/gp-trezor/trezor-firmware \
  --model T3W1 \
  --debug
```

Dry-run firmware upload before touching the device:

```bash
scripts/update_device_firmware.sh \
  --firmware-dir /Users/guopenglin/gp-trezor/trezor-firmware \
  --dry-run
```

Actual firmware upload is intentionally explicit. Put the device into
bootloader/update mode first, then run:

```bash
scripts/update_device_firmware.sh \
  --firmware-dir /Users/guopenglin/gp-trezor/trezor-firmware \
  --yes
```

## Real Device Replay

Device and network tests are opt-in. They must be enabled explicitly.
For an independent checkout, make `trezorctl` available on `PATH`, set
`TREZORCTL`, pass `--trezorctl /absolute/path/to/trezorctl`, or put the path in
ignored `ckb-pytest/pytest.local.json`.

Recommended one-command daily regression:

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests

scripts/run_regression.sh
```

This uses `ckb-pytest/cases.testnet.hardware.json`, enables device and on-chain
tests, prints CLI input/output, and skips `slow` boundary tests by default.

Run only one test file:

```bash
scripts/run_regression.sh --target tests/test_sighash_all.py
```

Run slow boundary cases explicitly:

```bash
scripts/run_regression.sh --include-slow --target tests/test_boundary.py
```

Manual pytest equivalent:

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest

python3.9 -m pytest -s tests/test_transaction_semantics.py::test_ckb_tx_012_output_with_type_script \
  --run-device \
  --run-onchain \
  --trezor-transport webusb:000:1 \
  --onchain-case-file cases.testnet.hardware.json \
  --ckb-rpc-url http://testnet.ckb.dev
```

Before signing, the framework prints the full `trezor.sign_tx.json` so the exact
device input can be reviewed. It also prints the exact `trezorctl` command and
writes the same command to `trezorctl.command.json`.

Expected skips in full regression:

- `slow` boundary tests unless `--include-slow` is used.
- Cases marked as unsupported or known issues, such as DAO withdraw2
  compensation or DAO-specific replay cases kept for future regression.
- Fixtures explicitly marked as not generated or manual-only in the test case
  matrix.

## Fixture Generation

Use `tx-factory-ccc` to generate Testnet transactions and case JSON. Keep
mnemonics in `.env.local` or a local mnemonic file only.

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/tx-factory-ccc

npm exec -- tsx src/ckb_tx_factory.ts \
  --generate-fixture-recipes \
  --fixture-name self-send-change-only \
  --out-recipe-file generated/self-send/recipes.json
```

Submit a generated recipe to Testnet:

```bash
npm exec -- tsx src/ckb_tx_factory.ts \
  --recipe-file generated/self-send/recipes.json \
  --send \
  --out-dir generated/self-send/run \
  --out-case-file ../ckb-pytest/cases.testnet.self-send.json
```

## Known Current Limits

- `CKB-TX-053 dao-withdraw1`: real-device replay signs the hash without
  top-level `header_deps`, so the returned hash differs from the real chain tx.
- `CKB-TX-051 mock-dao-withdraw2`: DAO compensation is not supported by the
  current fee/capacity validation path.
- Large device payloads above roughly 8-10 KB should stay out of normal
  regression runs unless explicitly testing boundaries.

## Local State

Do not commit local or generated state:

- `.env.local`
- `pytest.local.json`
- `node_modules/`
- `generated/`
- `runs/`
- firmware build outputs in `trezor-firmware/`
- Python cache files

## Maintenance Rule

For every case change:

1. Update `docs/ckb_test_case_analysis_zh.md`.
2. Update `docs/ckb_tx_fixture_todo_zh.md`.
3. Update pytest cases in `ckb-pytest/tests/`.
4. Update fixture recipes or builders in `tx-factory-ccc/`.
5. Run the smallest relevant verification.
6. Update `docs/ckb_test_run_log_zh.md` and findings when behavior changes.
