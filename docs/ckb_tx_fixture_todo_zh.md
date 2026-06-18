# CKB 交易构造 TODO

本文档用于跟踪 `ckb-pytest` 集成测试所需的交易数据构造工作。

目标产物：

- 链上合法交易：提交到 Testnet/Mainnet 后生成 `cases.testnet.json` 或固定 Mainnet case。
- 本地负向交易：生成 trezorctl `sign-tx` JSON，不需要提交链上。
- 每个链上 case 的 `cases[].name` 必须和 pytest 用例里的 `fixture_name` 一致。

## 状态说明

| 状态 | 含义 |
|---|---|
| TODO | 还没构造或还没写入 case JSON |
| CCC-READY | 当前 `tests/tx-factory-ccc` 已能生成 recipe |
| NEEDS-BUILDER | 需要补专门构造器或手工构造链上交易 |
| NEEDS-SPECIAL | 需要特殊链上状态、专用 deployed fixture 或手工 case，不适合默认一键生成 |
| LOCAL-JSON | 不需要上链，只需构造本地畸形 trezorctl JSON |
| COMMITTED | 已提交链上并生成可回放 case，但尚未完成设备/模拟器验证 |
| DONE | 已有可回放 case，并且至少完成一次设备/模拟器验证 |
| BLOCKED | 依赖协议、固件或工具能力，当前不能完成 |

## P0 / P1 优先链上交易

| 状态 | 用例 ID | fixture name | 构造目标 | 备注 |
|---|---|---|---|---|
| TODO | CKB-TX-001 | `minimal-external-transfer` | 1 input + 1 external output | P0 最小交易，可复用 CKB-TX-014 形态 |
| TODO | CKB-TX-002 | `testnet-signing-ui` | Testnet 交易签名 | UI warning 验证，可复用最小 Testnet 交易 |
| TODO | CKB-TX-003 | `external-output-ui` | external output | UI 展示地址和金额，可复用 CKB-TX-014 |
| TODO | CKB-TX-004 | `fee-present-ui` | 带明确 fee 的交易 | UI 展示 total / fee，可复用 CKB-TX-014 |
| DONE | CKB-TX-012 | `output-with-type-script` | output 带 type script | tx `0x10f960aaa3aafb68647e6ebba9071be5e30e29b5648357690cf9ad3805f06ab3`，设备验证通过 |
| DONE | CKB-TX-013 | `self-send-change-only` | 纯 self-send / change-only | tx `0xd60446c0b6ae0a83df8df639a8f754018baf2cd43a9674824cd4db0909cb454b`，设备验证通过 |
| DONE | CKB-TX-014 | `external-output-plus-change` | external output + change | tx `0xeb005d0c1aad2fd8248e34a319a79d75f51562abf7271b98c886e654d21ffb87`，设备验证通过 |
| DONE | CKB-TX-015 | `multiple-inputs-same-account` | 多 inputs，同账户同 lock group | tx `0x355602c9c99b12f03fcb35e891d60c9601c04c314b26a93880a0debd098aa429`，设备验证通过 |
| DONE | CKB-TX-016 | `multiple-cell-deps-ordered` | 多 cell_deps，顺序固定 | tx `0x6db8120010310ae1991a5e1b51040c352ab29147b67a0e00dc9d08ece4110bf0`，设备验证通过 |
| DONE | CKB-TX-017 | `output-data-present` | output data 非空 | tx `0xd13f341e6cda6b55962aeefb51c27b91cf478942c2f36de6119f2a39b3d4aa16`，设备验证通过 |
| DONE | CKB-TX-049 | `xudt-mint` | owner lock 授权创建新的 xUDT cell | tx `0x54591aefa39687a05ea4e29df386024dca16f07dc3e6335e0fc9db9d1e348770`，设备验证通过 |
| DONE | CKB-TX-050 | `xudt-transfer` | 消费已有 xUDT input，生成 recipient token cell 和可选 token change | tx `0xa55f405f2e18db19f7e8b7b76aeac5a40c98d132c025e5bf5a5b09abbdf4b1eb`，设备验证通过 |
| LOCAL-JSON | CKB-TX-051 | `mock-dao-withdraw2` | DAO withdraw2 mock，`total_out > plain input capacity` | 已有 `mock_dao_withdraw2_sign_tx` 和 pytest 自动化用例 `tests/test_dao.py`；这是未来应通过的正向用例，当前 skip，待固件支持后取消 skip |
| COMMITTED | CKB-TX-052 | `dao-deposit` | 创建 Nervos DAO deposit cell | 复用 DAO withdraw1 的 deposit funding tx `0xb559be5a0624a7d64d84f90839ee8e10e11d9af3da712c6c53d39733c0ffe869`；case file 已补充到 `tests/ckb-pytest/cases.testnet.hardware.json` 和 `tests/ckb-pytest/cases.testnet.dao-withdraw1.json`；需要真机回放后更新为 DONE |
| COMMITTED | CKB-TX-053 | `dao-withdraw1` | 提交 DAO deposit 后消费该 cell 生成 withdraw1 tx | deposit funding tx `0xb559be5a0624a7d64d84f90839ee8e10e11d9af3da712c6c53d39733c0ffe869`；withdraw1 tx `0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db`；case file 已补充到 `tests/ckb-pytest/cases.testnet.json`、`tests/ckb-pytest/cases.testnet.hardware.json`、`tests/ckb-pytest/cases.testnet.dao-withdraw1.json`；这是 DAO 专项回归入口，历史测试曾暴露 top-level header_deps 被忽略的问题；先用 CKB-TX-054 独立验证 headerDep，再决定是否取消该 DAO 用例 skip |
| COMMITTED | CKB-TX-054 | `top-level-header-dep` | 普通 sign-tx 回放中保留当前交易顶层 `header_deps` | 复用已提交 DAO withdraw1 tx `0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db` 作为 headerDep fixture；case file 已补充到 `tests/ckb-pytest/cases.testnet.json`、`tests/ckb-pytest/cases.testnet.hardware.json`、`tests/ckb-pytest/cases.testnet.dao-withdraw1.json`；用于验证 `header_deps` 被写入 trezorctl JSON 并参与 raw tx hash |

