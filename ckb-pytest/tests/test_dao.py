from __future__ import annotations

import pytest

from onchain_compare.address import decode_ckb_full_address
from onchain_compare.common import strip_0x
from onchain_compare.synthetic_prevtx import mock_dao_withdraw2_sign_tx


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.p1]


def test_ckb_tx_052_dao_deposit(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-052", fixture_name="dao-deposit")

    assert result.tx_hash_matches is True
    assert result.signature_matches is True


@pytest.mark.skip(
    "CKB-TX-053 is kept as a DAO-specific regression case; run CKB-TX-054 for focused "
    "top-level header_deps coverage, then revalidate DAO withdraw1 expectations before unskipping"
)
def test_ckb_tx_053_dao_withdraw1(onchain_compare_case):
    result = onchain_compare_case("CKB-TX-053", fixture_name="dao-withdraw1")

    assert result.tx_hash_matches is True
    assert result.signature_matches is True


@pytest.mark.skip(
    "CKB-TX-051 is expected to pass once DAO withdraw2 compensation is supported; "
    "current firmware rejects it with DataError: Inputs do not cover outputs"
)
def test_ckb_tx_051_mock_dao_withdraw2_should_pass(
    trezorctl_client,
    default_ckb_path,
    testnet_network,
):
    address = trezorctl_client.ckb_get_address(
        coin=testnet_network,
        path=default_ckb_path,
    ).address
    lock_args = strip_0x(decode_ckb_full_address(address)["args"])
    tx = mock_dao_withdraw2_sign_tx(
        network=testnet_network,
        path=default_ckb_path,
        lock_args=lock_args,
    )

    trezorctl_client.ckb_sign_tx(
        coin=testnet_network,
        path=default_ckb_path,
        tx=tx,
    )
