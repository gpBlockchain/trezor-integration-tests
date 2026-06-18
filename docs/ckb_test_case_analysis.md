# CKB Test Case Analysis

This document defines a practical test strategy for the current Trezor CKB
integration. It covers emulator-based manual tests, CLI-level regression tests,
and firmware behavior that should be automated in future device tests.

## Test Objectives

The CKB integration should prove the following:

- The emulator and physical device can expose CKB capability.
- CKB BIP-44 derivation works for supported paths.
- Mainnet and Testnet address generation use the correct HRP.
- Address display UI is correct and user-confirmable.
- Message signing produces a CKB-native recoverable secp256k1 signature.
- Message verification accepts valid signatures and rejects invalid ones.
- Transaction signing streams inputs, outputs, and cell deps correctly.
- Transaction signing handles boundary-sized transactions without crashes,
  silent truncation, wrong hashes, or unusable UI flows.
- Firmware validates malformed transaction fields before signing.
- User confirmation screens appear for sensitive operations.
- Returned transaction hash and signature are deterministic for fixed inputs.

## Test Environment

### Emulator

Recommended deterministic emulator startup:

```bash
cd /Users/guopenglin/gp-trezor/trezor-firmware
source .venv/bin/activate
cd core
./emu.py --slip0014 --output /tmp/trezor-emulator.log
```

Log inspection:

```bash
tail -f /tmp/trezor-emulator.log
```

Transport:

```bash
udp:127.0.0.1:21324
```

Basic connectivity:

```bash
trezorctl -p udp:127.0.0.1:21324 get-features
```

If the device reports `NotInitialized`, restart with `--slip0014` or initialize
the emulator with `trezorctl device setup`.

### Shell Notes

In `zsh`, use direct `-p` arguments, `TREZOR_PATH`, or an array. Do not use a
plain string variable containing both `-p` and the path.

Good:

```zsh
trezorctl -p udp:127.0.0.1:21324 get-features

export TREZOR_PATH=udp:127.0.0.1:21324
trezorctl get-features

T=(-p udp:127.0.0.1:21324)
trezorctl $T get-features
```

Risky in zsh:

```zsh
T='-p udp:127.0.0.1:21324'
trezorctl $T get-features
```

## Priority Levels

| Priority | Meaning |
|---|---|
| P0 | Must pass before considering CKB support usable. |
| P1 | Important behavior and error coverage. |
| P2 | Nice-to-have coverage, robustness, or UX polish. |

## Manual Smoke Test Flow

### P0: Emulator Connectivity

Command:

```bash
trezorctl -p udp:127.0.0.1:21324 get-features
```

Expected:

- Command connects to emulator.
- If pairing is required, emulator asks for confirmation.
- Features are returned after confirmation.
- `Capability_CKB` is present in features.

### P0: Testnet Address

Command:

```bash
trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Testnet
```

Expected:

- Address is returned.
- Address starts with `ckt1`.
- No display confirmation is required unless `-d` is used.

### P0: Mainnet Address

Command:

```bash
trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Mainnet
```

Expected:

- Address is returned.
- Address starts with `ckb1`.

### P0: Address Display Confirmation

Command:

```bash
trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Testnet -d
```

Expected:

- Emulator shows the CKB address.
- Path is shown as `m/44'/309'/0'/0/0` or equivalent display format.
- User can confirm and receive the same address as the non-display call.

### P0: Message Sign and Verify

Sign:

```bash
trezorctl -j -p udp:127.0.0.1:21324 ckb sign-message --coin Testnet "hello ckb"
```

Verify:

```bash
trezorctl -p udp:127.0.0.1:21324 ckb verify-message --coin Testnet "<address>" "<signature>" "hello ckb"
```

Expected:

- Signing displays a confirmation UI.
- Returned signature is 65 bytes, encoded as 130 hex chars after `0x`.
- String messages are NFC-normalized and signed as UTF-8 bytes. Length boundaries are measured in UTF-8 bytes, not Unicode scalar count or screen glyph count.
- On Safe 7 WebUSB/THP, the first host-side transport failure for `CKBSignMessage` is a 65476-byte ASCII message. For the default path/network payload, 65475 bytes is the largest ASCII message that still fits into the THP wire message limit, including trezorlib's 3-byte THP session/message header, the Noise authentication tag, and the THP packet checksum.
- `CKBVerifyMessage` carries address and signature fields in addition to the message, so its usable message boundary is lower. With the default Testnet address and a 65-byte signature, 65331 bytes is the largest fitting ASCII message and 65332 bytes is the first host-side THP encoded-message failure.
- Verification returns `True`.

### P0: Minimal Transaction Signing

Create `/tmp/ckb-tx.json`:

