from __future__ import annotations

from .common import strip_0x
from .trezor_models import (
    TrezorCellDep,
    TrezorInput,
    TrezorOutput,
    TrezorPrevTx,
    TrezorSignTx,
    TrezorWitness,
)


def input_to_json(value: TrezorInput) -> dict:
    return {
        "tx_hash": value.tx_hash,
        "index": value.index,
        "since": value.since,
    }


def output_to_json(value: TrezorOutput) -> dict:
    result = {
        "capacity": value.capacity,
        "lock_code_hash": value.lock_code_hash,
        "lock_hash_type": value.lock_hash_type,
        "lock_args": value.lock_args,
    }
    if value.type_code_hash is not None:
        result["type_code_hash"] = value.type_code_hash
        result["type_hash_type"] = value.type_hash_type
        result["type_args"] = value.type_args
    if value.data is not None:
        result["data"] = value.data
    return result


def cell_dep_to_json(value: TrezorCellDep) -> dict:
    return {
        "tx_hash": value.tx_hash,
        "index": value.index,
        "dep_type": value.dep_type,
    }


def witness_to_json(value: TrezorWitness) -> dict:
    if value.witness_args is not None:
        result = {"lock_size": value.witness_args.lock_size}
        if value.witness_args.input_type is not None:
            result["input_type"] = value.witness_args.input_type
        if value.witness_args.output_type is not None:
            result["output_type"] = value.witness_args.output_type
        return {"witness_args": result}
    return {"raw": value.raw or "0x"}


def prev_tx_to_json(value: TrezorPrevTx) -> dict:
    return {
        "version": value.version,
        "header_deps": [strip_0x(item) for item in value.header_deps],
        "inputs": [input_to_json(item) for item in value.inputs],
        "outputs": [output_to_json(item) for item in value.outputs],
        "cell_deps": [cell_dep_to_json(item) for item in value.cell_deps],
    }


def to_trezorctl_json(tx: TrezorSignTx) -> dict:
    return {
        "inputs": [input_to_json(value) for value in tx.inputs],
        "outputs": [output_to_json(value) for value in tx.outputs],
        "cell_deps": [cell_dep_to_json(value) for value in tx.cell_deps],
        "header_deps": [strip_0x(value) for value in tx.header_deps],
        "witnesses": [witness_to_json(value) for value in tx.witnesses],
        "sign_group_input_indices": tx.sign_group_input_indices,
        "prev_txs": {
            tx_hash: prev_tx_to_json(value) for tx_hash, value in tx.prev_txs.items()
        },
    }
