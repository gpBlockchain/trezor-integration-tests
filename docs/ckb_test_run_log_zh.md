# CKB 测试执行记录

本文档用于边测试边记录结果，并反向调整测试用例分析文档：

- 基线分析文档：[ckb_test_case_analysis_zh.md](ckb_test_case_analysis_zh.md)
- 功能说明文档：[ckb_features.md](../../docs/ckb_features.md)

## 状态说明

| 状态 | 含义 |
|---|---|
| TODO | 还未执行 |
| PASS | 通过，实际行为符合预期 |
| FAIL | 失败，倾向于是代码或产品行为问题 |
| ADJUST | 用例描述需要调整 |
| BLOCKED | 环境、工具或依赖阻塞，暂时无法判断 |
| UNSUPPORTED | 当前设计明确不支持，需记录限制或后续支持条件 |

## 测试环境

| 项目 | 值 |
|---|---|
| 日期 |  |
| tester |  |
| trezor-firmware commit |  |
| trezor-ckb-dev commit |  |
| firmware model | T3W1 |
| emulator 启动命令 | `./emu.py --slip0014 --output /tmp/trezor-emulator.log` |
| trezorctl transport | `udp:127.0.0.1:21324` |
| emulator log | `/tmp/trezor-emulator.log` |
| 备注 |  |

## 常用命令

启动 emulator：

```bash
cd "$TREZOR_FIRMWARE_DIR"
source .venv/bin/activate
cd core
./emu.py --slip0014 --output /tmp/trezor-emulator.log
```

查看日志：

```bash
tail -f /tmp/trezor-emulator.log
```

连通性：

```bash
trezorctl -p udp:127.0.0.1:21324 get-features
```

pytest 集成测试：

```bash
cd ckb-pytest

# 默认只跑离线工具层测试，不触发设备
pytest -q

# 跑 P0 emulator/设备测试
pytest -m "p0 and integration" \
  --run-device \
  --trezor-transport udp:127.0.0.1:21324
```

执行 artifacts 默认写入：

```text
tests/ckb-pytest/runs/pytest/<test_nodeid_sanitized>/
```

## 执行记录