```bash
cat > /tmp/ckb-tx.json <<'JSON'
{
  "inputs": [
    {
      "tx_hash": "<hash-of-prev-tx-without-0x>",
      "index": 0,
      "since": 0
    }
  ],
  "outputs": [
    {
      "capacity": 6100000000,
      "lock_code_hash": "0x9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
      "lock_hash_type": 1,
      "lock_args": "0x2222222222222222222222222222222222222222",
      "data": "0x"
    }
  ],
  "cell_deps": [],
  "witnesses": [
    {
      "witness_args": {
        "lock_size": 65
      }
    }
  ],
  "sign_group_input_indices": [0],
  "prev_txs": {
    "<hash-of-prev-tx-without-0x>": {
      "version": 0,
      "header_deps": [],
      "inputs": [],
      "outputs": [
        {
          "capacity": 6200000000,
          "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
          "lock_hash_type": 1,
          "lock_args": "2222222222222222222222222222222222222222"
        }
      ],
      "cell_deps": []
    }
  }
}
JSON
```

Sign:

```bash
trezorctl -p udp:127.0.0.1:21324 ckb sign-tx --coin Testnet -n "m/44'/309'/0'/0/0" /tmp/ckb-tx.json
```

Expected:

- Testnet warning appears.
- Output confirmation appears.
- Total and fee confirmation appears.
- Result includes `Signature` and `TX Hash`.
- Signature is 65 bytes.
- Transaction hash is 32 bytes.

This sample is intended to test firmware signing flow only. It is not expected
to be broadcast. The input hash must match the raw transaction hash of the
corresponding `prev_txs` entry; using a fake `0x1111...` hash now fails with
`Missing previous tx` or `Previous transaction hash mismatch`. The JSON `fee`
field is no longer trusted by firmware. The device computes fee from verified
previous outputs.

## Mainnet Explorer Regression Fixture

Use the committed Mainnet transaction
`0x5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673` as a
real-world regression fixture for the firmware raw transaction hash path.

Source transaction:

```text
https://explorer.nervos.org/transaction/0x5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673
```

Explorer-observed shape:

| Field | Value |
|---|---|
| Network | Mainnet |
| Status | committed |
| Inputs | 1 |
| Outputs | 1 |
| Cell deps | 1 `dep_group` |
| Header deps | 0 |
| Witnesses | 1 |
| Transaction fee | `11861` shannons |
| Transaction size | 357 bytes |
| Cycles | 1638383 |

Decoded test fixture:

```json
{
  "path": "m/44'/309'/0'/0/0",
  "network": "Mainnet",
  "inputs": [
    {
      "tx_hash": "dccc0b8f9b01addafb8c2c7ed440d91ebc07082c39c21b6bdee5ad22d1f20c71",
      "index": 0,
      "since": 0
    }
  ],
  "outputs": [
    {
      "capacity": 110999832445,
      "lock_code_hash": "d00c84f0ec8fd441c38bc3f87a371f547190f2fcff88e642bc5bf54b9e318323",
      "lock_hash_type": 1,
      "lock_args": "00016367c9d04ac0af40cc5b1b3a3adc52788e5d3df0"
    }
  ],
  "cell_deps": [
    {
      "tx_hash": "71a7ba8fc96349fea0ed3a5c47992e3b4084b031a42264a018e0072e8172e46c",
      "index": 0,
      "dep_type": 1
    }
  ],
  "fee": 11861
}
```

Expected firmware result:

- `tx_hash` is
  `5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673`.
- Signature is 65 bytes.
- Output address is encoded with Mainnet HRP `ckb`.
- Output lock script uses a non-default `code_hash` with `hash_type=type` and
  22-byte args, so this case exercises full-format address handling.
- Fee confirmation shows `11861` shannons.

This fixture is now represented in
`trezor-firmware/common/tests/fixtures/ckb/sign_tx.json` as
`sign_real_mainnet_transfer_5d357bc4`.

## Transaction Boundary and Stress Tests

CKB transactions can become large because they may contain many cell inputs,
many outputs, many cell deps, long script args, type scripts, and non-empty
output data. The firmware should be tested at realistic and synthetic
boundaries because transaction signing allocates streamed data into lists,
serializes Molecule structures, hashes the raw transaction, computes
`sighash_all`, and drives multiple UI confirmations.

These tests are firmware robustness tests. They do not by themselves prove that
the transaction is acceptable to a CKB node. Node policy, relay limits, block
limits, and cycle limits must be validated separately with CKB tooling.

### Boundary Dimensions

Exercise these dimensions independently first, then in combined stress cases:

