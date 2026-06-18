from __future__ import annotations

import pytest

from onchain_compare.trezor_models import (
    TrezorCellDep,
    TrezorInput,
    TrezorOutput,
    TrezorSignTx,
)


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.negative, pytest.mark.p1]


def test_ckb_addr_005_non_ckb_slip44_path_rejected(trezorctl_client, testnet_network):
    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_get_address(coin=testnet_network, path="m/44'/0'/0'/0/0")


def test_ckb_addr_006_invalid_network_rejected(trezorctl_client, default_ckb_path):
    result = trezorctl_client.run_raw(
        ["ckb", "get-address", "--coin", "InvalidNet", "-n", default_ckb_path],
        operation="CKB-ADDR-006",
    )

    assert result.returncode != 0
    assert "Invalid" in result.stdout or "Error" in result.stdout


def test_ckb_tx_005_zero_inputs_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = TrezorSignTx(
        network=testnet_network,
        path=default_ckb_path,
        inputs=[],
        outputs=[minimal_output()],
        cell_deps=[],
        fee=100000,
    )

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def test_ckb_tx_006_zero_outputs_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = TrezorSignTx(
        network=testnet_network,
        path=default_ckb_path,
        inputs=[minimal_input()],
        outputs=[],
        cell_deps=[],
        fee=100000,
    )

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def test_ckb_tx_007_input_tx_hash_not_32_bytes_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = minimal_tx(default_ckb_path, testnet_network)
    tx.inputs[0] = TrezorInput(tx_hash="11" * 31, index=0, since=0)

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def test_ckb_tx_008_lock_code_hash_not_32_bytes_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = minimal_tx(default_ckb_path, testnet_network)
    tx.outputs[0] = TrezorOutput(
        capacity=6100000000,
        lock_code_hash="9bd7" * 15,
        lock_hash_type=1,
        lock_args="22" * 20,
        data="",
    )

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def test_ckb_tx_009_invalid_lock_hash_type_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = minimal_tx(default_ckb_path, testnet_network)
    tx.outputs[0] = TrezorOutput(
        capacity=6100000000,
        lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
        lock_hash_type=3,
        lock_args="22" * 20,
        data="",
    )

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def test_ckb_tx_010_cell_dep_tx_hash_not_32_bytes_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = minimal_tx(default_ckb_path, testnet_network)
    tx.cell_deps.append(TrezorCellDep(tx_hash="33" * 31, index=0, dep_type=1))

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def test_ckb_tx_011_invalid_cell_dep_type_rejected(trezorctl_client, default_ckb_path, testnet_network):
    tx = minimal_tx(default_ckb_path, testnet_network)
    tx.cell_deps.append(TrezorCellDep(tx_hash="33" * 32, index=0, dep_type=9))

    with pytest.raises(RuntimeError):
        trezorctl_client.ckb_sign_tx(coin=testnet_network, path=default_ckb_path, tx=tx)


def minimal_input() -> TrezorInput:
    return TrezorInput(tx_hash="11" * 32, index=0, since=0)


def minimal_output() -> TrezorOutput:
    return TrezorOutput(
        capacity=6100000000,
        lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
        lock_hash_type=1,
        lock_args="22" * 20,
        data="",
    )


def minimal_tx(path: str, network: str) -> TrezorSignTx:
    return TrezorSignTx(
        network=network,
        path=path,
        inputs=[minimal_input()],
        outputs=[minimal_output()],
        cell_deps=[],
        fee=100000,
    )
