from __future__ import annotations

from .common import strip_0x
from .trezor_models import CompareResult
from .trezorctl_cli import parse_trezorctl_output


def uint32_le_at(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 4], "little")


def extract_standard_signature(witness_hex: str) -> str | None:
    raw = bytes.fromhex(strip_0x(witness_hex))
    if not raw or len(raw) < 16:
        return None

    total_size = uint32_le_at(raw, 0)
    lock_offset = uint32_le_at(raw, 4)
    input_type_offset = uint32_le_at(raw, 8)
    if total_size > len(raw) or lock_offset >= input_type_offset:
        return None

    lock_field = raw[lock_offset:input_type_offset]
    if len(lock_field) < 4:
        return None
    lock_len = uint32_le_at(lock_field, 0)
    lock_value = lock_field[4 : 4 + lock_len]
    if lock_len != 65 or len(lock_value) != 65:
        return None
    return "0x" + lock_value.hex()


def compare_sign_result(
    trezor_output: str,
    *,
    chain_tx_hash: str,
    chain_signature: str | None,
) -> CompareResult:
    trezor_result = parse_trezorctl_output(trezor_output)
    normalized_chain_tx_hash = chain_tx_hash.lower()
    normalized_chain_signature = chain_signature.lower() if chain_signature else None
    return CompareResult(
        tx_hash_matches=trezor_result.tx_hash == normalized_chain_tx_hash,
        signature_matches=(
            None
            if normalized_chain_signature is None
            else trezor_result.signature == normalized_chain_signature
        ),
        trezor_tx_hash=trezor_result.tx_hash,
        chain_tx_hash=normalized_chain_tx_hash,
        trezor_signature=trezor_result.signature,
        chain_signature=normalized_chain_signature,
    )