| Dimension | Why It Matters | Suggested Cases |
|---|---|---|
| Input count | Affects streaming loop, raw transaction size, and `sighash_all` witness hashing. | `1`, `2`, `10`, `50`, `100+` inputs. |
| Output count | Affects streaming loop, output confirmations, dynamic-vector serialization, and UI burden. | `1`, `2`, `10`, `50`, `100+` outputs. |
| Cell dep count | Affects streaming loop and fixed-vector serialization. | `0`, `1`, `5`, `20`, `100+` cell deps. |
| Output data size | Affects `outputs_data` serialization and transaction hash memory pressure. | empty, 1 byte, 1 KB, 10 KB, 100 KB, near host/node limit. |
| Lock args size | Affects address encoding and display behavior for non-default locks. | 0 bytes, 20 bytes, 32 bytes, 128 bytes, large synthetic args. |
| Type script presence | Affects warning UI, script serialization, and token-cell semantics. | no type script, one type script, many type-script outputs, xUDT mint, xUDT transfer. |
| Type args size | Affects type script serialization and warning flow. | empty, 20 bytes, 32 bytes, large synthetic args. |
| Token data | Affects `outputs_data`, type-script cell deps, and token amount encoding. | xUDT u128 little-endian amount, mint, transfer, token change cell. |
| Witness shape | Affects `sighash_all` compatibility with the CKB default lock script. | default `WitnessArgs`, `input_type`, `output_type`, trailing witnesses, non-empty group witnesses, multiple account groups with `input_type/output_type`. |
| Lock script group shape | Affects which witnesses are included in `sighash_all` and whether the signing key is authorized for the target group. | one default lock group, mixed lock groups, target group not owned by current key, multiple default inputs in one group. |
| Script hash type | Affects Script serialization, address encoding, change detection, and future VM compatibility. | `data`, `type`, `data1`, `data2`, future `data3` placeholder. |
| Capacity values | Affects amount formatting and uint64 handling. | minimum practical capacity, 61 CKB, 62 CKB, large uint64 values. |
| Fee values | Affects summary formatting and total calculation; firmware computes fee from verified `prev_txs` instead of trusting host JSON. | normal fee, very large fee, outputs greater than inputs, DAO withdraw2 exception. |
| `since` values | Affects input serialization and uint64 handling. | `0`, small non-zero, max valid uint64-like value. |

### Large Transaction Classes

#### Many Inputs, One Output

Purpose: stress input streaming and `sighash_all` hashing.

Expected:

- Device requests every input in order.
- No input is skipped or duplicated.
- Raw transaction hash is deterministic.
- Signature is returned once all inputs are processed.
- Runtime and memory remain acceptable on emulator and physical device.

Representative cases:

- 10 inputs, 1 output
- 50 inputs, 1 output
- 100 inputs, 1 output

#### One Input, Many Outputs

Purpose: stress output streaming, dynamic-vector serialization, and UI flow.

Expected:

- Device requests every output in order.
- External outputs are shown for confirmation.
- Change outputs are detected and redundant confirmations are suppressed.
- User can complete the confirmation flow without layout overlap or truncated
  critical information.

Representative cases:

- 1 input, 10 external outputs
- 1 input, 50 outputs mixed between external and change
- 1 input, 100 small external outputs

#### Many Inputs and Many Outputs

Purpose: stress combined raw transaction serialization and signing flow.

Expected:

- Transaction signs successfully within an agreed timeout.
- Resulting tx hash matches a host-side independent hash implementation.
- UI remains usable for all required confirmations.

Representative cases:

- 10 inputs, 10 outputs
- 50 inputs, 50 outputs
- 100 inputs, 100 outputs, if memory allows

#### Large Output Data

Purpose: verify `outputs_data` is included completely and correctly in the raw
transaction hash.

Expected:

- Output data is not truncated.
- Hash changes when one byte of data changes.
- Empty data and missing data are treated consistently according to the CLI
  conversion rules.
- Firmware either signs successfully or fails with a clear error before signing.

Representative cases:

- one output with empty data
- one output with 1-byte data
- one output with 1 KB data
- one output with 10 KB data
- one output with 100 KB data

#### Many Cell Deps

Purpose: stress `cell_deps` streaming and fixed-vector serialization.

Expected:

- Device requests every cell dep in order.
- Invalid dep types are rejected.
- Hash changes when any dep outpoint or dep type changes.

Representative cases:

- 1 cell dep
- 20 cell deps
- 100 cell deps

#### Long Script Args

Purpose: test non-standard lock or type scripts and address display safety.

Expected:

- Valid script args are serialized completely.
- Address encoding for external output confirmation does not truncate silently.
- Very long addresses remain reviewable with `chunkify`.
- Type script warning appears when type script fields are present.

Representative cases:

- default 20-byte lock args
- 32-byte lock args
- 128-byte lock args
- type args with empty, 20-byte, and large values

#### Hash Type Compatibility

Purpose: ensure CKB `Script.hash_type` handling stays compatible with current
and future script versions.

Current positive values:

| Name | Value | Expected Current Behavior |
|---|---:|---|
| `data` | `0` | accepted |
| `type` | `1` | accepted |
| `data1` | `2` | accepted |
| `data2` | `4` | accepted |

Future compatibility item:

| Name | Value | Expected Current Behavior |
|---|---:|---|
| `data3` | not assigned in this firmware | rejected until the protocol value and firmware support are added |

Expected:

- `data1` and `data2` are tested as positive cases for both lock script and
  type script serialization.
- Unsupported hash types fail before signing.
- Test fixtures use symbolic names in their descriptions, even if JSON carries
  numeric values, so future protocol changes do not silently invert test meaning.
- `data3` is tracked as a forward-compatibility test. Until firmware explicitly
  supports it, the expected result is rejection.
