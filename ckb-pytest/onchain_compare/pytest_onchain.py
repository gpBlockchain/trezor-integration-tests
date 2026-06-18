from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

from .case_file import OnchainTestCase, load_case_file
from .runner import run_onchain_case
from .trezor_models import CompareResult


class OnchainFixtureNotFound(RuntimeError):
    pass


class OnchainNoSignOnly(RuntimeError):
    pass


OnchainRunner = Callable[[OnchainTestCase], int]


def resolve_case_file(case_file: Path, *, root: Path) -> Path:
    if case_file.is_absolute():
        return case_file
    return root / case_file


def load_case_by_fixture_name(case_file: Path, *, case_id: str, fixture_name: str) -> OnchainTestCase:
    cases = load_case_file(case_file)
    for case in cases:
        if case.name == fixture_name:
            return case
    raise OnchainFixtureNotFound(
        f"{case_id} fixture is not generated yet: {fixture_name}"
    )


def read_compare_result(path: Path) -> CompareResult:
    if not path.exists():
        raise RuntimeError(f"compare result was not written: {path}")
    payload = json.loads(path.read_text())
    return CompareResult(
        tx_hash_matches=payload["tx_hash_matches"],
        signature_matches=payload["signature_matches"],
        trezor_tx_hash=payload["trezor_tx_hash"],
        chain_tx_hash=payload["chain_tx_hash"],
        trezor_signature=payload["trezor_signature"],
        chain_signature=payload["chain_signature"],
    )


def run_onchain_fixture_case(
    *,
    case_id: str,
    fixture_name: str,
    case_file: Path,
    out_dir: Path,
    transport: str,
    trezorctl: str,
    rpc_url_override: str | None,
    no_sign: bool,
    runner: Callable[..., int] = run_onchain_case,
) -> CompareResult:
    case = load_case_by_fixture_name(
        case_file,
        case_id=case_id,
        fixture_name=fixture_name,
    )
    case = replace(
        case,
        transport=transport,
        trezorctl=trezorctl,
        rpc_url=rpc_url_override if rpc_url_override is not None else case.rpc_url,
    )
    exit_code = runner(case, no_sign=no_sign, out_dir=out_dir)
    if exit_code != 0:
        raise RuntimeError(f"{case_id} fixture {fixture_name} failed with exit code {exit_code}")
    if no_sign:
        raise OnchainNoSignOnly(
            f"{case_id} generated on-chain artifacts with --onchain-no-sign; signing comparison skipped"
        )
    return read_compare_result(out_dir / "compare.result.json")
