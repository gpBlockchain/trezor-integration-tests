# CKB 测试用例分析

本文档整理当前 Trezor CKB 适配的测试策略和测试用例，覆盖 emulator 手工测试、`trezorctl` 回归测试、交易签名边界、`sighash_all` 兼容性，以及后续需要自动化的设备测试。

## 测试目标

CKB 适配至少需要证明：

- Emulator 和物理设备能正确暴露 `Capability.CKB`。
- CKB BIP-44 路径 `m/44'/309'/...` 派生正确。
- Mainnet/Testnet 地址使用正确 HRP：`ckb` / `ckt`。
- 地址展示 UI 可确认，展示内容和返回地址一致。
- 消息签名返回 CKB 原生 65-byte recoverable secp256k1 签名。
- 消息验签能接受有效签名，并拒绝错误 message、address、signature。
- 交易签名能按协议流式请求 inputs、outputs、cell deps。
- raw transaction hash 和 `sighash_all` 计算结果可被独立实现验证。
- 异常交易字段在签名前被拒绝。
- 边界交易不会导致崩溃、卡死、静默截断、错误 hash 或不可用 UI。
- 对当前不支持的复杂 CKB witness / lock group 形态，要明确拒绝或标记 unsupported。

## 测试环境

### Emulator 启动

推荐使用固定助记词启动，便于地址和签名结果复现：

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

默认 UDP transport：

```text
udp:127.0.0.1:21324
```

连通性检查：

```bash
trezorctl -p udp:127.0.0.1:21324 get-features
```

如果返回 `NotInitialized`，说明设备未初始化。可以重启 emulator 并加 `--slip0014`，或用 `trezorctl device setup` 初始化。

### zsh 参数注意

不要在 zsh 里这样写：

```zsh
T='-p udp:127.0.0.1:21324'
trezorctl $T get-features
```

推荐写法：

```zsh
trezorctl -p udp:127.0.0.1:21324 get-features

export TREZOR_PATH=udp:127.0.0.1:21324
trezorctl get-features

T=(-p udp:127.0.0.1:21324)
trezorctl $T get-features
```

## 优先级定义

| 优先级 | 含义 |
|---|---|
| P0 | CKB 支持可用前必须通过。 |
| P1 | 重要行为、边界、负向和安全相关覆盖。 |
| P2 | 稳健性、压力、兼容性或 UX 补充覆盖。 |

## P0 手工冒烟流程

### 1. Emulator 连通性

```bash
trezorctl -p udp:127.0.0.1:21324 get-features
```

预期：

- 能连接 emulator。
- 需要配对时，emulator 弹出确认。
- 返回 features。
- features 中包含 CKB capability。

### 2. Testnet 地址

```bash
trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Testnet
```

预期：

- 返回地址。
- 地址以 `ckt1` 开头。

### 3. Mainnet 地址

```bash
trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Mainnet
```

预期：

- 返回地址。
- 地址以 `ckb1` 开头。

### 4. 地址展示确认

```bash
trezorctl -p udp:127.0.0.1:21324 ckb get-address --coin Testnet -d
```

预期：

- 设备展示 CKB 地址。
- 展示派生路径，例如 `m/44'/309'/0'/0/0`。
- 用户确认后，返回地址和非展示调用一致。

### 5. 消息签名和验签

签名：

```bash
trezorctl -j -p udp:127.0.0.1:21324 ckb sign-message --coin Testnet "hello ckb"
```

验签：

```bash
trezorctl -p udp:127.0.0.1:21324 ckb verify-message --coin Testnet "<address>" "<signature>" "hello ckb"
```

预期：

- 签名时设备展示确认 UI。
- 返回签名是 65 bytes，即 `0x` 后 130 个 hex 字符。
- 验签返回 `True`。
- `str` 类型 message 按 NFC normalize 后的 UTF-8 bytes 签名/验签；长度边界按 UTF-8 byte 长度统计，不按字符数统计。
- 当前 Safe 7 WebUSB/THP transport 下，`CKBSignMessage` 首个 host-side 传输报错长度为 65476-byte ASCII message；65475 bytes 是该 path/network 下 sign-message 请求可容纳的最大 ASCII message 长度。该边界包含 trezorlib 在 Noise 加密前追加的 3-byte THP session/message header、Noise authentication tag，以及 THP packet checksum。`CKBVerifyMessage` 因额外携带 address 和 65-byte signature，roundtrip 最大可验签长度为 65331 bytes，65332 bytes 是 verify-message 首个 host-side encoded-message 报错长度。