- Do not assume numeric value `3` means `data3`. In the current firmware, `3` is
  simply an unsupported hash type.

#### xUDT Token Cells

Purpose: verify token-cell transactions are still signed as ordinary CKB
transactions with complete type script, cell dep, output data, and witness
coverage.

Expected:

- xUDT cell deps are included in the raw transaction hash.
- xUDT output type scripts are serialized completely and trigger the type-script
  warning flow.
- Token amounts are encoded in `outputs_data` as 16-byte little-endian u128
  values and are included byte-for-byte in the hash.
- Firmware signs only the requested `secp256k1_blake160` lock group. xUDT mint
  authorization and transfer token conservation are enforced by the on-chain
  xUDT type script, not by firmware-side trust in host-provided token semantics.

Representative cases:

- owner-authorized xUDT mint that creates a new xUDT cell
- xUDT transfer that consumes an existing xUDT input and creates recipient and
  optional token-change outputs

#### SighashAll Compatibility

Purpose: verify that firmware CKB signatures match the
`secp256k1_blake160_sighash_all` lock script digest rules.

The current firmware signing API has moved from a default single-group shortcut
to an explicit witness/group model:

- `CKBSignTx.witnesses_count` is required and represents the full on-chain
  witness vector length.
- `CKBSignTx.sign_group_input_indices` is required and selects the input lock
  group signed in this call.
- The signing witness uses `WitnessArgs`; the device replaces only
  `WitnessArgs.lock` with a 65-byte zero placeholder while preserving
  `input_type` and `output_type`.
- Non-signing witnesses are streamed as raw bytes, covering other groups, empty
  witnesses, and trailing witnesses.
- `prev_txs` must cover every previous transaction referenced by inputs. The
  device reserializes each previous transaction, recomputes its hash, and only
  then trusts the previous output capacity for fee calculation.

Mixed lock groups can be signed with multiple signing calls. For example, the
host can ask `trezorctl ckb sign-tx` to sign the `[0, 1]` group with
`m/44'/309'/0'/0/0`, then sign the `[2, 3]` group with
`m/44'/309'/0'/0/1`. That flow requires the signing protocol to carry:

- the exact target group input indexes through `sign_group_input_indices`, so
  firmware does not treat all inputs as one group for the selected key
- the original witness vector, including existing signatures from other groups,
  explicit empty witnesses, and trailing witnesses
- the original `WitnessArgs.input_type` and `WitnessArgs.output_type` for the
  target group, with only `WitnessArgs.lock` replaced by a 65-byte zero
  placeholder while signing

The current test framework now carries explicit `sign_group_input_indices` and
the full witness vector. Mixed lock groups are covered by signing the same
committed transaction twice with different paths:

- `CKB-TX-041`: path0 signs the `[0, 1]` group.
- `CKB-TX-045`: path1 signs the `[2, 3]` group.
- `CKB-TX-046`: mixed lock groups where the path0 first witness has both
  `input_type` and `output_type`.
- `CKB-TX-047`: the same transaction's path1 first witness also has both
  `input_type` and `output_type`.
- Each run compares the Trezor signature with the corresponding on-chain group
  witness signature.

This proves that both lock-group sighash/signature preimages can be reproduced
by Trezor. It does not by itself prove the separate workflow that assembles two
fresh Trezor signatures into a final transaction and broadcasts it again.

The official `sighash_all` flow hashes the raw transaction hash, the first group
witness with the lock field zeroed, the remaining witnesses in the same lock
group, and all trailing witnesses after the input witness range. The updated API
now exposes enough metadata for the host to provide those bytes explicitly. The
remaining risk is host assembly: Suite or any other caller must pass the correct
group indexes and exact witness vector instead of reconstructing a simplified
transaction shape.

Expected:

- Default one-input transfer computes the same sighash as an independent
  host-side implementation.
- Multiple inputs in the same default lock group compute the same sighash when
  the remaining group witnesses are empty.
- If the target signing group does not contain the current derived
  `secp256k1_blake160` lock, the host/framework rejects or routes it to an
  explicit unsupported path before signing. Other non-target lock groups may be
  present in the same transaction.
- Transactions with trailing witnesses preserve them in the sighash preimage and
  match the corresponding on-chain signature.
- Transactions requiring `WitnessArgs.input_type` or `WitnessArgs.output_type`
  preserve those fields in the sighash preimage and match the corresponding
  on-chain signature.
- Transactions whose first group witness has both non-empty
  `WitnessArgs.input_type` and `WitnessArgs.output_type` preserve both fields in
  the signing preimage.
- Transactions whose signing witness is `witness_args` while other witnesses are
  random raw bytes preserve both the structured fields and the raw witness bytes
  in the CKB `sighash_all` preimage.
- Mixed lock-group transactions are supported per signing call when the host
  provides the target group's exact input indexes and the full witness vector.
  End-to-end double signing still needs a separate assembly-and-broadcast test.
