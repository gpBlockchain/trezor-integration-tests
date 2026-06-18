from __future__ import annotations

from .constants import INT_TO_HASH_TYPE

CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
BECH32M_CONST = 0x2BC830A3


def polymod(values: list[int]) -> int:
    chk = 1
    generator = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    for value in values:
        top = chk >> 25
        chk = (chk & 0x1FFFFFF) << 5 ^ value
        for i in range(5):
            if (top >> i) & 1:
                chk ^= generator[i]
    return chk


def hrp_expand(hrp: str) -> list[int]:
    return [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]


def convertbits(data: list[int], from_bits: int, to_bits: int, pad: bool) -> list[int]:
    acc = 0
    bits = 0
    result = []
    maxv = (1 << to_bits) - 1
    max_acc = (1 << (from_bits + to_bits - 1)) - 1
    for value in data:
        if value < 0 or value >> from_bits:
            raise ValueError("invalid data range while converting bits")
        acc = ((acc << from_bits) | value) & max_acc
        bits += from_bits
        while bits >= to_bits:
            bits -= to_bits
            result.append((acc >> bits) & maxv)
    if pad:
        if bits:
            result.append((acc << (to_bits - bits)) & maxv)
    elif bits >= from_bits or ((acc << (to_bits - bits)) & maxv):
        raise ValueError("invalid padding while converting bits")
    return result


def decode_ckb_full_address(address: str) -> dict[str, str]:
    if address.lower() != address and address.upper() != address:
        raise ValueError("mixed-case Bech32 address")

    address = address.lower()
    separator = address.rfind("1")
    if separator < 1 or separator + 7 > len(address):
        raise ValueError("invalid Bech32 separator or checksum length")

    hrp = address[:separator]
    data = []
    for ch in address[separator + 1 :]:
        idx = CHARSET.find(ch)
        if idx == -1:
            raise ValueError(f"invalid Bech32 character: {ch!r}")
        data.append(idx)

    if polymod(hrp_expand(hrp) + data) != BECH32M_CONST:
        raise ValueError("invalid Bech32m checksum")

    payload = bytes(convertbits(data[:-6], 5, 8, False))
    if len(payload) < 35 or payload[0] != 0:
        raise ValueError("only CKB2021 full addresses are supported")

    hash_type = payload[33]
    if hash_type not in INT_TO_HASH_TYPE:
        raise ValueError(f"unsupported CKB hash_type byte: {hash_type}")

    return {
        "code_hash": "0x" + payload[1:33].hex(),
        "hash_type": INT_TO_HASH_TYPE[hash_type],
        "args": "0x" + payload[34:].hex(),
    }