### 6. 最小交易签名

当前 `trezorctl ckb sign-tx` JSON 不能再只传 `inputs / outputs / cell_deps / fee`。
设备需要 host 提供可校验的 previous transaction、完整 witness vector 和本次要签的
lock group。最小 JSON 结构应包含：

```json
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
```

注意：

- `inputs[0].tx_hash` 必须等于 `prev_txs` 中 previous raw transaction 的 CKB hash。
- 设备会重新序列化 `prev_txs` 并校验 hash；伪造 `0x1111...` 会报 `Missing previous tx` 或 `Previous transaction hash mismatch`。
- JSON 中不再依赖 `fee` 字段；fee 由设备根据已校验 previous outputs 自行计算。
- 本地 synthetic smoke 用例应使用 `onchain_compare.synthetic_prevtx` 构造 hash 自洽的 previous tx。

签名：

```bash
trezorctl -p udp:127.0.0.1:21324 ckb sign-tx --coin Testnet -n "m/44'/309'/0'/0/0" /tmp/ckb-tx.json
```

预期：

- 展示 Testnet warning。
- 展示 output 确认。
- 展示 total 和 fee 确认。
- 返回 `Signature` 和 `TX Hash`。
- signature 为 65 bytes。
- tx hash 为 32 bytes。

说明：synthetic 交易只用于测试固件签名流程，不要求可在 CKB 链上广播；链上回归应使用
`tests/ckb-pytest/cases.testnet.hardware.json` 中已提交的 fixture。

## Mainnet 真实交易回归用例

使用已提交的 Mainnet 交易作为 raw transaction hash 回归用例：

```text
0x5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673
```

来源：

```text
https://explorer.nervos.org/transaction/0x5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673
```

交易形态：

| 字段 | 值 |
|---|---|
| Network | Mainnet |
| Status | committed |
| Inputs | 1 |
| Outputs | 1 |
| Cell deps | 1 个 `dep_group` |
| Header deps | 0 |
| Witnesses | 1 |
| Fee | `11861` shannons |
| Tx size | 357 bytes |
| Cycles | 1638383 |

预期：

- 固件计算出的 raw tx hash 等于 explorer tx hash。
- 输出地址使用 Mainnet HRP `ckb`。
- output lock 是非默认 `code_hash`，`hash_type=type`，`args` 为 22 bytes。
- fee 确认为 `11861` shannons。

该用例已加入：

```text
trezor-firmware/common/tests/fixtures/ckb/sign_tx.json
```

fixture 名称：

```text
sign_real_mainnet_transfer_5d357bc4
```

## 交易边界测试维度

| 维度 | 测试意义 | 建议覆盖 |
|---|---|---|
| input 数量 | 影响 streaming、raw tx size、`sighash_all` witness hashing | `1`、`2`、`10`、`50`、`100+` |
| output 数量 | 影响 output streaming、UI 确认、动态 vector 序列化 | `1`、`2`、`10`、`50`、`100+` |
| cell dep 数量 | 影响 fixed vector 序列化和 streaming | `0`、`1`、`5`、`20`、`100+` |
| output data 大小 | 影响 `outputs_data` 序列化和 hash 内存压力 | empty、1 byte、1 KB、10 KB、100 KB |
| lock args 大小 | 影响地址编码和展示 | 0 bytes、20 bytes、32 bytes、128 bytes、大 args |
| type script | 影响 warning UI、Script 序列化和 token cell 语义 | 无 type、单 type、多 type、xUDT mint、xUDT transfer |
| type args 大小 | 影响 type script 序列化 | empty、20 bytes、32 bytes、大 args |
| token data | 影响 `outputs_data`、type script cell_dep 和 token amount 编码 | xUDT u128 little-endian amount、mint、transfer、change token cell |
| witness 形态 | 影响 `sighash_all` 兼容性 | 默认 `WitnessArgs`、`input_type`、`output_type`、trailing witnesses、多 account group 均带 `input_type/output_type` |
| lock group 形态 | 影响哪些 witnesses 参与 `sighash_all`，以及当前 key 是否有权签目标 group | 单默认 lock group、mixed lock groups、目标 group 不属于当前 key |
| hash type | 影响 Script 序列化和未来 VM 兼容 | `data`、`type`、`data1`、`data2`、未来 `data3` |
| capacity | 影响金额展示和 uint64 处理 | 最小容量、61 CKB、62 CKB、大 uint64 |
| fee | 影响 summary 展示和 total 计算；当前由设备从已校验 `prev_txs` 自行计算，不信任 host JSON 字段 | 正常 fee、大 fee、outputs > inputs、DAO withdraw2 例外 |
| `since` | 影响 input 序列化和 uint64 处理 | `0`、小非零、max uint64 |