- Mixed lock-group transactions whose multiple account groups both carry
  `WitnessArgs.input_type` and `WitnessArgs.output_type` must preserve those
  fields independently for each path/group signing call.

#### Numeric Boundaries

Purpose: catch overflow, display, and serialization issues.

Expected:

- uint32 indexes serialize little-endian correctly.
- uint64 capacity, fee, and since serialize little-endian correctly.
- Total amount calculation does not overflow silently.
- Display formatting remains clear for very large amounts.

Representative cases:

- input index `0`
- input index `4294967295`
- since `0`
- since `18446744073709551615`
- capacity `6100000000`
- large capacity near uint64 range
- fee omitted, fee `0`, normal fee, large fee

### Pass and Fail Criteria

For large transaction tests, a pass means:

- no firmware crash
- no host-side protocol deadlock
- no missing request or out-of-order request
- no silent truncation
- no malformed signature length
- tx hash matches independent host-side computation
- UI remains usable and confirms the correct semantic information

A graceful failure is acceptable for transactions beyond practical device or
host limits, but the failure must happen before signing and must produce a clear
error. A hang, panic, wrong hash, or signature over truncated data is a failure.

### Suggested Large Transaction Generator

Use generated JSON fixtures instead of hand-writing large cases. A generator
should take at least:

- `inputs_count`
- `outputs_count`
- `cell_deps_count`
- `output_data_size`
- `external_output_ratio`
- `with_type_script`
- `lock_args_size`
- `type_args_size`
- `capacity`
- `fee`
- `since`

Each generated fixture should be deterministic, named by its dimensions, and
paired with a host-side expected raw transaction hash.

## Functional Test Matrix

