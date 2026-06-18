from __future__ import annotations

from onchain_compare.constants import DEFAULT_TESTNET_ADDRESS


def assert_sign_verify_roundtrip(
    trezorctl_client,
    *,
    coin: str,
    path: str,
    message: str,
    expected_utf8_len: int,
) -> None:
    assert len(message.encode("utf-8")) == expected_utf8_len

    signed = trezorctl_client.ckb_sign_message(
        coin=coin,
        path=path,
        message=message,
    )

    assert signed.message == message
    assert signed.address == DEFAULT_TESTNET_ADDRESS
    assert signed.signature.startswith("0x")
    assert (len(signed.signature) - 2) // 2 == 65

    verified = trezorctl_client.ckb_verify_message(
        coin=coin,
        address=signed.address,
        signature=signed.signature,
        message=message,
    )

    assert verified.valid is True