## SighashAll 兼容性边界

当前固件交易签名 API 已从“默认单 group 简化模型”扩展为显式 witness/group 模型：

- `CKBSignTx.witnesses_count` 必填，表示链上 witness vector 长度。
- `CKBSignTx.sign_group_input_indices` 必填，表示本次要签的 input lock group。
- 签名 witness 必须使用 `WitnessArgs`，设备只把 `lock` 字段替换为 65-byte zero placeholder。
- 非签名 witness 使用 raw witness bytes，覆盖其他 group witness、空 witness 和 trailing witness。
- `WitnessArgs.input_type` / `WitnessArgs.output_type` 会保留进 signing preimage。
- `prev_txs` 必须覆盖每个 input 引用的 previous transaction，设备会重算 previous tx hash 后才信任 input capacity。

mixed lock groups 需要按 lock group 分别签名，例如先用
`m/44'/309'/0'/0/0` 签 path0 对应的 input group，再用
`m/44'/309'/0'/0/1` 签 path1 对应的 input group。当前测试框架已经通过
`sign_group_input_indices` 和完整 witness vector 覆盖该形态：

- `CKB-TX-041`：使用 path0 签 `[0, 1]` group。
- `CKB-TX-045`：使用 path1 签 `[2, 3]` group。
- `CKB-TX-046`：mixed lock groups，path0 group 的 first witness 同时带 `input_type/output_type`。
- `CKB-TX-047`：同一交易的 path1 group first witness 同时带 `input_type/output_type`。
- 同一 mixed fixture 的 primary/secondary 用例复用同一笔链上交易，分别比较 Trezor 返回 signature 和链上对应 group witness 中的 signature。
- 当前覆盖证明两个 lock group 的 sighash/signature 均可由 Trezor 正确复现；它不额外证明“把两个 Trezor 签名重新组装后再次广播”的完整提交流程。

需要重点测试：

- 默认 1 input 交易的 sighash 是否匹配独立实现。
- 多 input 同默认 lock group 时 sighash 是否匹配独立实现。
- 目标签名 group 的 previous cell lock 不是当前派生 `secp256k1_blake160` lock 时，应在 host/framework 层拒绝；其他非目标 lock group 可以存在。
- 有 trailing witness 时，sighash 是否保留并匹配链上 signature。
- witness 有 `input_type` / `output_type` 时，签名前 witness 是否保留对应字段并匹配链上 signature。
- witness 同时有非空 `input_type` 和 `output_type` 时，签名前 witness 是否同时保留两个字段。
- 签名 witness 为 `witness_args`，同时存在其他随机 `raw` witness 时，`witness_args` 和 raw bytes 都必须按 CKB `sighash_all` 原样进入 preimage。
- mixed lock groups 已覆盖 primary/secondary 两个 group；当前 key 对应的 lock group 可以不从 input 0 开始，但必须通过 `sign_group_input_indices` 精确指定。
- mixed lock groups 中多个 account 的 first witness 都带 `input_type/output_type` 时，分别签 primary/secondary group 后 signature 都必须与链上 witness 匹配。

## 功能测试矩阵

### P0 必测

