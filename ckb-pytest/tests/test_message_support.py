from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.device, pytest.mark.p2]
from message_helpers import assert_sign_verify_roundtrip


def test_ckb_msg_007_utf8_mixed_message(trezorctl_client, default_ckb_path, testnet_network):
    assert_sign_verify_roundtrip(
        trezorctl_client,
        coin=testnet_network,
        path=default_ckb_path,
        message="CKB UTF-8: 你好，Nervos 🚀 café",
        expected_utf8_len=37,
    )
