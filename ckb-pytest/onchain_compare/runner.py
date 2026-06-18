from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .address import decode_ckb_full_address
from .case_file import OnchainTestCase
from .common import ensure_0x, sanitize_name, strip_0x
from .compare import compare_sign_result, extract_standard_signature
from .constants import DEFAULT_RPC_URLS
from .converter import resolve_signing_group, rpc_transaction_to_trezor_sign_tx
from .rpc_client import (
    fetch_transaction,
    resolve_previous_outputs_from_transactions,
    resolve_previous_transactions,
)
from .rpc_models import RpcTransaction
from .trezor_json import to_trezorctl_json
from .trezor_models import TrezorCtlRequest
from .trezorctl_cli import sign_with_trezorctl


def default_run_dir(tx_hash: str) -> Path:
    return Path("runs") / strip_0x(tx_hash)[:16]


def extract_signing_group_chain_signature(
    chain_tx: RpcTransaction, *, signing_group_indexes: list[int]
) -> str | None:
    first_signing_witness_index = signing_group_indexes[0]
    return extract_standard_signature(
        chain_tx.witnesses[first_signing_witness_index]
        if first_signing_witness_index < len(chain_tx.witnesses)
        else "0x"
    )


def run_onchain_case(
    case: OnchainTestCase,
    *,
    no_sign: bool,
    out_dir: Path,
) -> int:
    rpc_url = case.rpc_url or DEFAULT_RPC_URLS[case.network]
    out_dir.mkdir(parents=True, exist_ok=True)

    chain_result = fetch_transaction(rpc_url, case.tx_hash)
    chain_tx = RpcTransaction.from_json(chain_result["transaction"])
    chain_status = chain_result.get("tx_status", {})
    chain_hash = chain_tx.hash.lower()
    if chain_hash != ensure_0x(case.tx_hash).lower():
        raise RuntimeError(f"RPC returned unexpected tx hash: {chain_hash}")

    previous_transactions = resolve_previous_transactions(rpc_url, chain_tx)
    previous_outputs = resolve_previous_outputs_from_transactions(
        chain_tx, previous_transactions
    )
    target_lock = decode_ckb_full_address(case.address)
    signing_group_indexes = resolve_signing_group(previous_outputs, target_lock)
    trezor_tx = rpc_transaction_to_trezor_sign_tx(
        chain_tx,
        previous_outputs=previous_outputs,
        previous_transactions=previous_transactions,
        sign_group_input_indices=signing_group_indexes,
        network=case.network,
        path=case.path,
    )
    chain_signature = extract_signing_group_chain_signature(
        chain_tx, signing_group_indexes=signing_group_indexes
    )

    (out_dir / "case.json").write_text(json.dumps(asdict(case), indent=2) + "\n")
    (out_dir / "rpc.transaction.json").write_text(
        json.dumps(chain_result, indent=2) + "\n"
    )
    (out_dir / "previous.outputs.json").write_text(
        json.dumps([output.to_json() for output in previous_outputs], indent=2) + "\n"
    )
    trezor_sign_tx_json = json.dumps(to_trezorctl_json(trezor_tx), indent=2)
    (out_dir / "trezor.sign_tx.json").write_text(trezor_sign_tx_json + "\n")

    print(f"[{case.name}] Fetched chain transaction: {chain_hash}")
    print(f"[{case.name}] Status: {chain_status.get('status')}")
    print(f"[{case.name}] Resolved fee: {trezor_tx.fee} shannons")
    print(f"[{case.name}] Wrote Trezor sign JSON: {out_dir / 'trezor.sign_tx.json'}")
    print(f"[{case.name}] Trezor sign transaction JSON:")
    print(trezor_sign_tx_json)

    if no_sign:
        print(f"[{case.name}] Skipped Trezor signing because --no-sign was set.")
        return 0

    print(f"[{case.name}] Waiting for confirmation on Trezor device...")
    request = TrezorCtlRequest(
        transport=case.transport,
        coin=case.network,
        path=case.path,
        tx=trezor_tx,
        trezorctl=case.trezorctl,
        chunkify=case.chunkify,
    )
    sign_result = sign_with_trezorctl(request, out_dir)
    trezor_output = (out_dir / "trezorctl.output.txt").read_text()

    compare_result = compare_sign_result(
        trezor_output,
        chain_tx_hash=chain_hash,
        chain_signature=chain_signature if case.signature_policy != "ignore" else None,
    )
    (out_dir / "compare.result.json").write_text(
        json.dumps(asdict(compare_result), indent=2) + "\n"
    )

    print(f"Signature: {sign_result.signature}")
    print(f"TX Hash: {sign_result.tx_hash}")
    print(f"[{case.name}] TX hash match: {compare_result.tx_hash_matches}")
    if case.signature_policy != "ignore":
        print(f"[{case.name}] Signature match: {compare_result.signature_matches}")

    if not compare_result.tx_hash_matches:
        return 2
    if case.signature_policy == "require" and compare_result.signature_matches is not True:
        return 3
    return 0


def case_output_dir(base_out_dir: Path, case: OnchainTestCase) -> Path:
    return base_out_dir / sanitize_name(case.name)