## 边界和压力交易

| 状态 | 用例 ID | fixture name | 构造目标 | 备注 |
|---|---|---|---|---|
| CCC-READY | CKB-TX-018 | `50-inputs-1-output` | 50 inputs + 1 output | 已生成链上 case；大交易默认 skip，未做真实设备签名验证 |
| CCC-READY | CKB-TX-019 | `1-input-50-outputs` | 1 input + 50 outputs | CCC 可生成 50 outputs；input 数量需链上 UTXO 配合 |
| CCC-READY | CKB-TX-020 | `50-inputs-50-outputs` | 50 inputs + 50 outputs | CCC 可生成 outputs；input 数量需链上 UTXO 配合 |
| CCC-READY | CKB-TX-021 | `100kb-output-data` | 100KB output data | 当前 CCC fixture recipe 已覆盖 |
| NEEDS-SPECIAL | CKB-TX-022 | `100-cell-deps` | 100 cell_deps | 需要 100 个唯一、有效 live cell_deps；重复 dep 容易被 node policy/consensus 拒绝，不放入默认 CCC 生成 |
| DONE | CKB-TX-023 | `long-lock-args-chunkify` | 超长 lock args | tx `0x0fe2485ae3c89f6a92895415a5396a45d9471b9a20b9e722d0a60b4b5e3aa873`，设备验证通过 |
| DONE | CKB-TX-024 | `long-type-args` | 超长 type args | tx `0x761985cfb35ec97f9bcb3a589220d313de4f3581d0f4877d0c19b371029d7d13`，设备验证通过 |
| LOCAL-JSON | CKB-TX-025 | `max-uint32-output-index` | output index 极值 | 不适合普通链上 fixture，构造本地边界 JSON 验证序列化/拒绝行为 |
| LOCAL-JSON | CKB-TX-026 | `max-uint64-since` | input `since = uint64 max` | 先用本地/特殊 fixture 定义预期拒绝；若要上链需满足 since 语义 |
| LOCAL-JSON | CKB-TX-027 | `large-capacity-and-fee` | 超大 capacity / fee | 链上资金成本不现实，使用本地 JSON 重点验证金额 overflow/显示/拒绝 |
| CCC-READY | CKB-TX-028 | `100-inputs-100-outputs` | 100 inputs + 100 outputs | CCC 可生成 outputs；input 数量需链上 UTXO 配合 |
| NEEDS-SPECIAL | CKB-TX-029 | `near-host-node-size-limit` | 接近 host/node tx size limit | 需要专用大小目标和手工边界 fixture；默认回归不跑大于 8KB 的交易 |