| ID | 模块 | 用例 | 预期 |
|---|---|---|---|
| CKB-ADDR-001 | 地址 | 默认 Testnet 地址 | 返回 `ckt1...` |
| CKB-ADDR-002 | 地址 | 默认 Mainnet 地址 | 返回 `ckb1...` |
| CKB-ADDR-003 | 地址 UI | Testnet 地址带 `-d` | 设备展示并确认 |
| CKB-MSG-001 | 消息 | 签名短 ASCII 消息 | 返回地址和 65-byte 签名 |
| CKB-MSG-002 | 消息 | 验证有效签名 | 返回成功 |
| CKB-MSG-007 | 消息 | UTF-8 混合字符消息 | 按精确 UTF-8 bytes 签名/验签 |
| CKB-MSG-008 | 消息 | 空消息，0 byte | 可签名并验签成功 |
| CKB-MSG-009 | 消息 | 1-byte ASCII 消息 | 可签名并验签成功 |
| CKB-MSG-010 | 消息 | 256-byte ASCII 消息 | 可签名并验签成功 |
| CKB-MSG-011 | 消息 | 255-byte UTF-8 消息 | 可签名并验签成功 |
| CKB-MSG-012 | 消息边界 | 65475-byte ASCII 消息 | WebUSB/THP 下 sign-message 可成功 |
| CKB-MSG-013 | 消息边界 | 65476-byte ASCII 消息 | WebUSB/THP 下 sign-message 触发 `Encoded message is too long` |
| CKB-MSG-014 | 消息边界 | 65331-byte ASCII 消息 | WebUSB/THP 下 sign+verify roundtrip 成功 |
| CKB-MSG-015 | 消息边界 | 65332-byte ASCII 消息 | WebUSB/THP 下 verify-message 触发 `Encoded message is too long` |
| CKB-TX-001 | 交易 | 1 input + 1 external output | 返回签名和 tx hash |
| CKB-TX-002 | 交易 UI | Testnet 签名 | 展示 Testnet warning |
| CKB-TX-003 | 交易 UI | external output | 展示 output 地址和金额 |
| CKB-TX-004 | 交易 UI | fee present | 展示 total 和 fee |
| CKB-TX-035 | Mainnet 回归 | 真实交易 `0x5d357bc4...` | raw tx hash 匹配 explorer |
| CKB-TX-036 | SighashAll | 1 input 默认 `WitnessArgs.lock` placeholder | sighash 匹配独立实现 |

### 地址用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-ADDR-004 | P1 | 合法 alternate account path | 返回确定性地址 |
| CKB-ADDR-005 | P1 | 非 CKB SLIP-44 path | 固件拒绝 |
| CKB-ADDR-006 | P1 | 非法 network | 返回 `DataError` |

### 消息签名/验签用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-MSG-003 | P1 | message 被篡改 | 验签失败 |
| CKB-MSG-004 | P1 | address 被篡改 | 验签失败 |
| CKB-MSG-005 | P1 | signature 长度不是 65 bytes | 拒绝 |
| CKB-MSG-006 | P1 | recovery id 大于 3 | 拒绝 |
| CKB-MSG-007 | P2 | UTF-8 混合字符 message，例如中文、emoji、拉丁扩展字符 | 按 NFC normalize 后的 UTF-8 bytes 签名/验签 |
| CKB-MSG-008 | P2 | 空 message，长度 0 byte | 签名和验签成功，不把空串误判为缺失参数 |
| CKB-MSG-009 | P2 | 最短非空 message，长度 1 byte | 签名和验签成功 |
| CKB-MSG-010 | P2 | 长 ASCII message，长度 256 bytes | 签名和验签成功，UI/host 不截断 |
| CKB-MSG-011 | P2 | 长 UTF-8 message，85 个中文字符，长度 255 bytes | 签名和验签成功，按 byte 长度处理 |
| CKB-MSG-012 | P1 | sign-message 最大 THP 可发送长度，65475-byte ASCII message | WebUSB/THP 下签名成功，用于锁定 sign-message 失败前一档 |
| CKB-MSG-013 | P1 | sign-message 首个 THP host-side 报错长度，65476-byte ASCII message | WebUSB/THP 下拒绝，错误包含 `Encoded message is too long` |
| CKB-MSG-014 | P1 | sign+verify roundtrip 最大 THP 可发送长度，65331-byte ASCII message | WebUSB/THP 下签名和验签成功，用于锁定 verify-message 失败前一档 |
| CKB-MSG-015 | P1 | verify-message 首个 THP host-side 报错长度，65332-byte ASCII message | WebUSB/THP 下拒绝，错误包含 `Encoded message is too long` |