### P0 冒烟

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-ENV-001 | TODO | `trezorctl -p udp:127.0.0.1:21324 get-features` | 能连接 emulator，features 包含 CKB capability |  |  |
| CKB-ADDR-001 | TODO | `trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Testnet` | 返回 `ckt1...` 地址 |  |  |
| CKB-ADDR-002 | TODO | `trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Mainnet` | 返回 `ckb1...` 地址 |  |  |
| CKB-ADDR-003 | TODO | `trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Testnet -d` | 设备展示地址，可确认 |  |  |
| CKB-MSG-001 | TODO | `trezorctl -j -p udp:127.0.0.1:21324 ckb sign-message --coin Testnet "hello ckb"` | 返回地址和 65-byte 签名 |  |  |
| CKB-MSG-002 | TODO | `trezorctl -p udp:127.0.0.1:21324 ckb verify-message --coin Testnet "<address>" "<signature>" "hello ckb"` | 返回 `True` |  |  |
| CKB-MSG-007 | TODO | `pytest -s tests/test_message_support.py::test_ckb_msg_007_utf8_mixed_message --trezor-transport <transport>` | UTF-8 混合字符按精确 bytes 签名/验签 |  |  |
| CKB-MSG-008 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_008_length_boundary_empty_0_bytes --trezor-transport <transport>` | 0-byte 空消息签名/验签成功 |  |  |
| CKB-MSG-009 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_009_length_boundary_single_byte --trezor-transport <transport>` | 1-byte 消息签名/验签成功 |  |  |
| CKB-MSG-010 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_010_length_boundary_256_byte_ascii --trezor-transport <transport>` | 256-byte ASCII 消息不截断，签名/验签成功 |  |  |
| CKB-MSG-011 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_011_length_boundary_255_byte_utf8 --trezor-transport <transport>` | 255-byte UTF-8 消息按 byte 长度处理 |  |  |
| CKB-MSG-012 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_012_length_boundary_max_sign_thp_ok_65475_bytes --trezor-transport auto` | 65475-byte ASCII `sign-message` 成功 | 65475 是 `CKBSignMessage` 最大可容纳长度，包含 THP header、Noise tag、packet checksum；需人工确认长消息 UI |  |
| CKB-MSG-013 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_013_length_boundary_first_sign_thp_error_65476_bytes --trezor-transport auto` | 65476-byte ASCII `sign-message` 触发 `Encoded message is too long` | 65476 是 `CKBSignMessage` 首个 THP encoded-message 报错长度 |  |
| CKB-MSG-014 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_014_length_boundary_max_roundtrip_ok_65331_bytes --trezor-transport auto` | 65331-byte ASCII 消息签名/验签成功 | `CKBVerifyMessage` 因携带 address + signature，可用 message 上限低于 sign-only |  |
| CKB-MSG-015 | TODO | `pytest -s tests/test_message_length_boundary.py::test_ckb_msg_015_length_boundary_first_verify_thp_error_65332_bytes --trezor-transport auto` | 65332-byte ASCII `verify-message` 触发 `Encoded message is too long` | 65332 是默认 Testnet address + 65-byte signature 下验签首个 THP encoded-message 报错长度 |  |
| CKB-TX-001 | TODO | `/tmp/ckb-tx.json` + `trezorctl ... ckb sign-tx --coin Testnet` | 返回 signature 和 tx hash |  |  |

### Mainnet 真实交易回归

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-TX-035 | TODO | `common/tests/fixtures/ckb/sign_tx.json::sign_real_mainnet_transfer_5d357bc4` | raw tx hash 为 `5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673` |  |  |

建议执行命令：

```bash
cd "$TREZOR_FIRMWARE_DIR"
source .venv/bin/activate
python -m pytest tests/device_tests/ckb/test_sign_tx.py -k sign_real_mainnet_transfer_5d357bc4
```

## 交易语义

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-TX-012 | PASS | `output-with-type-script` | output 带 type script，tx hash 和 signature 匹配 | tx `0x10f960aaa3aafb68647e6ebba9071be5e30e29b5648357690cf9ad3805f06ab3`；fee `598` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json`；artifact: `runs/pytest-supplemental-real-device/tests-test_transaction_semantics.py-test_ckb_tx_012_output_with_type_script/` |
| CKB-TX-013 | PASS | `self-send-change-only` | 纯 self-send / change-only，tx hash 和 signature 匹配 | tx `0xd60446c0b6ae0a83df8df639a8f754018baf2cd43a9674824cd4db0909cb454b`；fee `508` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-014 | PASS | `external-output-plus-change` | external output + change，tx hash 和 signature 匹配 | tx `0xeb005d0c1aad2fd8248e34a319a79d75f51562abf7271b98c886e654d21ffb87`；fee `508` shannons；TX hash match: True；Signature match: True | 首轮 USB session 断开；重跑通过 |
| CKB-TX-015 | PASS | `multiple-inputs-same-account` | 多 inputs 同账户同 lock group，tx hash 和 signature 匹配 | tx `0x355602c9c99b12f03fcb35e891d60c9601c04c314b26a93880a0debd098aa429`；fee `464` shannons；TX hash match: True；Signature match: True | 首轮 USB session 断开；重跑通过 |
| CKB-TX-016 | PASS | `multiple-cell-deps-ordered` | 多 cell_deps 顺序保留，tx hash 和 signature 匹配 | tx `0x6db8120010310ae1991a5e1b51040c352ab29147b67a0e00dc9d08ece4110bf0`；fee `538` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json`；artifact: `runs/pytest-supplemental-real-device/tests-test_transaction_semantics.py-test_ckb_tx_016_multiple_cell_deps_ordered/` |
| CKB-TX-017 | PASS | `output-data-present` | output data 参与 raw tx hash，signature 匹配 | tx `0xd13f341e6cda6b55962aeefb51c27b91cf478942c2f36de6119f2a39b3d4aa16`；fee `468` shannons；TX hash match: True；Signature match: True | 首轮 USB session 断开；重跑通过 |

## 边界和 Hash Type 兼容性

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-TX-023 | PASS | `long-lock-args-chunkify` | 长 lock args 不截断，tx hash 和 signature 匹配 | tx `0x0fe2485ae3c89f6a92895415a5396a45d9471b9a20b9e722d0a60b4b5e3aa873`；fee `572` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json`；非大交易，小边界 payload |
| CKB-TX-024 | PASS | `long-type-args` | 长 type args 完整参与 hash，tx hash 和 signature 匹配 | tx `0x761985cfb35ec97f9bcb3a589220d313de4f3581d0f4877d0c19b371029d7d13`；fee `682` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json`；fixture capacity 调整为 `300` CKB 后链上提交通过 |
| CKB-TX-030 | PASS | `lock-hash-type-data1` | lock script `hash_type=data1` 可回放，tx hash 和 signature 匹配 | tx `0x7dc21cdb93ae43c643a7e1f77a413bab6028d426c82a4d7d19818679c2d47b43`；fee `464` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-031 | PASS | `lock-hash-type-data2` | lock script `hash_type=data2` 可回放，tx hash 和 signature 匹配 | tx `0x8fb11d52522bd2cc343f202420ae7372c2455b77e62a1bc9d3853af7da8a24bd`；fee `464` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-032 | PASS | `type-hash-type-data1-data2` | type script `hash_type=data1/data2` 可回放，tx hash 和 signature 匹配 | tx `0x321c5409f285c20f6c988e4b36b703b43c221fbb3d8f968009abf2f73d0bf98d`；fee `716` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |

## SighashAll 和 Lock Ownership

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-TX-036 | PASS | `one-input-default-witness` | sighash 匹配独立 CKB 实现 | tx `0x69fa70fc5a5b544e48ffeb9be801fd27aaa27f9273f9b555ef2460faa3ab3999`；fee `464` shannons；TX hash match: True；Signature match: True | 首轮 USB session 断开；重跑通过 |
| CKB-TX-037 | PASS | `two-inputs-same-lock-group` | 2 inputs 同默认 lock group，signature 匹配 | tx `0xd970703b7399161a039c9ba0ba76aa2b31384383c9f16513f7b5d17fc773db94`；fee `399` shannons；TX hash match: True；Signature match: True | 首轮 USB session 断开；重跑通过 |
| CKB-TX-038 | PASS | `trailing-witness` | trailing witness 纳入 sighash，signature 和链上 witness 匹配 | tx `0x4541fb35f0a845881593b35782ffb65ce49bf26f4dd18120873e194ea93e2df2`；fee `366` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-039 | PASS | `first-group-input-type` | 保留 `input_type`，signature 和链上 witness 匹配 | tx `0x0c640707ef5fd1df5d045c982e88b359875928d4f0cdcdf281028347b729e535`；fee `361` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-040 | PASS | `first-group-output-type` | 保留 `output_type`，signature 和链上 witness 匹配 | tx `0xdb4d8531dbb0cb12ee2ef7a3b817690e0aabcba529d63955683fe25e2a1814b8`；fee `361` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-041 | PASS | `mixed-lock-groups-primary` | 允许其他 lock group，Trezor 只签 path0 group，signature 匹配 | tx `0xfdf3ae2403e05306d556b6b5da987ff921c4d8c971c916dbbf95c95bb7bc7571`；fee `814` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-042 | PASS | `same-lock-group-non-empty-witness` | 必须纳入 sighash，signature 和链上 witness 匹配 | tx `0xf05fbfa72a7cc178a4cb3ad43d5268d8bfafbf884290c96b4b586e8366a136d3`；fee `410` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-043 | TODO | 目标签名 group 不属于当前派生 `secp256k1_blake160` lock | host/framework 签名前拒绝或明确 unsupported |  |  |
| CKB-TX-044 | PASS | `first-group-input-output-type` | 两个字段都保留，signature 和链上 witness 匹配 | tx `0x1de44d9c134dd2829acf18573ffc297b770cdb5f161bd26f0e22861d2b8bb63e`；fee `367` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-045 | PASS | `mixed-lock-groups-secondary` | Trezor 只签 path1 group，signature 匹配 | tx `0xfdf3ae2403e05306d556b6b5da987ff921c4d8c971c916dbbf95c95bb7bc7571`；fee `814` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-046 | PASS | `mixed-lock-groups-input-output-type-primary` | 两个字段都保留，signature 和链上 witness 匹配 | tx `0x7a8cb9f7e530cc0d7222a36bace1fc54b2b25f882a7d2f39ea94d109de5c8100`；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-047 | PASS | `mixed-lock-groups-input-output-type-secondary` | 两个字段都保留，signature 和链上 witness 匹配 | tx `0x7a8cb9f7e530cc0d7222a36bace1fc54b2b25f882a7d2f39ea94d109de5c8100`；TX hash match: True；Signature match: True | 与 CKB-TX-046 复用同一 tx hash，已加入 `cases.testnet.hardware.json` |
| CKB-TX-048 | PASS | `witness-args-and-random-raw` | `witness_args.input_type/output_type` 保留，其他随机 raw witness 原样纳入 sighash，signature 和链上 witness 匹配 | tx `0x742fbdb8a4f42558c7ffbbfa0c5f902332f3bb4c7ea7614ba3fded9cc2919c98`；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |

## xUDT Token

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-TX-049 | PASS | `xudt-mint` | owner lock 授权创建 xUDT cell；xUDT cell_dep/type script/output data 全量参与 hash；signature 和链上 witness 匹配 | tx `0x54591aefa39687a05ea4e29df386024dca16f07dc3e6335e0fc9db9d1e348770`；fee `646` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-050 | PASS | `xudt-transfer` | 消费已有 xUDT input，生成 recipient/change token cells；outputs_data 顺序保留；signature 和链上 witness 匹配 | tx `0xa55f405f2e18db19f7e8b7b76aeac5a40c98d132c025e5bf5a5b09abbdf4b1eb`；fee `856` shannons；TX hash match: True；Signature match: True | 已加入 `cases.testnet.hardware.json` |
| CKB-TX-051 | BLOCKED | `mock-dao-withdraw2` | DAO withdraw2 mock，`total_out > plain input capacity`，预期支持 DAO compensation 后应签名通过 | 自动化用例：`tests/test_dao.py::test_ckb_tx_051_mock_dao_withdraw2_should_pass` 当前标记 skip；历史真机输出为 `DataError: Inputs do not cover outputs`；artifact: `tests/ckb-pytest/runs/pytest-dao-real-device/tests-test_dao.py-test_ckb_tx_051_mock_dao_withdraw2_currently_rejected/trezor.sign_tx.json`、`trezorctl.output.txt` | 这是未来正向回归用例；当前跳过，待协议/固件支持 DAO withdraw2 compensation 后取消 skip |
| CKB-TX-053 | BLOCKED | `dao-withdraw1` | 真实链上 DAO withdraw1 交易应签出链上 tx hash | 链上 tx `0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db`，包含 1 个 top-level `headerDeps`；真机返回 `TX Hash: 0xa790195b183bab0d676dec6e737fc6e6c1357e13709186233fa626265ee5e572`；该 hash 等于同一交易移除 `headerDeps` 后的 raw tx hash | 当前 `trezorctl sign-tx` 会忽略 top-level `header_deps`，不能正确回放 DAO withdraw1；保留 skip，待协议/CLI 支持当前交易 header_deps |
| CKB-TX-054 | FAIL | `top-level-header-dep` | 普通 sign-tx 回放必须保留顶层 `header_deps`，返回 tx hash 和链上交易 hash 匹配 | 真机命令：`tests/test_transaction_semantics.py::test_ckb_tx_054_top_level_header_dep`；链上 tx `0x7bfc26ccb73c60df6459f4c1f9ffbbccb43f43d8fe71f52d8c6fd3d2ee0dc0db`；`trezor.sign_tx.json` 已包含 `header_deps=["7b7bb386afbb6c2addbdd9759e433c37561527b57b161b8be460256b64393f67"]`；真机返回 `TX Hash: 0xa790195b183bab0d676dec6e737fc6e6c1357e13709186233fa626265ee5e572`；TX hash match: False；Signature match: False | 框架输入已包含 headerDep，失败发生在设备/CLI 签名路径；该用例保持失败作为 headerDep 回归证据 |

## 负向用例记录

| ID | 状态 | 命令/fixture | 预期 | 实际结果 | 结论/调整 |
|---|---|---|---|---|---|
| CKB-ADDR-005 | TODO | 非 CKB SLIP-44 path | 固件拒绝 |  |  |
| CKB-ADDR-006 | TODO | 非法 network | `DataError` |  |  |
| CKB-TX-005 | TODO | zero inputs | `DataError` |  |  |
| CKB-TX-006 | TODO | zero outputs | `DataError` |  |  |
| CKB-TX-007 | TODO | input tx hash 非 32 bytes | `DataError` |  |  |
| CKB-TX-008 | TODO | lock code hash 非 32 bytes | `DataError` |  |  |
| CKB-TX-009 | TODO | invalid lock hash type | `DataError` |  |  |
| CKB-TX-010 | TODO | cell dep tx hash 非 32 bytes | `DataError` |  |  |
| CKB-TX-011 | TODO | invalid cell dep type | `DataError` |  |  |

## 待调整项

| 编号 | 来源用例 | 类型 | 描述 | 处理结论 |
|---|---|---|---|---|
| 1 |  | ADJUST/BUG/UNSUPPORTED |  |  |

## 本轮结论

- 通过项：本轮补充链上提交并真机回放 `CKB-TX-012/016/023/024/030/031/032`，pytest 结果 `7 passed in 256.01s`。
- 失败项：`CKB-TX-054 top-level-header-dep` 真机返回不含 top-level `header_deps` 的 tx hash，TX hash/signature 均不匹配。
- 需要调整的用例：`long-type-args` fixture output capacity 从 `150` CKB 调整为 `300` CKB；链上最小占用容量为 `222` CKB，调整后提交成功。
- 当前确认不支持的场景：`CKB-TX-051 mock-dao-withdraw2` 仍保持 skip，等待 DAO withdraw2 compensation 支持；`CKB-TX-053 dao-withdraw1` 真机确认会忽略 top-level `header_deps` 并签出错误 tx hash；大于 8KB 的大交易本轮未跑。
- 下一轮优先测试：`CKB-TX-022/029/043` 特殊 fixture，以及 `CKB-TX-025/026/027` 本地 JSON 边界。
