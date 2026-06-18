from __future__ import annotations

import pytest

from onchain_compare.constants import DEFAULT_TESTNET_ADDRESS
from onchain_compare.synthetic_prevtx import synthetic_prev_tx_for_outputs
from onchain_compare.trezor_models import (
    TrezorInput,
    TrezorOutput,
    TrezorSignTx,
    TrezorWitness,
    TrezorWitnessArgs,
)


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.p0]


def test_ckb_env_001_get_features_exposes_ckb_capability(trezorctl_client):
    result = trezorctl_client.get_features()
    assert result.returncode == 0
    assert "CKB" in result.stdout


def test_ckb_addr_001_testnet_address(trezorctl_client, default_ckb_path, testnet_network):
    result = trezorctl_client.ckb_get_address(coin=testnet_network, path=default_ckb_path)
    assert result.address.startswith("ckt1")


def test_ckb_addr_002_mainnet_address(trezorctl_client, default_ckb_path, mainnet_network):
    result = trezorctl_client.ckb_get_address(coin=mainnet_network, path=default_ckb_path)

    assert result.address.startswith("ckb1")


# @pytest.mark.manual_ui
def test_ckb_addr_003_testnet_address_display(trezorctl_client, default_ckb_path, testnet_network):
    result = trezorctl_client.ckb_get_address(
        coin=testnet_network,
        path=default_ckb_path,
        show_display=True,
    )

    assert result.address == DEFAULT_TESTNET_ADDRESS


def test_ckb_msg_001_sign_short_testnet_message(trezorctl_client, default_ckb_path, testnet_network):
    result = trezorctl_client.ckb_sign_message(
        coin=testnet_network,
        path=default_ckb_path,
        message="hello ckb",
    )

    assert result.address.startswith("ckt1")
    assert result.signature.startswith("0x")
    assert (len(result.signature) - 2) // 2 == 65


def test_ckb_msg_002_verify_valid_testnet_message(trezorctl_client, default_ckb_path, testnet_network):
    signed = trezorctl_client.ckb_sign_message(
        coin=testnet_network,
        path=default_ckb_path,
        message="hello ckb",
    )
    verified = trezorctl_client.ckb_verify_message(
        coin=testnet_network,
        address=signed.address,
        signature=signed.signature,
        message="hello ckb",
    )

    assert verified.valid is True


def test_ckb_tx_001_sign_minimal_testnet_tx(trezorctl_client, default_ckb_path, testnet_network):
    previous_output = TrezorOutput(
        capacity=24400100000,
        lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
        lock_hash_type=1,
        lock_args="22" * 20,
    )
    previous_tx_hash, previous_tx = synthetic_prev_tx_for_outputs([previous_output])
    tx = TrezorSignTx(
        network=testnet_network,
        path=default_ckb_path,
        inputs=[
            TrezorInput(
                tx_hash=previous_tx_hash,
                index=0,
                since=0,
            )
        ],
        outputs=[
            TrezorOutput(
                capacity=6100000000,
                lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                lock_hash_type=4,
                lock_args="22" * 40,
                type_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                type_hash_type=1,
                type_args="22" * 40,
                data="22" * 124,
            ),TrezorOutput(
                capacity=6100000000,
                lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                lock_hash_type=1,
                lock_args="22" * 40,
                data="",
            ),
            TrezorOutput(
                capacity=6100000000,
                lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                lock_hash_type=1,
                lock_args="22" * 40,
                data="",
            ),TrezorOutput(
                capacity=6100000000,
                lock_code_hash="9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8",
                lock_hash_type=1,
                lock_args="22" * 400,
                data="",
            )
        ],
        cell_deps=[],
        fee=10000,
        witnesses=[TrezorWitness(witness_args=TrezorWitnessArgs())],
        sign_group_input_indices=[0],
        prev_txs={previous_tx_hash: previous_tx},
    )

    result = trezorctl_client.ckb_sign_tx(
        coin=testnet_network,
        path=default_ckb_path,
        tx=tx,
    )

    assert result.signature.startswith("0x")
    assert (len(result.signature) - 2) // 2 == 65
    assert result.tx_hash.startswith("0x")
    assert (len(result.tx_hash) - 2) // 2 == 32
