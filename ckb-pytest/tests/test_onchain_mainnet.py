from __future__ import annotations

import pytest

from onchain_compare.case_file import OnchainTestCase
from onchain_compare.runner import run_onchain_case


pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.onchain, pytest.mark.p0]


def test_ckb_tx_035_real_mainnet_transfer_5d357bc4(
    artifact_store,
    mainnet_network,
    default_ckb_path,
    trezor_transport,
    trezorctl_binary,
    ckb_rpc_url,
    ckb_owner_address,
    request,
):
    if ckb_owner_address is None:
        pytest.skip("CKB-TX-035 requires --ckb-owner-address for the input owner lock")

    case = OnchainTestCase(
        name="CKB-TX-035-real-mainnet-transfer-5d357bc4",
        network=mainnet_network,
        tx_hash="0x5d357bc4dfbfa2bc59651d82c8358358b22ec126414182d53843a01c15a08673",
        address=ckb_owner_address,
        path=default_ckb_path,
        rpc_url=ckb_rpc_url,
        transport=trezor_transport,
        trezorctl=trezorctl_binary,
        signature_policy="compare",
        chunkify=False,
    )

    exit_code = run_onchain_case(
        case,
        no_sign=False,
        out_dir=artifact_store.case_dir(request.node.nodeid),
    )

    assert exit_code == 0
