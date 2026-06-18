from __future__ import annotations

import json
import urllib.request
from typing import Any

from .common import ensure_0x
from .rpc_models import RpcOutput, RpcTransaction


def rpc_call(rpc_url: str, method: str, params: list[Any]) -> Any:
    payload = json.dumps({"id": 1, "jsonrpc": "2.0", "method": method, "params": params})
    request = urllib.request.Request(
        rpc_url,
        data=payload.encode(),
        headers={
            "content-type": "application/json",
            "user-agent": "trezor-ckb-pytest/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode())
    if "error" in body:
        raise RuntimeError(body["error"])
    return body["result"]


def fetch_transaction(rpc_url: str, tx_hash: str) -> dict[str, Any]:
    result = rpc_call(rpc_url, "get_transaction", [ensure_0x(tx_hash)])
    if result is None:
        raise RuntimeError(f"transaction not found: {tx_hash}")
    return result


def resolve_previous_transactions(
    rpc_url: str, rpc_tx: RpcTransaction
) -> dict[str, RpcTransaction]:
    cache: dict[str, RpcTransaction] = {}
    for tx_hash, index in rpc_tx.input_out_points():
        if tx_hash not in cache:
            response = fetch_transaction(rpc_url, tx_hash)
            cache[tx_hash] = RpcTransaction.from_json(response["transaction"])
        if index >= len(cache[tx_hash].outputs):
            raise RuntimeError(f"previous output index out of range: {tx_hash}:{index}")
    return cache


def resolve_previous_outputs_from_transactions(
    rpc_tx: RpcTransaction, previous_transactions: dict[str, RpcTransaction]
) -> list[RpcOutput]:
    previous_outputs = []
    for tx_hash, index in rpc_tx.input_out_points():
        previous_tx = previous_transactions[tx_hash]
        previous_outputs.append(previous_tx.outputs[index])
    return previous_outputs


def resolve_previous_outputs(rpc_url: str, rpc_tx: RpcTransaction) -> list[RpcOutput]:
    previous_transactions = resolve_previous_transactions(rpc_url, rpc_tx)
    return resolve_previous_outputs_from_transactions(rpc_tx, previous_transactions)
