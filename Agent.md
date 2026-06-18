# CKB Trezor Tests Agent Guide

本文档给后续维护测试框架的 Agent/工程师使用。本仓库负责 CKB Trezor
适配的集成测试、链上 fixture 构造、测试文档和执行记录。

## 目录职责

- `docs/`：测试策略、用例分析、执行记录、fixture TODO 和硬件测试发现。
- `ckb-pytest/`：pytest 集成测试框架。`onchain_compare` 是工具层，`tests/` 放真实 pytest 用例。
- `tx-factory-ccc/`：用 CCC 和助记词构造/提交 Testnet 链上交易，并输出 pytest 可消费的 case JSON。
- `scripts/`：准备源码版 `trezorctl`、编译固件、更新测试设备固件的本地辅助脚本。

## 重要文档

- `docs/ckb_test_case_analysis_zh.md`：中文测试用例基线，pytest 用例 ID 必须与这里保持一致。
- `docs/ckb_test_case_analysis.md`：英文测试用例基线。
- `docs/ckb_test_run_log_zh.md`：执行日志和证据。
- `docs/ckb_tx_fixture_todo_zh.md`：链上交易 fixture 构造状态。
- `docs/ckb_trezor_test_findings.md`：当前硬件测试发现和限制。

## pytest 测试入口

默认入口是 `ckb-pytest`：

```bash
cd ckb-pytest
python3.9 -m pytest -q test_ckb_onchain_compare.py
```

默认不跑真实设备、链上 RPC、人工 UI 和慢速大交易测试。真实设备测试需要显式打开开关：

```bash
python3.9 -m pytest -s -m "p0 and integration" \
  --run-device \
  --trezor-transport webusb:000:1 \
  --trezorctl-debug
```

链上回放测试示例：

```bash
NO_PROXY='*' no_proxy='*' python3.9 -m pytest -s tests/test_sighash_all.py::test_ckb_tx_036_one_input_default_witness_placeholder \
  --run-device \
  --run-onchain \
  --trezor-transport webusb:000:1 \
  --onchain-case-file cases.testnet.hardware.json \
  --ckb-rpc-url http://testnet.ckb.dev
```

PyCharm 单测直接点跑时，框架会对显式 nodeid 自动放行设备用例，并默认打开 `TrezorCtlClient` debug 输出。

推荐的一键日常回归入口：

```bash
scripts/run_regression.sh
```

该脚本默认使用 `ckb-pytest/cases.testnet.hardware.json`，开启真实设备和链上回放，
并跳过 `slow` 大交易/边界用例。需要跑大交易时显式执行：

```bash
scripts/run_regression.sh --include-slow --target tests/test_boundary.py
```

全量目录回归中出现 skip 是正常的，主要来自三类：

- `slow` 大交易/边界测试，默认不跑。
- 已知未支持或未来回归用例，例如 DAO withdraw2 compensation、DAO 专项回归。
- fixture 尚未生成或手工专用用例。

## 固件和 trezorctl 准备

本仓库是独立仓库，不应假设一定和 `trezor-firmware` 放在固定相对路径。
脚本支持通过 `--firmware-dir` 或 `TREZOR_FIRMWARE_DIR` 指定 firmware 源码目录；
如果本机刚好有 sibling `trezor-firmware`，才会自动使用。

准备源码版 `trezorctl`：

```bash
export TREZOR_FIRMWARE_DIR=../trezor-firmware

scripts/prepare_trezorctl.sh \
  --write-pytest-local
```

编译测试固件：

```bash
scripts/build_firmware.sh \
  --model T3W1 \
  --debug
```

更新真实设备前先 dry-run：

```bash
scripts/update_device_firmware.sh \
  --dry-run
```

真正刷入设备必须显式 `--yes`，并且需要用户已经把设备放到 bootloader/update mode：

```bash
scripts/update_device_firmware.sh \
  --yes
```

## 本地配置