### 交易基础和负向用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-TX-005 | P1 | zero inputs | `DataError` |
| CKB-TX-006 | P1 | zero outputs | `DataError` |
| CKB-TX-007 | P1 | input tx hash 非 32 bytes | `DataError` |
| CKB-TX-008 | P1 | lock code hash 非 32 bytes | `DataError` |
| CKB-TX-009 | P1 | invalid lock hash type | `DataError` |
| CKB-TX-010 | P1 | cell dep tx hash 非 32 bytes | `DataError` |
| CKB-TX-011 | P1 | invalid cell dep type | `DataError` |

### 交易 UI 和语义用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-TX-012 | P1 | output 带 type script | 展示 type script warning |
| CKB-TX-013 | P1 | 纯 change/self-send | 至少展示一次 self-send 确认 |
| CKB-TX-014 | P1 | external + change | 展示 external output，抑制冗余 change 确认 |
| CKB-TX-015 | P2 | 多 inputs 同账户 | 按单 lock group 生成签名 |
| CKB-TX-016 | P2 | 多 cell deps | 按顺序 stream 和序列化 |
| CKB-TX-017 | P2 | output data present | hash 覆盖 `outputs_data` |
| CKB-TX-054 | P1 | top-level header dep | 当前交易包含非空 `header_deps`；设备/trezorctl JSON 必须保留并参与 raw tx hash，返回 tx hash 和链上交易 hash 匹配 |

### xUDT Token 用例

xUDT 对 Trezor 签名来说仍然是 CKB 交易签名：设备需要正确序列化
output type script、cell dep、outputs data 和 witnesses，并为当前
`secp256k1_blake160` lock group 生成签名。xUDT 的 mint/transfer 代币守恒由链上
xUDT type script 执行，设备侧不应把 host 传入的 token 语义当作可信判断来源。

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-TX-049 | P1 | xUDT mint：owner lock 授权创建新的 xUDT cell | 包含 xUDT cell dep；output type script 使用 xUDT；output data 为 16-byte little-endian u128 amount；设备展示 type warning，tx hash 和 signature 与链上 witness 匹配 |
| CKB-TX-050 | P1 | xUDT transfer：消费已有 xUDT input，生成 recipient token cell 和可选 change token cell | input/output 的 xUDT type script 保持一致；token amount data 原样参与 raw tx hash；设备展示 type warning，tx hash 和 signature 与链上 witness 匹配 |
| CKB-TX-051 | P1 | DAO withdraw2 mock：`total_out > plain input capacity` | 本地 mock JSON 允许 DAO compensation 语义下 output capacity 大于 previous output capacity；`prev_txs` hash 自洽；不作为普通 fee 负数拒绝用例 |
| CKB-TX-052 | P1 | DAO deposit：创建 Nervos DAO deposit cell | output 带 Nervos DAO type script；output data 为 8-byte little-endian zero；包含 Nervos DAO cell dep；设备完整 hash output type/data/cell_dep，tx hash 和 signature 与链上 witness 匹配 |
| CKB-TX-053 | P1 | DAO withdraw1：消费 DAO deposit cell 并进入 withdrew phase | input 消费上一阶段 DAO deposit cell；output 保留 Nervos DAO type script；output data 写入 deposit block number 的 8-byte little-endian；header_deps 包含 deposit header hash；CCC 可生成链上 fixture；这是 DAO 专项回归入口，历史测试曾暴露顶层 `header_deps` 被忽略的问题；先用 CKB-TX-054 独立验证 headerDep，再决定是否取消该 DAO 用例 skip |

