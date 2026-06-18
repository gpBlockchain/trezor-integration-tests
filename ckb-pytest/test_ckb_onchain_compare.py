from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import tests.conftest as pytest_conftest

from onchain_compare.artifacts import ArtifactStore
from onchain_compare.case_file import OnchainTestCase, load_case_file
from onchain_compare.cli import run_direct_trezorctl_action
from onchain_compare.compare import compare_sign_result, extract_standard_signature
from onchain_compare.converter import rpc_transaction_to_trezor_sign_tx
from onchain_compare.converter import parse_witness_args_for_signing
from onchain_compare.converter import resolve_signing_group
from onchain_compare.rpc_models import RpcTransaction
from onchain_compare.runner import extract_signing_group_chain_signature, run_onchain_case
from onchain_compare.synthetic_prevtx import synthetic_prev_tx_for_outputs
from onchain_compare.synthetic_prevtx import mock_dao_withdraw2_sign_tx
from onchain_compare.pytest_selection import (
    should_auto_debug_trezorctl,
    should_auto_run_device,
    should_auto_run_manual_ui,
    should_auto_run_onchain,
    should_auto_run_slow,
)
from onchain_compare.pytest_onchain import (
    OnchainFixtureNotFound,
    OnchainNoSignOnly,
    run_onchain_fixture_case,
)
from onchain_compare.trezor_json import to_trezorctl_json
from onchain_compare.trezor_models import (
    TrezorAddressResult,
    TrezorCtlRequest,
    TrezorInput,
    TrezorOutput,
    TrezorSignTx,
    TrezorWitness,
    TrezorWitnessArgs,
)
from onchain_compare.trezorctl_client import TrezorCtlClient
from onchain_compare.trezorctl_locator import resolve_trezorctl
from onchain_compare.transport import parse_trezorctl_list_transport
from onchain_compare.trezorctl_cli import (
    build_trezorctl_command,
    get_address_with_trezorctl,
    parse_verify_message_output,
    parse_trezorctl_output,
    sign_message_with_trezorctl,
    sign_with_trezorctl,
    verify_message_with_trezorctl,
)
from probe_message_length import ProbeResult, classify_probe_output, find_boundary


def sample_rpc_transaction() -> dict:
    return {
        "cell_deps": [
            {
                "dep_type": "dep_group",
                "out_point": {
                    "tx_hash": "0xf8de3bb47d055cdf460d93a2a6e1b05f7432f9777c8c474abf4eec1d4aee5d37",
                    "index": "0x0",
                },
            }
        ],
        "hash": "0xf9d787fe6378586855b263bf0d9cd7407c554a485b1c70ba335589522c25958a",
        "header_deps": [],
        "inputs": [
            {
                "since": "0x0",
                "previous_output": {
                    "tx_hash": "0xc4976992c9a2c443401740ed11babee38d73281b7f52ac2836b75ef4951ac3e9",
                    "index": "0x0",
                },
            }
        ],
        "outputs": [
            {
                "capacity": "0xe8d4a38960",
                "lock": {
                    "args": "0xdf17df360c819b0fb8d4cda4f43e309db09cf62a",
                    "code_hash": "0x9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                    "hash_type": "type",
                },
                "type": None,
            }
        ],
        "outputs_data": ["0x"],
        "version": "0x0",
        "witnesses": ["0x"],
    }


def sample_previous_outputs() -> list[dict]:
    return [
        {
            "capacity": "0xe8d4a51000",
            "lock": {
                "args": "0xdf17df360c819b0fb8d4cda4f43e309db09cf62a",
                "code_hash": "0x9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                "hash_type": "type",
            },
            "type": None,
        }
    ]


def sample_previous_transactions() -> dict:
    return {
        "0xc4976992c9a2c443401740ed11babee38d73281b7f52ac2836b75ef4951ac3e9": {
            "version": "0x0",
            "header_deps": [],
            "inputs": [],
            "outputs": sample_previous_outputs(),
            "outputs_data": ["0x"],
            "cell_deps": [],
        }
    }


def molecule_bytes(data: bytes) -> bytes:
    return len(data).to_bytes(4, "little") + data


def witness_args_hex(
    lock: bytes,
    input_type: bytes | None = None,
    output_type: bytes | None = None,
) -> str:
    lock_field = molecule_bytes(lock)
    input_field = molecule_bytes(input_type) if input_type is not None else b""
    output_field = molecule_bytes(output_type) if output_type is not None else b""
    offset_lock = 16
    offset_input = offset_lock + len(lock_field)
    offset_output = offset_input + len(input_field)
    total_size = offset_output + len(output_field)
    return "0x" + b"".join(
        [
            total_size.to_bytes(4, "little"),
            offset_lock.to_bytes(4, "little"),
            offset_input.to_bytes(4, "little"),
            offset_output.to_bytes(4, "little"),
            lock_field,
            input_field,
            output_field,
        ]
    ).hex()