多人维护时不要提交个人设备配置。可以在 `ckb-pytest/pytest.local.json`
中保存本机默认值，该文件已被忽略。独立仓库环境下不要依赖固定目录结构，
建议通过 `trezorctl` 字段、`TREZORCTL` 环境变量或 PATH 指定本机 binary：

```json
{
  "run_device": true,
  "run_onchain": true,
  "trezor_transport": "webusb:000:1",
  "trezorctl": "auto",
  "onchain_case_file": "cases.testnet.hardware.json",
  "ckb_rpc_url": "http://testnet.ckb.dev",
  "artifact_dir": "runs/pytest-local",
  "env": {
    "NO_PROXY": "*",
    "no_proxy": "*"
  }
}
```

## ckb-pytest 流程

```text
RPC 链上交易
-> RpcTransaction
-> TrezorSignTx
-> trezorctl sign-tx JSON
-> trezorctl CLI
-> TrezorSignResult
-> CompareResult
```

核心原则：

- `onchain_compare` 只做工具层，不决定跑哪些测试。
- pytest marker 和参数决定测试选择。
- `trezorctl` 调用走 CLI subprocess，便于和真实用户流程保持一致。
- artifacts 要按 pytest case ID 写入，便于复盘输入、输出和比较结果。

## tx-factory-ccc 流程

`tx-factory-ccc` 用来生成链上合法交易和 case JSON。它可以用助记词派生地址、
构造 Testnet 交易、提交上链，并输出给 pytest 回放的 case 文件。

助记词只允许进入 `tx-factory-ccc` 构造模块，不应进入 `onchain_compare` 测试回放模块。

## 已知限制

- `CKB-TX-054 top-level-header-dep`：独立覆盖当前交易顶层 `header_deps` 序列化和签名 hash。
- `CKB-TX-053 dao-withdraw1`：DAO 专项回归入口，历史测试曾暴露 top-level `header_deps` 被忽略的问题；若协议/CLI 已修复，应优先跑 `CKB-TX-054` 再决定是否取消该 DAO 用例的 skip。
- `CKB-TX-051 mock-dao-withdraw2`：当前普通 fee/capacity 校验不支持 DAO compensation。
- `sign-message` 对中文和 UTF-8 四字节字符存在设备 UI 乱码问题。
- 大于 8-10KB 的设备 payload 按慢速/边界场景处理，默认全量回归中应显式 skip。

## 维护规则

- 补充或修改测试用例时，必须先改文档，再改测试代码或 fixture：
  1. 先更新 `docs/ckb_test_case_analysis_zh.md`，必要时同步 `docs/ckb_test_case_analysis.md`。
  2. 再更新 `docs/ckb_tx_fixture_todo_zh.md`，明确 fixture name、状态和生成方式。
  3. 如果是回归执行或已知问题，更新 `docs/ckb_test_run_log_zh.md` 或 `docs/ckb_trezor_test_findings.md`。
  4. 最后再新增/修改 pytest 用例、CCC recipe、case JSON 或工具代码。
- 不允许先写 pytest 用例再回填文档。
- 如果测试实现发现原文档预期错误，先修正文档并说明原因，再调整测试断言。
- 新增 pytest 用例时，函数名必须包含用例 ID，例如 `test_ckb_tx_036_one_input_default_witness_placeholder`。
- 新增链上 case 时，case JSON 的 `name` 必须等于 pytest 中传给 `fixture_name` 的值。
- 新增链上正向 case 时，`signature_policy` 必须保持一致：默认使用 `require`，禁止使用 `compare` 半严格模式；只有明确没有链上 signature 可比较的手工/特殊场景才允许 `ignore`。
- 如果 case 数据还没生成，测试可以 skip，但 skip 信息必须包含用例 ID 和 fixture name。
- 对真实设备、链上 RPC、人工 UI、慢速压力测试继续使用显式 marker/参数保护。
- 更新真实设备固件属于高风险操作，必须用户明确要求；脚本必须保留 `--dry-run`/`--yes` 保护。
- 修改签名、witness、fee、capacity 或链上交易构造逻辑后，必须保留 artifacts 并更新测试文档。