## hash_type 兼容性交易

| 状态 | 用例 ID | fixture name | 构造目标 | 备注 |
|---|---|---|---|---|
| DONE | CKB-TX-030 | `lock-hash-type-data1` | lock script `hash_type = data1` | tx `0x7dc21cdb93ae43c643a7e1f77a413bab6028d426c82a4d7d19818679c2d47b43`，设备验证通过 |
| DONE | CKB-TX-031 | `lock-hash-type-data2` | lock script `hash_type = data2` | tx `0x8fb11d52522bd2cc343f202420ae7372c2455b77e62a1bc9d3853af7da8a24bd`，设备验证通过 |
| DONE | CKB-TX-032 | `type-hash-type-data1-data2` | type script 使用 `data1` / `data2` | tx `0x321c5409f285c20f6c988e4b36b703b43c221fbb3d8f968009abf2f73d0bf98d`，设备验证通过 |
| BLOCKED | CKB-TX-033 | `future-data3` | future `data3` fixture | 当前无官方固件映射，保持 xfail |
| LOCAL-JSON | CKB-TX-034 | `numeric-hash-type-3` | numeric hash type `3` | 当前预期 `DataError`，不要标成 `data3` |

## Mainnet 回归交易

| 状态 | 用例 ID | fixture name | 构造目标 | 备注 |
|---|---|---|---|---|
| TODO | CKB-TX-035 | `CKB-TX-035-real-mainnet-transfer-5d357bc4` | 回放真实 Mainnet 交易 | 使用 tx `0x5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673`，不重新构造 |

## SighashAll 兼容性交易

