from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from onchain_compare.artifacts import ArtifactStore
from onchain_compare.constants import DEFAULT_PATH, DEFAULT_RPC_URLS
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
    resolve_case_file,
    run_onchain_fixture_case,
)
from onchain_compare.trezorctl_client import TrezorCtlClient
from onchain_compare.trezorctl_locator import resolve_trezorctl
from onchain_compare.transport import resolve_transport


def load_local_pytest_config() -> dict[str, Any]:
    config_file = ROOT / "pytest.local.json"
    if not config_file.exists():
        return {}
    return json.loads(config_file.read_text())


LOCAL_PYTEST_CONFIG = load_local_pytest_config()


def local_option(name: str, default: Any = None) -> Any:
    return LOCAL_PYTEST_CONFIG.get(name, default)


def local_bool_option(name: str) -> bool:
    return bool(LOCAL_PYTEST_CONFIG.get(name, False))


def pytest_addoption(parser):
    parser.addoption("--trezor-transport", default=local_option("trezor_transport", "auto"))
    parser.addoption("--trezorctl", default=local_option("trezorctl", "auto"))
    parser.addoption("--trezorctl-debug", action="store_true", default=local_bool_option("trezorctl_debug"))
    parser.addoption("--artifact-dir", default=local_option("artifact_dir", "runs/pytest"))
    parser.addoption("--onchain-case-file", default=local_option("onchain_case_file", "cases.testnet.hardware.json"))
    parser.addoption("--onchain-no-sign", action="store_true", default=local_bool_option("onchain_no_sign"))
    parser.addoption("--ckb-rpc-url", default=local_option("ckb_rpc_url"))
    parser.addoption("--ckb-owner-address", default=local_option("ckb_owner_address"))
    parser.addoption("--run-device", action="store_true", default=local_bool_option("run_device"))
    parser.addoption("--run-onchain", action="store_true", default=local_bool_option("run_onchain"))
    parser.addoption("--run-manual-ui", action="store_true", default=local_bool_option("run_manual_ui"))
    parser.addoption("--run-slow", action="store_true", default=local_bool_option("run_slow"))


def pytest_configure(config):
    for key, value in LOCAL_PYTEST_CONFIG.get("env", {}).items():
        os.environ[str(key)] = str(value)


def pytest_collection_modifyitems(config, items):
    skip_device = pytest.mark.skip(reason="requires --run-device")
    skip_onchain = pytest.mark.skip(reason="requires --run-onchain")
    skip_manual_ui = pytest.mark.skip(reason="requires --run-manual-ui")
    skip_slow = pytest.mark.skip(reason="requires --run-slow")
    auto_run_device = should_auto_run_device(config.invocation_params.args)
    auto_run_manual_ui = should_auto_run_manual_ui(config.invocation_params.args)
    auto_run_onchain = should_auto_run_onchain(config.invocation_params.args)
    auto_run_slow = should_auto_run_slow(config.invocation_params.args)

    for item in items:
        if "device" in item.keywords and not config.getoption("--run-device") and not auto_run_device:
            item.add_marker(skip_device)
        if "onchain" in item.keywords and not config.getoption("--run-onchain") and not auto_run_onchain:
            item.add_marker(skip_onchain)
        if "manual_ui" in item.keywords and not config.getoption("--run-manual-ui") and not auto_run_manual_ui:
            item.add_marker(skip_manual_ui)
        if "slow" in item.keywords and not config.getoption("--run-slow") and not auto_run_slow:
            item.add_marker(skip_slow)


@pytest.fixture
def trezorctl_binary(pytestconfig) -> str:
    return resolve_trezorctl(pytestconfig.getoption("--trezorctl"), project_root=ROOT)


@pytest.fixture
def trezor_transport(pytestconfig, trezorctl_binary) -> str:
    return resolve_transport(pytestconfig.getoption("--trezor-transport"), trezorctl=trezorctl_binary)


@pytest.fixture
def trezorctl_debug(pytestconfig) -> bool:
    return bool(pytestconfig.getoption("--trezorctl-debug")) or should_auto_debug_trezorctl(
        pytestconfig.invocation_params.args
    )


@pytest.fixture
def artifact_store(pytestconfig) -> ArtifactStore:
    return ArtifactStore(Path(pytestconfig.getoption("--artifact-dir")))


@pytest.fixture
def trezorctl_client(artifact_store, request, trezor_transport, trezorctl_binary, trezorctl_debug) -> TrezorCtlClient:
    return TrezorCtlClient(
        transport=trezor_transport,
        trezorctl=trezorctl_binary,
        artifact_dir=artifact_store.case_dir(request.node.nodeid),
        debug=trezorctl_debug,
    )


@pytest.fixture
def ckb_rpc_url(pytestconfig) -> str:
    return pytestconfig.getoption("--ckb-rpc-url") or DEFAULT_RPC_URLS["Mainnet"]


@pytest.fixture
def ckb_owner_address(pytestconfig) -> str | None:
    return pytestconfig.getoption("--ckb-owner-address")


@pytest.fixture
def default_ckb_path() -> str:
    return DEFAULT_PATH


@pytest.fixture
def testnet_network() -> str:
    return "Testnet"


@pytest.fixture
def mainnet_network() -> str:
    return "Mainnet"


@pytest.fixture
def onchain_compare_case(pytestconfig, artifact_store, request, trezor_transport, trezorctl_binary):
    def _run(case_id: str, *, fixture_name: str):
        auto_run_onchain = should_auto_run_onchain(pytestconfig.invocation_params.args)
        if not pytestconfig.getoption("--run-onchain") and not auto_run_onchain:
            pytest.skip(f"{case_id} requires --run-onchain and fixture {fixture_name}")
        case_file = resolve_case_file(
            Path(pytestconfig.getoption("--onchain-case-file")),
            root=ROOT,
        )
        try:
            return run_onchain_fixture_case(
                case_id=case_id,
                fixture_name=fixture_name,
                case_file=case_file,
                out_dir=artifact_store.case_dir(request.node.nodeid),
                transport=trezor_transport,
                trezorctl=trezorctl_binary,
                rpc_url_override=pytestconfig.getoption("--ckb-rpc-url"),
                no_sign=bool(pytestconfig.getoption("--onchain-no-sign")),
            )
        except OnchainFixtureNotFound as exc:
            pytest.skip(str(exc))
        except OnchainNoSignOnly as exc:
            pytest.skip(str(exc))

    return _run