### 边界和压力用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-TX-018 | P1 | 50 inputs + 1 output | 成功或清晰失败，不跳 input |
| CKB-TX-019 | P1 | 1 input + 50 outputs | tx hash 匹配 host 计算 |
| CKB-TX-020 | P1 | 50 inputs + 50 outputs | 无崩溃/死锁，hash 确定 |
| CKB-TX-021 | P1 | 100 KB output data | 完整 hash 或签名前清晰拒绝 |
| CKB-TX-022 | P1 | 100 cell deps | 全部按顺序处理 |
| CKB-TX-023 | P1 | 长 lock args + chunkify | 地址展示可审查，无静默截断 |
| CKB-TX-024 | P1 | 长 type args | 展示 type warning，并 hash 完整 type script |
| CKB-TX-025 | P1 | max uint32 output index | 正确序列化或清晰拒绝 |
| CKB-TX-026 | P1 | max uint64 `since` | 正确序列化或清晰拒绝 |
| CKB-TX-027 | P1 | 大 capacity 和 fee | 不发生 silent overflow |
| CKB-TX-028 | P2 | 100 inputs + 100 outputs | 测 runtime/memory，无 emulator crash |
| CKB-TX-029 | P2 | 接近 host/node size limit | 记录 firmware 行为和 node policy 差异 |

构造状态补充：`CKB-TX-023/024` 已有 Testnet 链上 fixture，并完成真机回放验证；
`CKB-TX-022/029` 需要特殊链上 fixture；`CKB-TX-025/026/027`
优先使用本地 JSON 边界，不作为默认链上生成目标。

### Hash Type 兼容性用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-TX-030 | P1 | lock script 使用 `data1=2` | 接受，hash 匹配 |
| CKB-TX-031 | P1 | lock script 使用 `data2=4` | 接受，hash 匹配 |
| CKB-TX-032 | P1 | type script 使用 `data1` 或 `data2` | 接受，展示 type warning，hash 匹配 |
| CKB-TX-033 | P1 | future `data3` fixture | 当前拒绝，等官方数值和固件支持 |
| CKB-TX-034 | P1 | numeric hash type `3` | `DataError`，不要标成 `data3` |

构造状态补充：`CKB-TX-030/031/032` 已有 Testnet 链上 fixture，并完成真机回放验证；
其中 `CKB-TX-032` 使用 AlwaysSuccess type outputs 同时覆盖 `data1` 和 `data2`。

### SighashAll 和 Lock Ownership 用例

| ID | 优先级 | 用例 | 预期 |
|---|---|---|---|
| CKB-TX-037 | P1 | 两 inputs 同默认 lock group，剩余 witness 为空 | sighash 匹配独立实现 |
| CKB-TX-038 | P1 | 存在 trailing witness | trailing witness 纳入 sighash，signature 和链上 witness 匹配 |
| CKB-TX-039 | P1 | first group witness 有 `input_type` | 保留 `input_type`，signature 和链上 witness 匹配 |
| CKB-TX-040 | P1 | first group witness 有 `output_type` | 保留 `output_type`，signature 和链上 witness 匹配 |
| CKB-TX-041 | P1 | mixed lock script groups，path0 两 inputs | 使用 path0 签 `[0, 1]` group，signature 和链上对应 witness 匹配 |
| CKB-TX-042 | P1 | 同 lock group 其他 input 有非空 witness | 同 group 非空 witness 纳入 sighash，signature 和链上 witness 匹配 |
| CKB-TX-043 | P1 | 目标签名 group 没有当前派生 `secp256k1_blake160` lock | host/framework 签名前拒绝或明确 unsupported；设备不能被要求为不属于当前 key 的 group 签名 |
| CKB-TX-044 | P1 | first group witness 同时有非空 `input_type` 和 `output_type` | 同时保留两个字段，signature 和链上 witness 匹配 |
| CKB-TX-045 | P1 | mixed lock groups，path1 两 inputs | 使用 path1 签 `[2, 3]` group，signature 和链上对应 witness 匹配 |
| CKB-TX-046 | P1 | mixed lock groups，path0 group first witness 同时有 `input_type` 和 `output_type` | 使用 path0 签 `[0, 1]` group，两个字段都保留，signature 和链上对应 witness 匹配 |
| CKB-TX-047 | P1 | mixed lock groups，path1 group first witness 同时有 `input_type` 和 `output_type` | 使用 path1 签 `[2, 3]` group，两个字段都保留，signature 和链上对应 witness 匹配 |
| CKB-TX-048 | P1 | first witness 是 `witness_args`，同时存在同 group 随机 raw witness 和 trailing 随机 raw witness | `witness_args.input_type/output_type` 保留，其他 raw witness 原样纳入 sighash，signature 和链上 witness 匹配 |