class OnchainCompareObjectPipelineTests(unittest.TestCase):
    def test_explicit_pytest_nodeid_selection_auto_runs_device_and_debug(self):
        args = (
            "test_p0_smoke.py::test_ckb_env_001_get_features_exposes_ckb_capability",
        )

        self.assertTrue(should_auto_run_device(args))
        self.assertTrue(should_auto_run_manual_ui(args))
        self.assertTrue(should_auto_run_onchain(args))
        self.assertTrue(should_auto_run_slow(args))
        self.assertTrue(should_auto_debug_trezorctl(args))

    def test_pycharm_path_selection_auto_runs_device_and_debug(self):
        args = (
            "--path",
            "/Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest/tests/test_negative.py",
            "--no-header",
            "--no-summary",
            "-q",
        )

        self.assertTrue(should_auto_run_device(args))
        self.assertTrue(should_auto_run_manual_ui(args))
        self.assertTrue(should_auto_run_onchain(args))
        self.assertTrue(should_auto_run_slow(args))
        self.assertTrue(should_auto_debug_trezorctl(args))

    def test_pycharm_tests_directory_selection_auto_runs_device_but_not_slow(self):
        args = (
            "--path",
            "/Users/guopenglin/gp-trezor/trezor-integration-tests/ckb-pytest/tests",
            "--no-header",
            "--no-summary",
            "-q",
        )

        self.assertTrue(should_auto_run_device(args))
        self.assertTrue(should_auto_run_manual_ui(args))
        self.assertTrue(should_auto_run_onchain(args))
        self.assertFalse(should_auto_run_slow(args))
        self.assertTrue(should_auto_debug_trezorctl(args))

    def test_default_onchain_case_file_is_hardware_regression_file(self):
        self.assertEqual(
            pytest_conftest.local_option("onchain_case_file", "cases.testnet.hardware.json"),
            "cases.testnet.hardware.json",
        )

    def test_full_pytest_run_does_not_auto_run_device_or_debug(self):
        args = ("-q",)

        self.assertFalse(should_auto_run_device(args))
        self.assertFalse(should_auto_run_manual_ui(args))
        self.assertFalse(should_auto_run_onchain(args))
        self.assertFalse(should_auto_run_slow(args))
        self.assertFalse(should_auto_debug_trezorctl(args))

    def test_probe_message_length_classifies_encoded_message_limit_error(self):
        status = classify_probe_output(
            1,
            "Failed to end session: USB write failed: LIBUSB_ERROR_NO_DEVICE [-4]\n"
            "Error: Encoded message is too long\n",
        )

        self.assertEqual(status, "limit_error")

    def test_probe_message_length_binary_search_finds_first_error(self):
        def probe(length: int) -> ProbeResult:
            status = "within_limit" if length <= 10 else "limit_error"
            return ProbeResult(
                mode="sign",
                length=length,
                returncode=0 if status == "within_limit" else 1,
                stdout="",
                status=status,
            )

        result = find_boundary(mode="sign", low=0, high=16, probe=probe)

        self.assertEqual(result.max_ok, 10)
        self.assertEqual(result.first_error, 11)

    def test_resolve_trezorctl_keeps_explicit_binary(self):
        resolved = resolve_trezorctl(
            "/custom/bin/trezorctl",
            project_root=Path("/tmp/workspace/trezor-integration-tests/ckb-pytest"),
        )

        self.assertEqual(resolved, "/custom/bin/trezorctl")

    def test_parse_trezorctl_list_transport_uses_first_listed_path(self):
        output = "webusb:000:1 - Failed to read details <class 'trezorlib.exceptions.NotPairedError'>\n"

        self.assertEqual(parse_trezorctl_list_transport(output), "webusb:000:1")

    def test_resolve_trezorctl_uses_trezorctl_env(self):
        with patch.dict("os.environ", {"TREZORCTL": "/opt/trezorctl"}), patch(
            "onchain_compare.trezorctl_locator.shutil.which",
            return_value=None,
        ):
            resolved = resolve_trezorctl(
                "auto",
                project_root=Path("/tmp/workspace/trezor-integration-tests/ckb-pytest"),
            )

        self.assertEqual(resolved, "/opt/trezorctl")

    def test_resolve_trezorctl_finds_sibling_trezor_firmware_venv_without_fixed_depth(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_root = Path(tmp_dir)
            project_root = workspace_root / "trezor-integration-tests" / "ckb-pytest"
            project_root.mkdir(parents=True)
            sibling_trezorctl = (
                workspace_root / "trezor-firmware" / ".venv" / "bin" / "trezorctl"
            )
            sibling_trezorctl.parent.mkdir(parents=True)
            sibling_trezorctl.write_text("#!/bin/sh\n")

            with patch.dict("os.environ", {}, clear=True), patch(
                "onchain_compare.trezorctl_locator.shutil.which",
                return_value=None,
            ):
                resolved = resolve_trezorctl("auto", project_root=project_root)

        self.assertEqual(resolved, str(sibling_trezorctl))

    def test_resolve_trezorctl_auto_raises_actionable_error_when_not_found(self):
        with tempfile.TemporaryDirectory() as tmp_dir, patch.dict(
            "os.environ",
            {},
            clear=True,
        ), patch("onchain_compare.trezorctl_locator.shutil.which", return_value=None):
            with self.assertRaisesRegex(FileNotFoundError, "--trezorctl"):
                resolve_trezorctl("auto", project_root=Path(tmp_dir))

    def test_artifact_store_sanitizes_pytest_nodeid_and_writes_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            store = ArtifactStore(Path(tmp_dir))
            case_dir = store.case_dir("tests/test_p0_smoke.py::test_ckb_addr_001_testnet_address")
            store.write_json(case_dir, "trezorctl.command.json", {"command": ["trezorctl"]})

            written = json.loads((case_dir / "trezorctl.command.json").read_text())

        self.assertEqual(case_dir.name, "tests-test_p0_smoke.py-test_ckb_addr_001_testnet_address")
        self.assertEqual(written, {"command": ["trezorctl"]})

    def test_trezorctl_client_get_features_captures_command_and_output(self):
        calls = []

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="Features: Capability.CKB\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TrezorCtlClient(
                transport="udp:127.0.0.1:21324",
                trezorctl="trezorctl",
                artifact_dir=Path(tmp_dir),
                run=fake_run,
            )
            result = client.get_features()
            command_json = json.loads((Path(tmp_dir) / "trezorctl.command.json").read_text())

        self.assertEqual(result.returncode, 0)
        self.assertIn("Capability.CKB", result.stdout)
        self.assertEqual(calls[0], ["trezorctl", "-p", "udp:127.0.0.1:21324", "get-features"])
        self.assertEqual(command_json["operation"], "get-features")

    def test_trezorctl_client_auto_transport_omits_path_argument_for_real_device(self):
        calls = []

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="Features: Capability.CKB\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TrezorCtlClient(
                transport="auto",
                trezorctl="trezorctl",
                artifact_dir=Path(tmp_dir),
                run=fake_run,
            )
            client.get_features()
            command_json = json.loads((Path(tmp_dir) / "trezorctl.command.json").read_text())

        self.assertEqual(calls[0], ["trezorctl", "get-features"])
        self.assertEqual(command_json["command"], ["trezorctl", "get-features"])

    def test_trezorctl_client_debug_prints_input_and_output(self):
        debug_messages = []

        def fake_run(command, text, stdout, stderr, check, env):
            return SimpleNamespace(returncode=0, stdout="Features: Capability.CKB\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TrezorCtlClient(
                transport="udp:127.0.0.1:21324",
                trezorctl="trezorctl",
                artifact_dir=Path(tmp_dir),
                run=fake_run,
                debug=True,
                debug_writer=debug_messages.append,
            )
            client.get_features()

        joined = "\n".join(debug_messages)
        self.assertIn("[trezorctl_client] input", joined)
        self.assertIn("get-features", joined)
        self.assertIn("[trezorctl_client] output", joined)
        self.assertIn("Capability.CKB", joined)

    def test_trezorctl_client_debug_truncates_long_command_arguments_only_for_console(self):
        debug_messages = []

        def fake_run(command, text, stdout, stderr, check, env):
            return SimpleNamespace(returncode=1, stdout="NoiseInvalidMessage\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TrezorCtlClient(
                transport="auto",
                trezorctl="trezorctl",
                artifact_dir=Path(tmp_dir),
                run=fake_run,
                debug=True,
                debug_writer=debug_messages.append,
            )
            long_arg = "a" * 2048
            client.run_raw(["ckb", "sign-message", long_arg], operation="ckb sign-message")
            command_json = json.loads((Path(tmp_dir) / "trezorctl.command.json").read_text())

        joined = "\n".join(debug_messages)
        self.assertIn("<truncated", joined)
        self.assertNotIn(long_arg, joined)
        self.assertEqual(command_json["command"][-1], long_arg)

    def test_parse_rpc_transaction_to_object(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())

        self.assertEqual(tx.hash, sample_rpc_transaction()["hash"])
        self.assertEqual(tx.inputs[0].tx_hash, "0xc4976992c9a2c443401740ed11babee38d73281b7f52ac2836b75ef4951ac3e9")
        self.assertEqual(tx.outputs[0].capacity, 999999900000)
        self.assertEqual(tx.outputs[0].lock.hash_type, "type")
        self.assertEqual(tx.cell_deps[0].dep_type, "dep_group")

    def test_convert_rpc_transaction_to_trezor_sign_tx_object(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]

        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )

        self.assertEqual(trezor_tx.network, "Testnet")
        self.assertEqual(trezor_tx.fee, 100000)
        self.assertEqual(trezor_tx.inputs[0].tx_hash, "c4976992c9a2c443401740ed11babee38d73281b7f52ac2836b75ef4951ac3e9")
        self.assertEqual(trezor_tx.outputs[0].lock_hash_type, 1)
        self.assertEqual(trezor_tx.cell_deps[0].dep_type, 1)

    def test_convert_rpc_transaction_preserves_top_level_header_deps(self):
        payload = sample_rpc_transaction()
        payload["header_deps"] = ["0x" + "ab" * 32]
        tx = RpcTransaction.from_json(payload)
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]

        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )
        serialized = to_trezorctl_json(trezor_tx)

        self.assertEqual(trezor_tx.header_deps, ["ab" * 32])
        self.assertEqual(serialized["header_deps"], ["ab" * 32])

    def test_resolve_signing_group_allows_other_locks_after_target_first_input(self):
        target = RpcTransaction.output_from_json(sample_previous_outputs()[0])
        other_raw = sample_previous_outputs()[0].copy()
        other_raw["lock"] = {
            **other_raw["lock"],
            "args": "0x" + "44" * 20,
        }
        other = RpcTransaction.output_from_json(other_raw)

        indexes = resolve_signing_group(
            [target, other, target],
            expected_lock=target.lock.to_json(),
        )

        self.assertEqual(indexes, [0, 2])

    def test_resolve_signing_group_allows_target_lock_after_other_lock_group(self):
        target = RpcTransaction.output_from_json(sample_previous_outputs()[0])
        other_raw = sample_previous_outputs()[0].copy()
        other_raw["lock"] = {
            **other_raw["lock"],
            "args": "0x" + "44" * 20,
        }
        other = RpcTransaction.output_from_json(other_raw)

        indexes = resolve_signing_group(
            [other, other, target, target],
            expected_lock=target.lock.to_json(),
        )

        self.assertEqual(indexes, [2, 3])

    def test_resolve_signing_group_rejects_when_target_lock_is_absent(self):
        target = RpcTransaction.output_from_json(sample_previous_outputs()[0])
        other_raw = sample_previous_outputs()[0].copy()
        other_raw["lock"] = {
            **other_raw["lock"],
            "args": "0x" + "44" * 20,
        }
        other = RpcTransaction.output_from_json(other_raw)

        with self.assertRaisesRegex(ValueError, "does not contain target address lock"):
            resolve_signing_group(
                [other],
                expected_lock=target.lock.to_json(),
            )

    def test_trezor_sign_tx_serializes_to_trezorctl_json(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]
        previous_transactions = {
            tx_hash: RpcTransaction.from_json(
                {
                    **prev_tx,
                    "hash": tx_hash,
                    "witnesses": [],
                }
            )
            for tx_hash, prev_tx in sample_previous_transactions().items()
        }
        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            previous_transactions=previous_transactions,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )

        self.assertEqual(
            to_trezorctl_json(trezor_tx),
            {
                "inputs": [
                    {
                        "tx_hash": "c4976992c9a2c443401740ed11babee38d73281b7f52ac2836b75ef4951ac3e9",
                        "index": 0,
                        "since": 0,
                    }
                ],
                "outputs": [
                    {
                        "capacity": 999999900000,
                        "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                        "lock_hash_type": 1,
                        "lock_args": "df17df360c819b0fb8d4cda4f43e309db09cf62a",
                    }
                ],
                "cell_deps": [
                    {
                        "tx_hash": "f8de3bb47d055cdf460d93a2a6e1b05f7432f9777c8c474abf4eec1d4aee5d37",
                        "index": 0,
                        "dep_type": 1,
                    }
                ],
                "header_deps": [],
                "witnesses": [{"witness_args": {"lock_size": 65}}],
                "sign_group_input_indices": [0],
                "prev_txs": {
                    "c4976992c9a2c443401740ed11babee38d73281b7f52ac2836b75ef4951ac3e9": {
                        "version": 0,
                        "header_deps": [],
                        "inputs": [],
                        "outputs": [
                            {
                                "capacity": 1000000000000,
                                "lock_code_hash": "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                                "lock_hash_type": 1,
                                "lock_args": "df17df360c819b0fb8d4cda4f43e309db09cf62a",
                            }
                        ],
                        "cell_deps": [],
                    }
                },
            },
        )

    def test_synthetic_prev_tx_matches_input_hash_and_serializes_prev_txs(self):
        previous_output = TrezorOutput(
            capacity=6200000000,
            lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
            lock_hash_type=1,
            lock_args="11" * 20,
        )
        tx_hash, prev_tx = synthetic_prev_tx_for_outputs([previous_output])
        tx = TrezorSignTx(
            network="Testnet",
            path="m/44'/309'/0'/0/0",
            inputs=[TrezorInput(tx_hash=tx_hash, index=0)],
            outputs=[
                TrezorOutput(
                    capacity=6199900000,
                    lock_code_hash=previous_output.lock_code_hash,
                    lock_hash_type=previous_output.lock_hash_type,
                    lock_args=previous_output.lock_args,
                )
            ],
            cell_deps=[],
            fee=100000,
            witnesses=[TrezorWitness(witness_args=TrezorWitnessArgs())],
            sign_group_input_indices=[0],
            prev_txs={tx_hash: prev_tx},
        )

        serialized = to_trezorctl_json(tx)

        self.assertEqual(serialized["inputs"][0]["tx_hash"], tx_hash)
        self.assertEqual(list(serialized["prev_txs"]), [tx_hash])
        self.assertEqual(serialized["prev_txs"][tx_hash]["outputs"][0]["capacity"], 6200000000)

    def test_mock_dao_withdraw2_allows_outputs_above_plain_input_capacity(self):
        tx = mock_dao_withdraw2_sign_tx(
            network="Testnet",
            path="m/44'/309'/0'/0/0",
            lock_args="11" * 20,
            input_capacity=100000000000,
            output_capacity=100100000000,
        )

        serialized = to_trezorctl_json(tx)
        previous_tx_hash = serialized["inputs"][0]["tx_hash"]
        previous_capacity = serialized["prev_txs"][previous_tx_hash]["outputs"][0]["capacity"]
        output_capacity = serialized["outputs"][0]["capacity"]

        self.assertGreater(output_capacity, previous_capacity)
        self.assertEqual(tx.fee, 0)
        self.assertEqual(serialized["inputs"][0]["since"], 0x2000000000000000)
        self.assertEqual(serialized["sign_group_input_indices"], [0])
        self.assertEqual(serialized["witnesses"], [{"witness_args": {"lock_size": 65}}])

    def test_parse_signing_witness_preserves_input_type_and_output_type(self):
        witness = witness_args_hex(
            lock=b"\x11" * 65,
            input_type=b"\x01\x02",
            output_type=b"\x03",
        )

        parsed = parse_witness_args_for_signing(witness)

        self.assertEqual(parsed.lock_size, 65)
        self.assertEqual(parsed.input_type, "0x0102")
        self.assertEqual(parsed.output_type, "0x03")

    def test_trezorctl_output_parses_to_sign_result(self):
        result = parse_trezorctl_output(
            "Signature: 0x" + "11" * 65 + "\nTX Hash: 0x" + "22" * 32 + "\n"
        )

        self.assertEqual(result.signature, "0x" + "11" * 65)
        self.assertEqual(result.tx_hash, "0x" + "22" * 32)

    def test_get_address_with_trezorctl_invokes_ckb_get_address(self):
        calls = []

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="ckt1qtest\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = get_address_with_trezorctl(
                transport="webusb:000:1",
                coin="Testnet",
                path="m/44'/309'/0'/0/0",
                work_dir=Path(tmp_dir),
                run=fake_run,
            )
            command_json = json.loads((Path(tmp_dir) / "trezorctl.command.json").read_text())

        self.assertEqual(result.address, "ckt1qtest")
        self.assertEqual(
            calls[0],
            [
                "trezorctl",
                "-p",
                "webusb:000:1",
                "ckb",
                "get-address",
                "--coin",
                "Testnet",
                "-n",
                "m/44'/309'/0'/0/0",
            ],
        )
        self.assertEqual(command_json["operation"], "get-address")

    def test_get_address_with_display_prompt_returns_final_address_line(self):
        stdout_text = (
            "Please confirm action on your Trezor device.\n"
            "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed\n"
        )

        def fake_run(command, text, stdout, stderr, check, env):
            return SimpleNamespace(returncode=0, stdout=stdout_text)

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = get_address_with_trezorctl(
                transport="auto",
                coin="Testnet",
                path="m/44'/309'/0'/0/0",
                work_dir=Path(tmp_dir),
                show_display=True,
                run=fake_run,
            )

        self.assertEqual(
            result.address,
            "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
        )

    def test_get_address_with_auto_transport_omits_path_argument_for_real_device(self):
        calls = []

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="ckt1qtest\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            get_address_with_trezorctl(
                transport="auto",
                coin="Testnet",
                path="m/44'/309'/0'/0/0",
                work_dir=Path(tmp_dir),
                run=fake_run,
            )

        self.assertEqual(
            calls[0],
            [
                "trezorctl",
                "ckb",
                "get-address",
                "--coin",
                "Testnet",
                "-n",
                "m/44'/309'/0'/0/0",
            ],
        )

    def test_trezorctl_client_get_address_with_display_prompt_returns_final_address_line(self):
        stdout_text = (
            "Please confirm action on your Trezor device.\n"
            "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed\n"
        )

        def fake_run(command, text, stdout, stderr, check, env):
            return SimpleNamespace(returncode=0, stdout=stdout_text)

        with tempfile.TemporaryDirectory() as tmp_dir:
            client = TrezorCtlClient(
                transport="auto",
                trezorctl="trezorctl",
                artifact_dir=Path(tmp_dir),
                run=fake_run,
            )
            result = client.ckb_get_address(
                coin="Testnet",
                path="m/44'/309'/0'/0/0",
                show_display=True,
            )

        self.assertEqual(
            result.address,
            "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
        )

    def test_sign_message_with_trezorctl_invokes_ckb_sign_message(self):
        calls = []
        stdout_text = json.dumps(
            {
                "message": "hello",
                "address": "ckt1qtest",
                "signature": "0x" + "aa" * 65,
            }
        )

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout=stdout_text + "\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = sign_message_with_trezorctl(
                transport="webusb:000:1",
                coin="Testnet",
                path="m/44'/309'/0'/0/0",
                message="hello",
                work_dir=Path(tmp_dir),
                run=fake_run,
            )

        self.assertEqual(result.message, "hello")
        self.assertEqual(result.address, "ckt1qtest")
        self.assertEqual(result.signature, "0x" + "aa" * 65)
        self.assertEqual(calls[0][3:7], ["ckb", "sign-message", "--coin", "Testnet"])
        self.assertEqual(calls[0][-1], "hello")

    def test_verify_message_with_trezorctl_invokes_ckb_verify_message(self):
        calls = []

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(returncode=0, stdout="True\n")

        with tempfile.TemporaryDirectory() as tmp_dir:
            result = verify_message_with_trezorctl(
                transport="webusb:000:1",
                coin="Testnet",
                address="ckt1qtest",
                signature="0x" + "aa" * 65,
                message="hello",
                work_dir=Path(tmp_dir),
                run=fake_run,
            )

        self.assertTrue(result.valid)
        self.assertEqual(calls[0][3:7], ["ckb", "verify-message", "--coin", "Testnet"])
        self.assertEqual(calls[0][-3:], ["ckt1qtest", "0x" + "aa" * 65, "hello"])

    def test_verify_message_output_with_device_prompt_returns_final_boolean_line(self):
        result = parse_verify_message_output("Please confirm action on your Trezor device.\nTrue\n")

        self.assertTrue(result.valid)

    def test_trezorctl_cli_builds_command_and_uses_json_file(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]
        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )
        request = TrezorCtlRequest(
            transport="webusb:000:1",
            coin="Testnet",
            path="m/44'/309'/0'/0/0",
            tx=trezor_tx,
            trezorctl="trezorctl",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            command = build_trezorctl_command(request, Path(tmp_dir) / "trezor.sign_tx.json")

        self.assertEqual(command[:7], ["trezorctl", "-p", "webusb:000:1", "ckb", "sign-tx", "--coin", "Testnet"])
        self.assertEqual(command[7], "-n")
        self.assertEqual(command[8], "m/44'/309'/0'/0/0")

    def test_trezorctl_cli_auto_transport_omits_path_argument_for_real_device(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]
        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )
        request = TrezorCtlRequest(
            transport="auto",
            coin="Testnet",
            path="m/44'/309'/0'/0/0",
            tx=trezor_tx,
            trezorctl="trezorctl",
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            command = build_trezorctl_command(request, Path(tmp_dir) / "trezor.sign_tx.json")

        self.assertEqual(command[:5], ["trezorctl", "ckb", "sign-tx", "--coin", "Testnet"])
        self.assertNotIn("-p", command)

    def test_trezorctl_sign_tx_command_supports_chunkify(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]
        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )
        request = TrezorCtlRequest(
            transport="webusb:000:1",
            coin="Testnet",
            path="m/44'/309'/0'/0/0",
            tx=trezor_tx,
            trezorctl="trezorctl",
            chunkify=True,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            tx_json_path = Path(tmp_dir) / "trezor.sign_tx.json"
            command = build_trezorctl_command(request, tx_json_path)

        self.assertEqual(command[-2:], ["-C", str(tx_json_path)])

    def test_sign_with_trezorctl_mocks_subprocess_and_writes_artifacts(self):
        tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_outputs = [RpcTransaction.output_from_json(item) for item in sample_previous_outputs()]
        trezor_tx = rpc_transaction_to_trezor_sign_tx(
            tx,
            previous_outputs=previous_outputs,
            network="Testnet",
            path="m/44'/309'/0'/0/0",
        )
        request = TrezorCtlRequest(
            transport="webusb:000:1",
            coin="Testnet",
            path="m/44'/309'/0'/0/0",
            tx=trezor_tx,
        )
        calls = []

        def fake_run(command, text, stdout, stderr, check, env):
            calls.append(command)
            return SimpleNamespace(
                returncode=0,
                stdout="Signature: 0x" + "11" * 65 + "\nTX Hash: 0x" + "22" * 32 + "\n",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = sign_with_trezorctl(request, Path(tmp_dir), run=fake_run)
            tx_json = json.loads((Path(tmp_dir) / "trezor.sign_tx.json").read_text())
            command_json = json.loads((Path(tmp_dir) / "trezorctl.command.json").read_text())

        printed = stdout.getvalue()
        self.assertIn("[trezorctl] command", printed)
        self.assertIn("trezorctl -p webusb:000:1 ckb sign-tx", printed)
        self.assertIn("trezorctl.command.json", printed)
        self.assertEqual(result.tx_hash, "0x" + "22" * 32)
        self.assertEqual(tx_json["witnesses"], [{"witness_args": {"lock_size": 65}}])
        self.assertEqual(tx_json["sign_group_input_indices"], [0])
        self.assertEqual(tx_json["prev_txs"], {})
        self.assertEqual(command_json["command"][0], "trezorctl")
        self.assertEqual(calls[0][3:6], ["ckb", "sign-tx", "--coin"])

    def test_run_onchain_case_prints_sign_tx_json_before_signing(self):
        chain_tx = RpcTransaction.from_json(sample_rpc_transaction())
        previous_transactions = {
            tx_hash: RpcTransaction.from_json(prev_tx)
            for tx_hash, prev_tx in sample_previous_transactions().items()
        }
        case = OnchainTestCase(
            name="print-preview",
            network="Testnet",
            tx_hash=chain_tx.hash,
            address="ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
            path="m/44'/309'/0'/0/0",
            rpc_url="https://testnet.example",
            transport="auto",
            trezorctl="trezorctl",
            signature_policy="ignore",
            chunkify=False,
        )

        def fake_sign(request, work_dir):
            (work_dir / "trezorctl.output.txt").write_text(
                "Signature: 0x" + "11" * 65 + "\nTX Hash: " + chain_tx.hash + "\n"
            )
            return SimpleNamespace(signature="0x" + "11" * 65, tx_hash=chain_tx.hash)

        with tempfile.TemporaryDirectory() as tmp_dir:
            stdout = io.StringIO()
            with patch(
                "onchain_compare.runner.fetch_transaction",
                return_value={
                    "transaction": sample_rpc_transaction(),
                    "tx_status": {"status": "committed"},
                },
            ), patch(
                "onchain_compare.runner.resolve_previous_transactions",
                return_value=previous_transactions,
            ), patch("onchain_compare.runner.sign_with_trezorctl", side_effect=fake_sign):
                with redirect_stdout(stdout):
                    exit_code = run_onchain_case(
                        case,
                        no_sign=False,
                        out_dir=Path(tmp_dir),
                    )

        output = stdout.getvalue()
        preview_index = output.index("[print-preview] Trezor sign transaction JSON:")
        waiting_index = output.index("[print-preview] Waiting for confirmation on Trezor device...")
        self.assertEqual(exit_code, 0)
        self.assertLess(preview_index, waiting_index)
        self.assertIn('"inputs": [', output)
        self.assertIn('"outputs": [', output)
        self.assertIn('"prev_txs": {', output)
        self.assertIn('"sign_group_input_indices": [', output)

    def test_extract_standard_signature_from_witness_args_lock_field(self):
        signature = "0x" + "11" * 65
        witness = "0x5500000010000000550000005500000041000000" + "11" * 65

        self.assertEqual(extract_standard_signature(witness), signature)

    def test_extract_signing_group_chain_signature_uses_first_signing_group_witness(self):
        signature0 = "0x" + "11" * 65
        signature1 = "0x" + "22" * 65
        tx = RpcTransaction.from_json(
            {
                **sample_rpc_transaction(),
                "witnesses": [
                    "0x5500000010000000550000005500000041000000" + "11" * 65,
                    "0x5500000010000000550000005500000041000000" + "22" * 65,
                ],
            }
        )

        self.assertEqual(
            extract_signing_group_chain_signature(tx, signing_group_indexes=[1]),
            signature1,
        )
        self.assertNotEqual(
            extract_signing_group_chain_signature(tx, signing_group_indexes=[1]),
            signature0,
        )

    def test_compare_sign_result_requires_chain_hash_and_signature_match(self):
        chain_tx_hash = "0x" + "22" * 32
        chain_signature = "0x" + "33" * 65
        trezor_output = f"Signature: {chain_signature}\nTX Hash: {chain_tx_hash}\n"

        result = compare_sign_result(
            trezor_output,
            chain_tx_hash=chain_tx_hash,
            chain_signature=chain_signature,
        )

        self.assertTrue(result.tx_hash_matches)
        self.assertTrue(result.signature_matches)
        self.assertEqual(result.trezor_tx_hash, chain_tx_hash)
        self.assertEqual(result.trezor_signature, chain_signature)

    def test_load_case_file_merges_defaults_and_filters_by_name(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "network": "Testnet",
                            "address": "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
                            "path": "m/44'/309'/0'/0/0",
                            "transport": "webusb:000:1",
                            "signature_policy": "require",
                            "chunkify": True,
                        },
                        "cases": [
                            {
                                "name": "keep",
                                "tx_hash": "0x" + "44" * 32,
                            },
                            {
                                "name": "skip",
                                "tx_hash": "0x" + "55" * 32,
                                "signature_policy": "ignore",
                            },
                        ],
                    }
                )
                + "\n"
            )

            cases = load_case_file(case_file, selected_names=["keep"])

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].name, "keep")
        self.assertEqual(cases[0].network, "Testnet")
        self.assertEqual(cases[0].tx_hash, "0x" + "44" * 32)
        self.assertEqual(cases[0].signature_policy, "require")
        self.assertEqual(cases[0].trezorctl, "auto")
        self.assertTrue(cases[0].chunkify)

    def test_load_case_file_rejects_compare_signature_policy(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "network": "Testnet",
                            "signature_policy": "compare",
                        },
                        "cases": [
                            {
                                "name": "bad-policy",
                                "tx_hash": "0x" + "44" * 32,
                            }
                        ],
                    }
                )
                + "\n"
            )

            with self.assertRaisesRegex(ValueError, "unsupported signature_policy"):
                load_case_file(case_file)

    def test_mixed_lock_group_case_file_contains_both_signing_groups(self):
        cases = load_case_file(Path("cases.testnet.mnemonic.mixed-lock-groups-2x2.json"))
        by_name = {case.name: case for case in cases}

        self.assertIn("mixed-lock-groups-primary", by_name)
        self.assertIn("mixed-lock-groups-secondary", by_name)
        self.assertEqual(
            by_name["mixed-lock-groups-primary"].tx_hash,
            by_name["mixed-lock-groups-secondary"].tx_hash,
        )
        self.assertEqual(by_name["mixed-lock-groups-primary"].path, "m/44'/309'/0'/0/0")
        self.assertEqual(by_name["mixed-lock-groups-secondary"].path, "m/44'/309'/0'/0/1")

    def test_run_onchain_fixture_case_returns_compare_result_and_overrides_runtime_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            case_file = tmp_path / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "defaults": {
                            "network": "Testnet",
                            "address": "ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
                            "path": "m/44'/309'/0'/0/0",
                            "transport": "webusb:000:1",
                            "trezorctl": "trezorctl",
                            "signature_policy": "require",
                        },
                        "cases": [
                            {
                                "name": "output-with-type-script",
                                "tx_hash": "0x" + "44" * 32,
                            }
                        ],
                    }
                )
                + "\n"
            )
            out_dir = tmp_path / "artifacts"
            calls = []

            def fake_runner(case, *, no_sign, out_dir):
                calls.append((case, no_sign, out_dir))
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "compare.result.json").write_text(
                    json.dumps(
                        {
                            "tx_hash_matches": True,
                            "signature_matches": True,
                            "trezor_tx_hash": "0x" + "44" * 32,
                            "chain_tx_hash": "0x" + "44" * 32,
                            "trezor_signature": "0x" + "11" * 65,
                            "chain_signature": "0x" + "11" * 65,
                        }
                    )
                    + "\n"
                )
                return 0

            result = run_onchain_fixture_case(
                case_id="CKB-TX-012",
                fixture_name="output-with-type-script",
                case_file=case_file,
                out_dir=out_dir,
                transport="auto",
                trezorctl="/custom/trezorctl",
                rpc_url_override="https://testnet.example",
                no_sign=False,
                runner=fake_runner,
            )

        self.assertTrue(result.tx_hash_matches)
        self.assertTrue(result.signature_matches)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0].transport, "auto")
        self.assertEqual(calls[0][0].trezorctl, "/custom/trezorctl")
        self.assertEqual(calls[0][0].rpc_url, "https://testnet.example")
        self.assertFalse(calls[0][1])
        self.assertEqual(calls[0][2], out_dir)

    def test_run_onchain_fixture_case_missing_fixture_raises_named_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "different-fixture",
                                "tx_hash": "0x" + "44" * 32,
                            }
                        ]
                    }
                )
                + "\n"
            )

            with self.assertRaisesRegex(
                OnchainFixtureNotFound,
                "CKB-TX-012.*output-with-type-script",
            ):
                run_onchain_fixture_case(
                    case_id="CKB-TX-012",
                    fixture_name="output-with-type-script",
                    case_file=case_file,
                    out_dir=Path(tmp_dir) / "artifacts",
                    transport="auto",
                    trezorctl="trezorctl",
                    rpc_url_override=None,
                    no_sign=False,
                    runner=lambda case, no_sign, out_dir: 0,
                )

    def test_run_onchain_fixture_case_no_sign_generates_artifacts_then_raises_no_sign_marker(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            case_file = tmp_path / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "output-with-type-script",
                                "tx_hash": "0x" + "44" * 32,
                            }
                        ]
                    }
                )
                + "\n"
            )
            calls = []

            def fake_runner(case, *, no_sign, out_dir):
                calls.append(no_sign)
                out_dir.mkdir(parents=True, exist_ok=True)
                return 0

            with self.assertRaisesRegex(OnchainNoSignOnly, "CKB-TX-012"):
                run_onchain_fixture_case(
                    case_id="CKB-TX-012",
                    fixture_name="output-with-type-script",
                    case_file=case_file,
                    out_dir=tmp_path / "artifacts",
                    transport="auto",
                    trezorctl="trezorctl",
                    rpc_url_override=None,
                    no_sign=True,
                    runner=fake_runner,
                )

        self.assertEqual(calls, [True])

    def test_run_onchain_fixture_case_nonzero_runner_exit_raises_runtime_error(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "output-with-type-script",
                                "tx_hash": "0x" + "44" * 32,
                            }
                        ]
                    }
                )
                + "\n"
            )

            with self.assertRaisesRegex(RuntimeError, "CKB-TX-012.*exit code 2"):
                run_onchain_fixture_case(
                    case_id="CKB-TX-012",
                    fixture_name="output-with-type-script",
                    case_file=case_file,
                    out_dir=Path(tmp_dir) / "artifacts",
                    transport="auto",
                    trezorctl="trezorctl",
                    rpc_url_override=None,
                    no_sign=False,
                    runner=lambda case, no_sign, out_dir: 2,
                )

    def test_direct_trezorctl_get_address_writes_result_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            args = SimpleNamespace(
                trezorctl_action="get-address",
                out_dir=Path(tmp_dir),
                transport="webusb:000:1",
                network="Testnet",
                path="m/44'/309'/0'/0/0",
                trezorctl="trezorctl",
                show_display=False,
                chunkify=True,
            )
            with patch(
                "onchain_compare.cli.get_address_with_trezorctl",
                return_value=TrezorAddressResult(address="ckt1qtest"),
            ) as fake_get_address:
                with redirect_stdout(io.StringIO()):
                    exit_code = run_direct_trezorctl_action(args)

            result_json = json.loads((Path(tmp_dir) / "trezorctl.result.json").read_text())

        self.assertEqual(exit_code, 0)
        self.assertEqual(result_json, {"address": "ckt1qtest"})
        self.assertTrue(fake_get_address.call_args.kwargs["chunkify"])

    def test_load_case_file_rejects_duplicate_case_names(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            case_file = Path(tmp_dir) / "cases.json"
            case_file.write_text(
                json.dumps(
                    {
                        "cases": [
                            {"name": "dup", "tx_hash": "0x" + "11" * 32},
                            {"name": "dup", "tx_hash": "0x" + "22" * 32},
                        ]
                    }
                )
                + "\n"
            )

            with self.assertRaisesRegex(ValueError, "duplicate case name"):
                load_case_file(case_file)

if __name__ == "__main__":
    unittest.main()
