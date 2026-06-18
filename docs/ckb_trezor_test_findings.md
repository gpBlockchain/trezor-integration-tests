# CKB Trezor Test Findings

Last updated: 2026-06-18

This document records behavior observed on real devices and committed fixtures.
Use it as the short findings summary; detailed case coverage lives in
`ckb_test_case_analysis_zh.md`, and execution evidence lives in
`ckb_test_run_log_zh.md`.

## Current Findings

### 1. `sign-message` UI does not render all UTF-8 content safely

Chinese characters and UTF-8 four-byte characters, such as emoji, are not
displayed correctly on the device confirmation screen.

Impact:

- Users cannot reliably confirm the exact human-readable content for CJK text or emoji.
- Tests should distinguish byte-level signing correctness from UI display correctness.

Expected future behavior:

- Either render UTF-8 content correctly, or clearly reject/mark unsupported characters before signing.

### 2. Large message and transaction payloads can hang real devices

Real-device testing showed practical hangs around large payloads, especially
above roughly 8-10 KB. Host transport limits can be higher, but device-side UI,
serialization, hashing, or session handling still creates a lower practical
boundary.

Impact:

- Boundary tests need timeouts and explicit `slow` gating.
- Normal regression should not include large-payload tests by default.

Expected future behavior:

- Large payloads should either complete within a bounded time or fail with a clear error.

### 3. Explicit witness/group support is available and must be regression-tested

The current CKB signing flow supports explicit:

- `witnesses`
- `sign_group_input_indices`
- `prev_txs`

This enables regression coverage for:

- first group `WitnessArgs.input_type`
- first group `WitnessArgs.output_type`
- same-lock multi-input groups
- mixed lock groups where Trezor signs only one group
- trailing and raw witnesses that affect `sighash_all`

Regression expectation:

- `TX Hash` must match the chain raw transaction hash.
- Signature should match the chain witness for deterministic same-input replays.
- Mixed lock group cases should be tested once per signing path/group.

### 4. Fee is computed from verified previous transactions

The current flow uses `prev_txs` so the device can recompute previous transaction
hashes and verify input capacities before calculating fee.

Impact:

- Host-provided `fee` should not be treated as trusted.
- Synthetic/local tests must provide hash-consistent `prev_txs`.
- Fake previous hashes such as `0x1111...` should fail before signing.

### 5. DAO withdraw1 exposed top-level `header_deps` risk

`CKB-TX-053 dao-withdraw1` has a committed Testnet fixture:

```text
0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db
```

The transaction includes one top-level `headerDeps`. Earlier real-device
replay showed the sign-tx flow ignoring that top-level field and signing the
transaction hash as if `headerDeps` were empty:

```text
device returned hash:
0xa790195b183bab0d676dec6e737fc6e6c1357e13709186233fa626265ee5e572
```

Regression handling:

- `CKB-TX-054 top-level-header-dep` is the focused regression case for
  top-level `header_deps` serialization and tx-hash matching.
- `CKB-TX-053 dao-withdraw1` remains a DAO-specific scenario and should be
  re-enabled only after the focused headerDep case and DAO expectations are
  both revalidated.

### 6. DAO withdraw2 compensation is not supported

`CKB-TX-051 mock-dao-withdraw2` models a DAO compensation case where
`total_out > plain input capacity`. Current real-device behavior rejects it with:

```text
DataError: Inputs do not cover outputs
```

Impact:

- This should remain a future positive regression case, not a normal negative-fee case.
- Keep the local mock and skip marker until DAO compensation is supported.

## Maintenance Notes

- When a finding changes, update this file and `ckb_test_run_log_zh.md`.
- If a finding maps to a stable test case, record the case ID.
- If a limitation becomes supported, remove the skip only after a real-device or emulator regression passes.
