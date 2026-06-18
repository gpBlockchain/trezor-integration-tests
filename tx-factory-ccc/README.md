# CCC Transaction Factory

This module uses CCC to build and optionally submit CKB Testnet transactions.
It then writes `ckb-pytest` case JSON that pytest can replay.

Mnemonic/private-key material must stay in local environment files or local
mnemonic files. Do not put secrets in recipes, case JSON, or artifacts intended
for commit.

## Setup

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/tx-factory-ccc
npm install
```

Optional local config, ignored by git:

```bash
CKB_TEST_MNEMONIC="word1 word2 ... word12"
CKB_TEST_PATH="m/44'/309'/0'/0/0"
CKB_TEST_EXTERNAL_PATH="m/44'/309'/0'/0/1"
```

## Verification

```bash
npm test -- test/ckb_tx_factory.test.ts
npm run build
python3 -m json.tool recipes.testnet.json >/dev/null
```

## Recipe Shape

```json
{
  "defaults": {
    "network": "Testnet",
    "from_address": "ckt1...",
    "path": "m/44'/309'/0'/0/0",
    "transport": "webusb:000:1",
    "signature_policy": "require",
    "fee_rate": 1000,
    "wait_committed": true
  },
  "recipes": [
    {
      "name": "self-transfer-62-ckb",
      "kind": "self_transfer",
      "amount_ckb": "62"
    }
  ]
}
```

Supported recipe families include:

- simple CKB transfers: `self_transfer`, `transfer`, `multi_output`
- witness/group fixtures: `two_stage_same_lock`, `two_stage_witness_payload`
- boundary fixtures: `many_inputs_one_output`, `two_stage_many_inputs_one_output`
- custom script fixtures: `custom_lock_output`, `custom_type_outputs`
- token fixtures: `xudt_mint`, `xudt_transfer`
- DAO fixtures: `dao_deposit`, `dao_withdraw1`

## Generate Fixture Recipes

Generate one fixture recipe:

```bash
node --import tsx src/ckb_tx_factory.ts \
  --generate-fixture-recipes \
  --fixture-name self-send-change-only \
  --out-recipe-file generated/self-send/recipes.json
```

Generate all supported fixture recipes using `.env.local`:

```bash
npm run fixtures:generate:all:mnemonic
```

`--fixture-name` can be repeated. If omitted, all currently supported fixture
recipes are generated.

## Submit To Testnet

Use proxy settings if your local environment requires them:

```bash
export https_proxy=http://127.0.0.1:10870
export http_proxy=http://127.0.0.1:10870
export all_proxy=socks5://127.0.0.1:10870
```

Submit one recipe file:

```bash
node --import tsx src/ckb_tx_factory.ts \
  --recipe-file generated/self-send/recipes.json \
  --send \
  --out-dir generated/self-send/run \
  --out-case-file ../ckb-pytest/cases.testnet.self-send.json
```

Submit all generated mnemonic fixtures:

```bash
npm run fixtures:send:all:mnemonic
```

Outputs:

```text
generated/<run>/<fixture_name>/recipe.normalized.json
generated/<run>/<fixture_name>/ccc.unsigned_tx.json
generated/<run>/<fixture_name>/ccc.signed_tx.json
generated/<run>/<fixture_name>/estimate_cycles.result.json
generated/<run>/<fixture_name>/submit.result.json
generated/<run>/<fixture_name>/committed.transaction.json
../ckb-pytest/cases.*.json
```

## DAO withdraw1 Fixture

Generate and submit only `dao-withdraw1`:

```bash
node --import tsx src/ckb_tx_factory.ts \
  --generate-fixture-recipes \
  --fixture-name dao-withdraw1 \
  --out-recipe-file generated/dao-withdraw1/recipes.dao-withdraw1.json

node --import tsx src/ckb_tx_factory.ts \
  --recipe-file generated/dao-withdraw1/recipes.dao-withdraw1.json \
  --send \
  --out-dir generated/dao-withdraw1/run \
  --out-case-file ../ckb-pytest/cases.testnet.dao-withdraw1.json
```

Current committed result:

```text
deposit funding tx:
0xb559be5a0624a7d64d84f90839ee8e10e11d9af3da712c6c53d39733c0ffe869

dao withdraw1 tx:
0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db
```

This case is useful as a protocol regression fixture even though current
real-device replay is blocked by missing top-level `header_deps` support.

## Replay Submitted Cases

After writing a case file, replay it from `ckb-pytest`:

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest

python3.9 -m pytest -s tests/test_transaction_semantics.py \
  --run-device \
  --run-onchain \
  --trezor-transport webusb:000:1 \
  --onchain-case-file cases.testnet.hardware.json
```

## Dry Run

Without `--send`, the factory builds and signs locally, writes artifacts, and
does not broadcast:

```bash
node --import tsx src/ckb_tx_factory.ts \
  --recipe-file recipes.testnet.json \
  --out-dir generated/dry-run
```