| 状态 | 用例 ID | fixture name | 构造目标 | 备注 |
|---|---|---|---|---|
| DONE | CKB-TX-036 | `one-input-default-witness` | 1 input 默认 `WitnessArgs.lock` placeholder | tx `0x69fa70fc5a5b544e48ffeb9be801fd27aaa27f9273f9b555ef2460faa3ab3999`，设备验证通过 |
| DONE | CKB-TX-037 | `two-inputs-same-lock-group` | 2 inputs 同默认 lock group | tx `0xd970703b7399161a039c9ba0ba76aa2b31384383c9f16513f7b5d17fc773db94`，设备验证通过 |
| DONE | CKB-TX-038 | `trailing-witness` | input witnesses 后存在 trailing witness | tx `0x4541fb35f0a845881593b35782ffb65ce49bf26f4dd18120873e194ea93e2df2`，设备验证通过 |
| DONE | CKB-TX-039 | `first-group-input-type` | first group witness 有 `input_type` | tx `0x0c640707ef5fd1df5d045c982e88b359875928d4f0cdcdf281028347b729e535`，设备验证通过 |
| DONE | CKB-TX-040 | `first-group-output-type` | first group witness 有 `output_type` | tx `0xdb4d8531dbb0cb12ee2ef7a3b817690e0aabcba529d63955683fe25e2a1814b8`，设备验证通过 |
| DONE | CKB-TX-041 | `mixed-lock-groups-primary` | mixed lock script groups，path0 group 在 input 0 | tx `0xfdf3ae2403e05306d556b6b5da987ff921c4d8c971c916dbbf95c95bb7bc7571`，primary group 设备验证通过 |
| DONE | CKB-TX-042 | `same-lock-group-non-empty-witness` | 同 lock group 其他 input witness 非空 | tx `0xf05fbfa72a7cc178a4cb3ad43d5268d8bfafbf884290c96b4b586e8366a136d3`，设备验证通过 |
| NEEDS-SPECIAL | CKB-TX-043 | `input-lock-not-current-key` | input 0 previous cell lock 不属于当前 key，且无法确定当前 signing group | 需要构造“链上 tx 存在，但 case address/path 不属于任何 input lock”的负向 case；预期 host/framework 签名前拒绝 |
| DONE | CKB-TX-044 | `first-group-input-output-type` | first group witness 同时有 `input_type/output_type` | tx `0x1de44d9c134dd2829acf18573ffc297b770cdb5f161bd26f0e22861d2b8bb63e`，设备验证通过 |
| DONE | CKB-TX-045 | `mixed-lock-groups-secondary` | mixed lock script groups，path1 group 在 input 2 | 与 CKB-TX-041 复用同一 tx hash，secondary group 设备验证通过 |
| DONE | CKB-TX-046 | `mixed-lock-groups-input-output-type-primary` | 多 account mixed lock groups，path0 group first witness 同时有 `input_type/output_type` | tx `0x7a8cb9f7e530cc0d7222a36bace1fc54b2b25f882a7d2f39ea94d109de5c8100`，设备验证通过 |
| DONE | CKB-TX-047 | `mixed-lock-groups-input-output-type-secondary` | 同一交易 path1 group first witness 同时有 `input_type/output_type` | 与 CKB-TX-046 复用同一 tx hash，secondary path 设备验证通过 |
| DONE | CKB-TX-048 | `witness-args-and-random-raw` | first witness 是 `witness_args(input_type/output_type)`，同 group 第二个 witness 和 trailing witness 都是随机 raw | tx `0x742fbdb8a4f42558c7ffbbfa0c5f902332f3bb4c7ea7614ba3fded9cc2919c98`，设备验证通过 |

## 本地负向 JSON

这些用例不需要提交链上，直接构造 trezorctl `ckb sign-tx` JSON 即可。

| 状态 | 用例 ID | 构造目标 | 预期 |
|---|---|---|---|
| LOCAL-JSON | CKB-TX-005 | zero inputs | `DataError` |
| LOCAL-JSON | CKB-TX-006 | zero outputs | `DataError` |
| LOCAL-JSON | CKB-TX-007 | input tx hash 非 32 bytes | `DataError` |
| LOCAL-JSON | CKB-TX-008 | lock code hash 非 32 bytes | `DataError` |
| LOCAL-JSON | CKB-TX-009 | invalid lock hash type | `DataError` |
| LOCAL-JSON | CKB-TX-010 | cell dep tx hash 非 32 bytes | `DataError` |
| LOCAL-JSON | CKB-TX-011 | invalid cell dep type | `DataError` |

## CCC-READY 交易生成命令

先生成和 pytest `fixture_name` 对齐的 recipe：

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/tx-factory-ccc

npm exec -- tsx src/ckb_tx_factory.ts \
  --generate-fixture-recipes \
  --from-address ckt1... \
  --fixture-name self-send-change-only \
  --to-address ckt1... \
  --out-recipe-file recipes.onchain-fixtures.generated.json
```

`--fixture-name` 可以重复传；不传时生成当前支持的全部 fixture recipe。

提交链上并生成 `cases.testnet.json`：

```bash
export CKB_TEST_MNEMONIC='word1 word2 ... word12'

