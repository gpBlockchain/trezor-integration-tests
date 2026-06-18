from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import ensure_0x
from .constants import DEFAULT_PATH, DEFAULT_RPC_URLS, DEFAULT_TESTNET_ADDRESS


@dataclass(frozen=True)
class OnchainTestCase:
    name: str
    network: str
    tx_hash: str
    address: str
    path: str
    rpc_url: str | None
    transport: str
    trezorctl: str
    signature_policy: str
    chunkify: bool


def make_case(raw_case: dict[str, Any], defaults: dict[str, Any]) -> OnchainTestCase:
    merged = {**defaults, **raw_case}
    missing = [field for field in ("name", "tx_hash") if not merged.get(field)]
    if missing:
        raise ValueError(f"case is missing required field(s): {', '.join(missing)}")

    network = merged.get("network", "Testnet")
    if network not in DEFAULT_RPC_URLS:
        raise ValueError(f"unsupported network for case {merged['name']}: {network}")

    signature_policy = merged.get("signature_policy", "compare")
    if signature_policy not in {"ignore", "compare", "require"}:
        raise ValueError(
            f"unsupported signature_policy for case {merged['name']}: {signature_policy}"
        )

    return OnchainTestCase(
        name=merged["name"],
        network=network,
        tx_hash=ensure_0x(merged["tx_hash"]),
        address=merged.get("address", DEFAULT_TESTNET_ADDRESS),
        path=merged.get("path", DEFAULT_PATH),
        rpc_url=merged.get("rpc_url"),
        transport=merged.get("transport", "webusb:000:1"),
        trezorctl=merged.get("trezorctl", "auto"),
        signature_policy=signature_policy,
        chunkify=bool(merged.get("chunkify", False)),
    )


def load_case_file(
    case_file: Path, selected_names: list[str] | None = None
) -> list[OnchainTestCase]:
    payload = json.loads(case_file.read_text())
    defaults = payload.get("defaults", {})
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("case file must contain a non-empty cases array")

    selected = set(selected_names or [])
    cases = []
    seen_names = set()
    for raw_case in raw_cases:
        case = make_case(raw_case, defaults)
        if case.name in seen_names:
            raise ValueError(f"duplicate case name: {case.name}")
        seen_names.add(case.name)
        if selected and case.name not in selected:
            continue
        cases.append(case)

    missing_selected = selected - seen_names
    if missing_selected:
        joined = ", ".join(sorted(missing_selected))
        raise ValueError(f"selected case name(s) not found: {joined}")
    if selected and not cases:
        raise ValueError("no cases selected")
    return cases