## 大交易通过/失败标准

通过标准：

- 固件不崩溃。
- host-side protocol 不死锁。
- request 顺序正确，不漏 input/output/cell dep。
- 不发生静默截断。
- 签名长度正确。
- tx hash 匹配独立 host-side 计算。
- UI 仍可用，并展示正确语义信息。

可接受失败：

- 超出设备或产品实际限制时，签名前清晰拒绝。
- 错误信息明确说明限制原因。

不可接受失败：

- hang。
- panic。
- 生成错误 hash。
- 对被截断数据签名。
- UI 展示和实际签名内容不一致。

## 建议执行顺序

1. P0 冒烟：连通性、地址、消息、最小交易、真实 Mainnet fixture、默认 sighash。
2. P1 负向：非法 path、network、hash 长度、hash type、dep type、zero input/output。
3. 交易语义：change、external output、type script、output data。
4. 兼容性：`data1/data2/data3`、`sighash_all` witness/group、input lock ownership。
5. 压力和边界：大量 inputs/outputs/cell_deps、大 output data、极值整数。
6. 物理设备：重复 P0/P1 核心路径，观察 USB transport、UI 和性能表现。

## 风险和覆盖缺口

- `trezorctl` 测试不能证明 Suite 集成正确。
- synthetic transaction 不证明链上可接受。
- 当前交易签名允许 mixed lock script groups；当前 key 对应的 signing group 可以位于非 0 input，但必须由 host 提供准确的 group indexes 和 witness vector。
- 固件会通过 `prev_txs` 校验 previous tx hash 和 input capacity，但当前固件没有强制校验目标 sign group 的 previous cell lock 一定等于当前派生 lock；host/framework 仍需保证 `sign_group_input_indices` 指向正确 group。
- 当前 `sighash_all` 已覆盖默认 `WitnessArgs.lock`、同 group 非空 witness、`input_type`、`output_type`、trailing witness、mixed lock groups，以及待生成的多 account 多 witness payload 交叉场景；仍需关注 Suite/host 组装是否正确传递这些字段。
- mixed lock groups 已通过 path0/path1 两组签名比较覆盖；仍需单独测试把多个 Trezor 签名重新组装成最终交易并广播的端到端流程。
- DAO withdraw2 可能出现 `total_out > plain input capacity`，当前普通 fee 校验不计算 DAO compensation，应作为独立 unsupported/未来功能覆盖。
- host-side transaction assembly 和 witness insertion 需要单独测试。
- 大交易必须定义明确上限，不能让用户通过卡死或失败才发现限制。
- 默认硬件回归 case 数据已迁移到 `cases.testnet.hardware.json`；大交易和未生成 fixture 通过 pytest 用例级 `skip` 控制，不再依赖专用 case file 避免误跑。
- 物理设备测试需要覆盖 emulator 之外的 USB transport 和真实 UI 表现。

## 验收标准

在认为 CKB 固件集成可进入更广泛测试前，至少满足：

1. Emulator P0 手工冒烟通过。
2. 物理开发设备 P0 地址、消息、交易核心路径通过。
3. device tests 覆盖地址生成、消息签名、消息验签、至少一个成功交易签名。
4. 负向测试覆盖 malformed hash、非法 network、非法 hash type、非法 dep type、非法 signature。
5. host-side 独立实现验证 raw transaction hash。
6. `sighash_all` 兼容性测试覆盖默认 witness、同组多 input、不支持 witness 形态的拒绝路径。
7. compatibility tests 覆盖 `data1`、`data2`，并把 `data3` 保持为未来支持项。
8. 大交易限制有明确文档和签名前拒绝行为。