npm exec -- tsx src/ckb_tx_factory.ts \
  --recipe-file recipes.onchain-fixtures.generated.json \
  --send \
  --out-dir generated/onchain-fixtures \
  --out-case-file ../ckb-pytest/cases.testnet.json
```

pytest 回放：

```bash
cd /Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest

pytest -s tests/test_transaction_semantics.py \
  --run-device \
  --run-onchain \
  --trezor-transport webusb:000:1 \
  --onchain-case-file cases.testnet.json
```

## 生成记录

| 日期 | 用例 ID | fixture name | 产物 | 结果 |
|---|---|---|---|---|
| 2026-06-02 | CKB-TX-013 | `self-send-change-only` | `tests/tx-factory-ccc/generated/ckb-tx-013/recipe.ckb-tx-013.json` | recipe 已生成；按原始助记词派生的 Testnet 地址余额为 0，构造交易时报 `Insufficient CKB, need 62 extra CKB`，未提交链上 |
| 2026-06-02 | CKB-TX-036 | `one-input-default-witness` | `tests/ckb-pytest/cases.testnet.json`、`tests/ckb-pytest/runs/pytest-ckb-tx-036/tests-test_sighash_all.py-test_ckb_tx_036_one_input_default_witness_placeholder/trezor.sign_tx.json` | 复用已 committed Testnet 交易 `0xf9d787fe6378586855b263bf0d9cd7407c554a485b1c70ba335589522c25958a`；已确认 1 input、1 witness、默认 lock、可生成 Trezor JSON；设备签名比较待执行 |
| 2026-06-18 | CKB-TX-012/016/023/024/030/031/032 | supplemental fixtures | `tests/ckb-pytest/cases.testnet.hardware.json`、`tests/tx-factory-ccc/generated/mnemonic/supplemental*` | 7 个补充 fixture 已提交 Testnet，并完成真机回放；pytest `7 passed in 256.01s` |
| 2026-06-18 | CKB-TX-052 | `dao-deposit` | `tests/tx-factory-ccc/generated/dao-withdraw1/run/dao-withdraw1/deposit-funding/`、`tests/ckb-pytest/cases.testnet.hardware.json`、`tests/ckb-pytest/cases.testnet.dao-withdraw1.json` | 复用已提交 Testnet DAO deposit funding tx `0xb559be5a0624a7d64d84f90839ee8e10e11d9af3da712c6c53d39733c0ffe869`；真机回放待执行 |
| 2026-06-18 | CKB-TX-053 | `dao-withdraw1` | `tests/tx-factory-ccc/generated/dao-withdraw1/run/dao-withdraw1/`、`tests/ckb-pytest/cases.testnet.json`、`tests/ckb-pytest/cases.testnet.hardware.json`、`tests/ckb-pytest/cases.testnet.dao-withdraw1.json` | 已提交 Testnet：deposit funding tx `0xb559be5a0624a7d64d84f90839ee8e10e11d9af3da712c6c53d39733c0ffe869`，withdraw1 tx `0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db`；target `estimate_cycles=1656954`；作为 DAO 专项回归入口保留 |
| 2026-06-18 | CKB-TX-054 | `top-level-header-dep` | `tests/ckb-pytest/cases.testnet.json`、`tests/ckb-pytest/cases.testnet.hardware.json`、`tests/ckb-pytest/cases.testnet.dao-withdraw1.json` | 复用已提交 Testnet DAO withdraw1 tx `0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db`；该 tx 包含 1 个顶层 `header_deps`，用于独立验证 headerDep 序列化和签名 hash |

## 下一步实现顺序建议

1. 为 `CKB-TX-022/029/043` 设计特殊 fixture；为 `CKB-TX-025/026/027` 设计本地 JSON 边界。
2. 保留大交易 fixture，但默认 pytest 标记 skip，不纳入常规真机回归。
3. DAO withdraw2 mock 当前作为未来正向用例 skip，待固件支持 compensation 后取消 skip。
4. 最后补极值和接近 node size limit 的压力交易，并明确 firmware 签名前拒绝边界。
