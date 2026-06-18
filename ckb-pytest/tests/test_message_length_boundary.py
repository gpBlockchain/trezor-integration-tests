from __future__ import annotations

import pytest

from message_helpers import assert_sign_verify_roundtrip


pytestmark = [pytest.mark.integration, pytest.mark.device]

SIGN_MESSAGE_THP_MAX_ASCII_BYTES = 65475
SIGN_MESSAGE_THP_FIRST_ERROR_BYTES = 65476
VERIFY_MESSAGE_THP_MAX_ASCII_BYTES = 65331
VERIFY_MESSAGE_THP_FIRST_ERROR_BYTES = 65332


def require_thp_or_auto_transport(trezor_transport: str, case_id: str) -> None:
    if trezor_transport != "auto" and not trezor_transport.startswith("webusb:"):
        pytest.skip(f"{case_id} targets THP/WebUSB transport max encrypted message length")


@pytest.mark.p2
def test_ckb_msg_008_length_boundary_empty_0_bytes(trezorctl_client, default_ckb_path, testnet_network):
    assert_sign_verify_roundtrip(
        trezorctl_client,
        coin=testnet_network,
        path=default_ckb_path,
        message="",
        expected_utf8_len=0,
    )


@pytest.mark.p2
def test_ckb_msg_009_length_boundary_single_byte(trezorctl_client, default_ckb_path, testnet_network):
    assert_sign_verify_roundtrip(
        trezorctl_client,
        coin=testnet_network,
        path=default_ckb_path,
        message="a",
        expected_utf8_len=1,
    )


@pytest.mark.p2
def test_ckb_msg_010_length_boundary_256_byte_ascii(trezorctl_client, default_ckb_path, testnet_network):
    assert_sign_verify_roundtrip(
        trezorctl_client,
        coin=testnet_network,
        path=default_ckb_path,
        message="a" * 256,
        expected_utf8_len=256,
    )


@pytest.mark.p2
def test_ckb_msg_011_length_boundary_255_byte_utf8(trezorctl_client, default_ckb_path, testnet_network):
    assert_sign_verify_roundtrip(
        trezorctl_client,
        coin=testnet_network,
        path=default_ckb_path,
        message="中" * 85,
        expected_utf8_len=255,
    )


@pytest.mark.skip("USB write failed: LIBUSB_ERROR_NO_DEVICE")
@pytest.mark.p1
@pytest.mark.slow
def test_ckb_msg_012_length_boundary_max_sign_thp_ok_65475_bytes(
    trezorctl_client,
    trezor_transport,
    default_ckb_path,
    testnet_network,
):
    require_thp_or_auto_transport(trezor_transport, "CKB-MSG-012")

    message = "a" * SIGN_MESSAGE_THP_MAX_ASCII_BYTES
    signed = trezorctl_client.ckb_sign_message(
        coin=testnet_network,
        path=default_ckb_path,
        message=message,
    )

    assert len(message.encode("utf-8")) == SIGN_MESSAGE_THP_MAX_ASCII_BYTES
    assert signed.message == message
    assert signed.signature.startswith("0x")
    assert (len(signed.signature) - 2) // 2 == 65


@pytest.mark.p1
@pytest.mark.negative
@pytest.mark.skip("too slow")
def test_ckb_msg_013_length_boundary_first_sign_thp_error_65476_bytes(
    trezorctl_client,
    trezor_transport,
    default_ckb_path,
    testnet_network,
):
    require_thp_or_auto_transport(trezor_transport, "CKB-MSG-013")

    with pytest.raises(RuntimeError, match="Encoded message is too long"):
        trezorctl_client.ckb_sign_message(
            coin=testnet_network,
            path=default_ckb_path,
            message="a" * SIGN_MESSAGE_THP_FIRST_ERROR_BYTES,
        )


@pytest.mark.p1
@pytest.mark.slow
def test_ckb_msg_014_length_boundary_max_roundtrip_ok_65331_bytes(
    trezorctl_client,
    trezor_transport,
    default_ckb_path,
    testnet_network,
):
    require_thp_or_auto_transport(trezor_transport, "CKB-MSG-014")

    assert_sign_verify_roundtrip(
        trezorctl_client,
        coin=testnet_network,
        path=default_ckb_path,
        message="a" * VERIFY_MESSAGE_THP_MAX_ASCII_BYTES,
        expected_utf8_len=VERIFY_MESSAGE_THP_MAX_ASCII_BYTES,
    )


@pytest.mark.p1
@pytest.mark.negative
@pytest.mark.skip("too slow")
def test_ckb_msg_015_length_boundary_first_verify_thp_error_65332_bytes(
    trezorctl_client,
    trezor_transport,
    testnet_network,
):
    require_thp_or_auto_transport(trezor_transport, "CKB-MSG-015")

    with pytest.raises(RuntimeError, match="Encoded message is too long"):
        trezorctl_client.ckb_verify_message(
            coin=testnet_network,
            address="ckt1qzda0cr08m85hc8jlnfp3zer7xulejywt49kt2rr0vthywaa50xwsqwlzl0nvrypnv8m34xd5n6ruvyakzw0v2s07n2ed",
            signature="0x" + "11" * 65,
            message="a" * VERIFY_MESSAGE_THP_FIRST_ERROR_BYTES,
        )