| ID | Priority | Area | Scenario | Expected Result |
|---|---|---|---|---|
| CKB-ADDR-001 | P0 | Address | Default Testnet address | Returns `ckt1...` address. |
| CKB-ADDR-002 | P0 | Address | Default Mainnet address | Returns `ckb1...` address. |
| CKB-ADDR-003 | P0 | Address UI | Testnet address with `-d` | Device displays and confirms address. |
| CKB-ADDR-004 | P1 | Address | Alternate valid account path | Returns deterministic address. |
| CKB-ADDR-005 | P1 | Address | Invalid SLIP-44 path | Firmware rejects path. |
| CKB-ADDR-006 | P1 | Address | Invalid network string | Firmware returns `DataError`. |
| CKB-MSG-001 | P0 | Message | Sign short ASCII message | Returns address and 65-byte signature. |
| CKB-MSG-002 | P0 | Message | Verify valid signature | Returns success. |
| CKB-MSG-003 | P1 | Message | Verify altered message | Rejects signature. |
| CKB-MSG-004 | P1 | Message | Verify altered address | Rejects signature. |
| CKB-MSG-005 | P1 | Message | Signature length not 65 bytes | Rejects signature. |
| CKB-MSG-006 | P1 | Message | Recovery ID greater than 3 | Rejects signature. |
| CKB-MSG-007 | P2 | Message | Mixed UTF-8 message with CJK, emoji, and extended Latin chars | Signs and verifies the NFC-normalized UTF-8 byte payload. |
| CKB-MSG-008 | P2 | Message | Empty message, 0 bytes | Signs and verifies successfully. |
| CKB-MSG-009 | P2 | Message | Shortest non-empty ASCII message, 1 byte | Signs and verifies successfully. |
| CKB-MSG-010 | P2 | Message | Long ASCII message, 256 bytes | Signs and verifies without host/device truncation. |
| CKB-MSG-011 | P2 | Message | Long UTF-8 message, 85 CJK chars / 255 bytes | Signs and verifies by byte length. |
| CKB-MSG-012 | P1 | Message boundary | Maximum fitting `CKBSignMessage` THP request, 65475-byte ASCII message | Signs successfully on WebUSB/THP. |
| CKB-MSG-013 | P1 | Message boundary | First `CKBSignMessage` THP host-side error, 65476-byte ASCII message | WebUSB/THP rejects with `Encoded message is too long`. |
| CKB-MSG-014 | P1 | Message boundary | Maximum fitting sign + verify roundtrip, 65331-byte ASCII message | Signs and verifies successfully on WebUSB/THP. |
| CKB-MSG-015 | P1 | Message boundary | First `CKBVerifyMessage` THP host-side error, 65332-byte ASCII message | WebUSB/THP rejects with `Encoded message is too long`. |
| CKB-TX-001 | P0 | Transaction | One input, one external output, no cell deps | Returns signature and tx hash. |
| CKB-TX-002 | P0 | Transaction UI | Testnet signing | Shows Testnet warning. |
| CKB-TX-003 | P0 | Transaction UI | External output | Shows output address and amount. |
| CKB-TX-004 | P0 | Transaction UI | Fee present | Shows total and fee. |
| CKB-TX-005 | P1 | Transaction | Zero inputs | Rejects with `DataError`. |
| CKB-TX-006 | P1 | Transaction | Zero outputs | Rejects with `DataError`. |
| CKB-TX-007 | P1 | Transaction | Input tx hash not 32 bytes | Rejects with `DataError`. |
| CKB-TX-008 | P1 | Transaction | Lock code hash not 32 bytes | Rejects with `DataError`. |
| CKB-TX-009 | P1 | Transaction | Invalid lock hash type | Rejects with `DataError`. |
| CKB-TX-010 | P1 | Transaction | Cell dep tx hash not 32 bytes | Rejects with `DataError`. |
| CKB-TX-011 | P1 | Transaction | Invalid cell dep type | Rejects with `DataError`. |
| CKB-TX-012 | P1 | Transaction UI | Output has type script | Shows type script warning before signing. |
| CKB-TX-013 | P1 | Transaction | Change output only | Shows one self-send confirmation. |
| CKB-TX-014 | P1 | Transaction | External plus change output | Shows external output; suppresses redundant change confirmation. |
| CKB-TX-015 | P2 | Transaction | Multiple inputs same account | Produces signature using one lock script group. |
| CKB-TX-016 | P2 | Transaction | Multiple cell deps | Streams and serializes all cell deps. |
| CKB-TX-017 | P2 | Transaction | Output data present | Hash includes `outputs_data`. |
| CKB-TX-018 | P1 | Transaction boundary | 50 inputs, one output | Signs or fails gracefully; no skipped input requests. |
| CKB-TX-019 | P1 | Transaction boundary | One input, 50 outputs | Confirms required outputs; tx hash matches host computation. |
| CKB-TX-020 | P1 | Transaction boundary | 50 inputs, 50 outputs | No crash or protocol deadlock; deterministic hash. |
| CKB-TX-021 | P1 | Transaction boundary | 100 KB output data | Data is fully hashed or rejected clearly before signing. |
| CKB-TX-022 | P1 | Transaction boundary | 100 cell deps | Streams all cell deps and hashes them in order. |
| CKB-TX-023 | P1 | Transaction boundary | Long lock args and `chunkify` | Address display remains reviewable; no silent truncation. |
| CKB-TX-024 | P1 | Transaction boundary | Long type args with type script | Shows type warning and hashes full type script. |
| CKB-TX-025 | P1 | Transaction boundary | Max uint32 output index | Serializes index correctly or rejects unsupported value clearly. |
| CKB-TX-026 | P1 | Transaction boundary | Max uint64 `since` | Serializes `since` correctly or rejects unsupported value clearly. |
| CKB-TX-027 | P1 | Transaction boundary | Very large capacity and fee | No silent total overflow; amount UI remains understandable. |
| CKB-TX-028 | P2 | Transaction stress | 100 inputs and 100 outputs | Measures runtime and memory; no crash on emulator. |
| CKB-TX-029 | P2 | Transaction stress | Host/node-size-limit fixture | Firmware behavior documented against external CKB node policy. |
| CKB-TX-030 | P1 | Hash type compatibility | Lock script uses `data1` hash type (`2`) | Accepted and hash matches host computation. |
| CKB-TX-031 | P1 | Hash type compatibility | Lock script uses `data2` hash type (`4`) | Accepted and hash matches host computation. |
| CKB-TX-032 | P1 | Hash type compatibility | Type script uses `data1` or `data2` hash type | Accepted, type warning shown, hash matches host computation. |
| CKB-TX-033 | P1 | Future compatibility | Candidate `data3` fixture | Rejected until official value and firmware support exist. |
| CKB-TX-034 | P1 | Hash type compatibility | Unsupported numeric hash type `3` | Rejected with `DataError`; do not label as `data3`. |

