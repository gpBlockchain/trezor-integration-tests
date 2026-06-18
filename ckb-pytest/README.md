# CKB Pytest Integration

This directory is the pytest integration framework for CKB Trezor signing.
`onchain_compare/` is the helper package; real test cases live in `tests/` and
are named with IDs from `../docs/ckb_test_case_analysis_zh.md`.

Default pytest execution does not touch real devices, RPC, manual UI, or slow
boundary cases.

## Structure

```text
onchain_compare/        # RPC, models, conversion, trezorctl client, artifacts
tests/                  # pytest integration cases
cases.*.json            # committed replay case files
test_ckb_onchain_compare.py
pytest.ini
```

Key helpers:

- `TrezorCtlClient`: wraps `get-features`, address, message, and `ckb sign-tx` CLI calls.
- `ArtifactStore`: writes per-test artifacts by pytest `nodeid`.
- `run_onchain_case`: RPC transaction -> Trezor JSON -> device signing -> compare result.

## Offline Checks

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest
python3.9 -m pytest -q test_ckb_onchain_compare.py
```

## Local Defaults

Create `pytest.local.json` for personal defaults. This file is ignored.
For an independent checkout, either install `trezorctl` on `PATH` or set the
absolute binary path here. `auto` also accepts the `TREZORCTL` environment
variable.

```json
{
  "run_device": true,
  "run_onchain": true,
  "trezor_transport": "webusb:000:1",
  "trezorctl": "/absolute/path/to/trezorctl",
  "onchain_case_file": "cases.testnet.hardware.json",
  "ckb_rpc_url": "http://testnet.ckb.dev",
  "artifact_dir": "runs/pytest-local",
  "env": {
    "no_proxy": "*",
    "NO_PROXY": "*"
  }
}
```

CLI flags override local defaults.

## Device Smoke Tests

Emulator:

```bash
python3.9 -m pytest -s -m "p0 and integration" \
  --run-device \
  --trezor-transport udp:127.0.0.1:21324 \
  --trezorctl-debug
```

Real device:

```bash
python3.9 -m pytest -s -m "p0 and integration" \
  --run-device \
  --trezor-transport webusb:000:1 \
  --trezorctl-debug
```

`--trezorctl-debug` prints the command, return code, stdout, and stderr. Use it
with `pytest -s`.

For daily real-device regression from the repository root, prefer:

```bash
scripts/run_regression.sh
```

It uses `cases.testnet.hardware.json` and keeps slow boundary tests disabled
unless `--include-slow` is passed.

## On-chain Replay

Run one committed Testnet case:

```bash
python3.9 -m pytest -s tests/test_transaction_semantics.py::test_ckb_tx_012_output_with_type_script \
  --run-device \
  --run-onchain \
  --trezor-transport webusb:000:1 \
  --onchain-case-file cases.testnet.hardware.json \
  --ckb-rpc-url http://testnet.ckb.dev
```

The framework prints `trezor.sign_tx.json` before device signing. Artifacts are
written under:

```text
runs/pytest/<test_nodeid_sanitized>/
```

Common artifact files:

- `case.json`
- `rpc.transaction.json`
- `previous.outputs.json`
- `trezor.sign_tx.json`
- `trezorctl.command.json`
- `trezorctl.output.txt`
- `compare.result.json`

For on-chain `sign-tx` cases, the console also prints the exact `trezorctl`
command before execution:

```text
[trezorctl] command
/path/to/trezorctl -p webusb:000:1 ckb sign-tx --coin Testnet -n "m/44'/309'/0'/0/0" runs/.../trezor.sign_tx.json
[trezorctl] command artifact: runs/.../trezorctl.command.json
```

## DAO withdraw1 Reproduction

`CKB-TX-053 dao-withdraw1` is a committed Testnet fixture:

```text
cases.testnet.dao-withdraw1.json
```

It is intentionally skipped in pytest because the current device flow signs the
hash without top-level `header_deps`.

Manual reproduction after generating `/private/tmp/dao-withdraw1.real-chain.trezor.sign_tx.with-header-deps.json`:

```bash
/Users/guopenglin/gp-trezor/trezor-firmware/.venv/bin/trezorctl \
  -p webusb:000:1 \
  ckb sign-tx \
  --coin Testnet \
  -n "m/44'/309'/0'/0/0" \
  /private/tmp/dao-withdraw1.real-chain.trezor.sign_tx.with-header-deps.json
```

Observed result:

```text
chain tx hash:
0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db

device returned hash:
0xa790195b183bab0d676dec6e737fc6e6c1357e13709186233fa626265ee5e572
```

The returned hash equals the same transaction with `headerDeps` removed.

## Useful pytest Flags

- `--trezor-transport`: `webusb:000:1`, `udp:127.0.0.1:21324`, or `auto`.
- `--trezorctl`: custom trezorctl path. If omitted, the framework checks
  `TREZORCTL`, then `PATH`, then a sibling `trezor-firmware/.venv/bin/trezorctl`
  for local development convenience.
- `--trezorctl-debug`: print CLI input/output.
- `--artifact-dir`: default `runs/pytest`.
- `--onchain-case-file`: case JSON used by fixture-name lookup.
- `--onchain-no-sign`: generate artifacts without calling the device.
- `--ckb-rpc-url`: Testnet/Mainnet RPC URL.
- `--ckb-owner-address`: expected lock owner for fixed Mainnet cases.
- `--run-device`: allow device tests.
- `--run-onchain`: allow RPC/on-chain tests.
- `--run-manual-ui`: allow manual UI tests.
- `--run-slow`: allow slow/boundary tests.

## Case Mapping

- `tests/test_p0_smoke.py`: `CKB-ENV-001`, `CKB-ADDR-001/002/003`, `CKB-MSG-001/002`, `CKB-TX-001`
- `tests/test_message_support.py`: `CKB-MSG-007`
- `tests/test_message_length_boundary.py`: `CKB-MSG-008` to `CKB-MSG-015`
- `tests/test_negative.py`: `CKB-ADDR-005/006`, `CKB-TX-005` to `CKB-TX-011`
- `tests/test_transaction_semantics.py`: `CKB-TX-012` to `CKB-TX-017`, `CKB-TX-049/050`, `CKB-TX-054`
- `tests/test_boundary.py`: `CKB-TX-018` to `CKB-TX-029`
- `tests/test_hash_type_compat.py`: `CKB-TX-030` to `CKB-TX-034`
- `tests/test_onchain_mainnet.py`: `CKB-TX-035`
- `tests/test_sighash_all.py`: `CKB-TX-036` to `CKB-TX-048`
- `tests/test_dao.py`: `CKB-TX-051/052/053`

## Manual Helpers

Generate Trezor JSON without signing:

```bash
python3.9 ckb_onchain_compare.py \
  --network Testnet \
  --tx-hash 0xf9d787fe6378586855b263bf0d9cd7407c554a485b1c70ba335589522c25958a \
  --no-sign
```

Call CKB get-address:

```bash
python3.9 ckb_onchain_compare.py \
  --trezorctl-action get-address \
  --network Testnet \
  --path "m/44'/309'/0'/0/0"
```

Probe message length boundaries:

```bash
python3.9 probe_message_length.py --mode sign --search --transport auto --low 65000 --high 65536
python3.9 probe_message_length.py --mode verify --search --transport auto --low 65000 --high 65536
```
