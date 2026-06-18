from __future__ import annotations


def strip_0x(value: str) -> str:
    return value[2:] if value.startswith("0x") else value


def ensure_0x(value: str) -> str:
    return value if value.startswith("0x") else "0x" + value


def hex_int(value: str) -> int:
    return int(value, 16)


def hex_quantity(value: int) -> str:
    return hex(value)


def sanitize_name(name: str) -> str:
    import re

    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip("-")
    if not sanitized:
        raise ValueError("case name must contain at least one safe character")
    return sanitized