Fixture status note: `CKB-TX-023/024/030/031/032` have CCC recipe builders.
`CKB-TX-022/029/043` require special fixtures, while `CKB-TX-025/026/027`
should be covered by local JSON boundary fixtures instead of default on-chain generation.
| CKB-TX-035 | P0 | Mainnet regression | Real committed transaction `0x5d357bc4...` | Firmware raw tx hash matches explorer transaction hash. |
| CKB-TX-036 | P0 | SighashAll | One input, default `WitnessArgs.lock` placeholder | Sighash matches independent CKB implementation. |
| CKB-TX-037 | P1 | SighashAll | Two inputs in same default lock group, empty remaining witness | Sighash matches independent CKB implementation. |
| CKB-TX-038 | P1 | SighashAll compatibility | Transaction has trailing witness after input witnesses | Trailing witness is included in sighash; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-039 | P1 | SighashAll compatibility | First group witness has `input_type` payload | `input_type` is preserved in sighash; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-040 | P1 | SighashAll compatibility | First group witness has `output_type` payload | `output_type` is preserved in sighash; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-041 | P1 | SighashAll compatibility | Mixed lock script groups, path0 two-input group | Sign `[0, 1]`; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-042 | P1 | SighashAll compatibility | Non-empty witness for another input in same lock group | Same-group non-empty witness is included in sighash; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-043 | P1 | Lock ownership | Target signing group does not contain the current derived `secp256k1_blake160` lock | Rejected by host/framework before signing or marked unsupported; device must not be asked to sign a group owned by another key. |
| CKB-TX-044 | P1 | SighashAll compatibility | First group witness has both non-empty `input_type` and `output_type` payloads | Both fields are preserved in sighash; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-045 | P1 | SighashAll compatibility | Mixed lock script groups, path1 two-input group | Sign `[2, 3]`; Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-046 | P1 | SighashAll compatibility | Mixed lock groups, path0 group first witness has both `input_type` and `output_type` | Sign `[0, 1]`; both fields are preserved and Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-047 | P1 | SighashAll compatibility | Mixed lock groups, path1 group first witness has both `input_type` and `output_type` | Sign `[2, 3]`; both fields are preserved and Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-048 | P1 | SighashAll compatibility | First witness is `witness_args`, while another same-group witness and a trailing witness are random `raw` bytes | `witness_args.input_type/output_type` are preserved, raw witnesses are included byte-for-byte, and Trezor signature matches the corresponding on-chain witness. |
| CKB-TX-049 | P1 | xUDT token | Owner-authorized xUDT mint creates a new token cell | xUDT cell dep, output type script, and 16-byte little-endian u128 amount data are hashed completely; type warning appears; signature matches the on-chain witness. |
| CKB-TX-050 | P1 | xUDT token | xUDT transfer consumes an existing token input and creates recipient/change token outputs | Input/output xUDT type scripts remain consistent; output token amount data is preserved in order; type warning appears; signature matches the on-chain witness. |
| CKB-TX-051 | P1 | DAO withdraw2 mock | Local mock where `total_out > plain input capacity` | Uses hash-consistent `prev_txs` and models DAO compensation as a local JSON fixture; it must not be treated as an ordinary negative-fee rejection case. |
| CKB-TX-052 | P1 | DAO deposit | Create a Nervos DAO deposit cell | Output uses the Nervos DAO type script; output data is 8-byte little-endian zero; Nervos DAO cell dep is included; tx hash and signature match the on-chain witness. |
| CKB-TX-053 | P1 | DAO withdraw1 | Consume a DAO deposit cell and create a withdrew-phase DAO cell | Input consumes the staged DAO deposit cell; output keeps the Nervos DAO type script; output data stores the deposit block number as 8-byte little-endian; header_deps includes the deposit header hash. This remains the DAO-specific regression entry; earlier device replay exposed top-level header_deps being ignored, so run CKB-TX-054 as the focused headerDep regression before unskipping this DAO case. |
| CKB-TX-054 | P1 | Top-level header dep | Current transaction contains non-empty `header_deps` | `header_deps` is preserved in trezorctl JSON and included in the raw tx hash; returned tx hash and signature match the on-chain transaction. |

## Negative Test Data Ideas

### Invalid Input Hash

```json
{
  "inputs": [
    {
      "tx_hash": "0x1234",
      "index": 0,
      "since": 0
    }
  ],
  "outputs": [
    {
      "capacity": 6100000000,
      "lock_code_hash": "0x9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
      "lock_hash_type": 1,
      "lock_args": "0x2222222222222222222222222222222222222222",
      "data": "0x"
    }
  ],
  "cell_deps": [],
  "witnesses": [
    {
      "witness_args": {
        "lock_size": 65
      }
    }
  ],
  "sign_group_input_indices": [0],
  "prev_txs": {}
}
```

Expected: firmware rejects before previous-transaction lookup because input tx
hash is not 32 bytes.

### Invalid Hash Type

Use `lock_hash_type: 3`.

Expected: firmware rejects because supported CKB hash types are `0`, `1`, `2`,
and `4`. Do not describe numeric `3` as `data3`; current firmware has no
`data3` mapping.

### Future Data3 Hash Type

When CKB defines a `data3` hash type and the firmware implements it, add a new
positive fixture using the official numeric value. Until then, any `data3`
fixture should be a forward-compatibility negative test that proves unsupported
hash types are rejected before signing.

### Invalid Cell Dep Type

Use `dep_type: 2`.

Expected: firmware rejects because supported dep types are `0` and `1`.

### Type Script Warning

Add `type_code_hash`, `type_hash_type`, and `type_args` to an output.

Expected: firmware shows a type script warning before output confirmation.

### Oversized Output Data

Generate an output with large `data`, for example 100 KB.

Expected: firmware either signs and produces a host-verified tx hash over the
complete data, or rejects before signing with a clear error. It must not sign a
hash over truncated data.

### Too Many Outputs for Usable Review

Generate a transaction with dozens of external outputs.

Expected: every external output that requires review is presented. If the UX is
too burdensome, document the practical limit and add host-side guardrails before
calling `CKBSignTx`.

### Numeric Overflow Probe

Use very large capacity and fee values.

Expected: total calculation and display do not overflow silently. If a value is
outside the supported range, firmware or host should reject it before signing.

## Automation Recommendations

### Device Tests

Add CKB tests under:

```text
trezor-firmware/tests/device_tests/ckb/
```

Recommended files:

- `test_getaddress.py`
- `test_sign_verify_message.py`
- `test_signtx.py`
- `test_signtx_negative.py`

These tests should use the existing Trezor device test harness, debuglink
confirmation helpers, and deterministic emulator seed.

### Golden Vectors

Create golden vectors for:

- default Testnet address
- default Mainnet address
- message digest and signature shape
- UTF-8 message byte handling and boundary lengths
- raw transaction hash for fixed JSON transaction
- transaction signature shape

For signatures, exact bytes may depend on nonce behavior. If signatures are
deterministic in the firmware secp256k1 binding, assert exact signatures.
Otherwise assert:

- length is 65 bytes
- recovery ID is `0..3`
- signature verifies against the returned address and digest

### Transaction Hash Verification

Host-side tests should independently compute the expected CKB raw transaction
hash for fixed inputs, outputs, outputs data, and cell deps. This protects the
firmware Molecule serialization logic from regressions.

Boundary fixtures should include large generated transactions. At minimum,
independent host-side hash verification should cover:

- many inputs
- many outputs
- many cell deps
- large output data
- long lock args
- long type args
- `data1` and `data2` hash types for lock scripts
- `data1` and `data2` hash types for type scripts
- unsupported hash type values, including numeric `3` until/unless the protocol
  assigns it
- maximum numeric values that the protobuf schema can represent

Fixtures should name hash types symbolically in metadata, for example
`lock_hash_type_name=data2`, while the JSON payload carries the numeric value.
This makes it easier to add `data3` later without rewriting the meaning of old
tests.

### UI Tests

Important UI assertions:

- Testnet warning appears only for Testnet.
- Address screen displays `CKB` context and correct address.
- Sign-message screen displays decoded message and address.
- UTF-8 sign-message screens remain reviewable for mixed and long messages, or the product limit is documented.
- Transaction output screen shows amount formatted as CKB.
- Transaction summary shows total and fee.
- Type script warning appears when `type_code_hash` is present.
- Large-output-count transactions remain reviewable, or the practical UI limit
  is documented and enforced by host-side tooling.

### Performance and Resource Tests

For large transaction fixtures, record:

- total signing time
- peak emulator memory, if available
- physical-device signing time, when tested
- number of UI confirmations
- transaction JSON size
- serialized raw transaction size
- output data total size

Use these numbers to define practical host-side limits. Any limit should be
documented as a product constraint, not discovered only by users through hangs
or failed signing attempts.

## Risks and Coverage Gaps

- Current tests based only on `trezorctl` do not prove Suite integration.
- Minimal synthetic transaction tests do not prove chain acceptance.
- Transaction signing allows mixed lock script groups when the selected key's
  signing group is provided through explicit group indexes, even when it does
  not start at input 0.
- Firmware verifies previous transaction hashes and input capacities through
  `prev_txs`, but it does not currently enforce that the target sign group's
  previous cell locks match the derived lock. The host/framework must still
  ensure `sign_group_input_indices` selects the correct group for the path.
- `sighash_all` coverage now includes default `WitnessArgs.lock`, same-group
  non-empty witnesses, `input_type`, `output_type`, trailing witnesses, mixed
  lock groups, and the pending multi-account witness-payload cross cases.
  Suite/host assembly still needs to prove it passes the same fields into the
  firmware API.
- DAO withdraw2 can have `total_out > plain input capacity`; current normal
  transaction fee validation does not calculate DAO compensation and should be
  tracked as unsupported/future coverage.
- Default hardware regression data is consolidated in `cases.testnet.hardware.json`;
  large or not-yet-generated fixtures are controlled by pytest-level `skip`
  markers instead of separate case files.
- Transactions with both non-empty `input_type` and `output_type` are covered as
  their own case because that is the easiest place to regress witness
  preservation.
- Mixed lock groups can be completed by signing with multiple paths. The current
  comparison tests prove both group signatures on a committed fixture; a final
  end-to-end test should still assemble both fresh signatures and broadcast the
  resulting transaction.
- Host-side transaction assembly and witness insertion need separate tests.
- Very large transaction support needs explicit limits. If firmware memory,
  protocol latency, UI review burden, or host-side policy makes large
  transactions impractical, the host should enforce a clear pre-signing limit.
- Physical device tests should cover USB transport and unlocked development
  firmware separately from emulator behavior.

## Suggested Acceptance Criteria

Before treating the CKB firmware integration as ready for broader testing:

1. P0 manual smoke tests pass on emulator.
2. P0 address and message tests pass on a physical development device.
3. Device tests cover address generation, message signing, message verification,
   and one successful transaction signing flow.
4. Negative tests cover malformed hashes, invalid networks, invalid hash types,
   invalid dep types, and invalid signatures.
5. A host-side test independently verifies raw transaction hash computation for
   at least one fixed transaction vector.
6. Boundary tests define and verify practical limits for input count, output
   count, cell dep count, output data size, script arg size, and numeric ranges.
7. Compatibility tests cover `data1` and `data2`, and keep `data3` as an
   explicit future-support item with rejection expected until implemented.
