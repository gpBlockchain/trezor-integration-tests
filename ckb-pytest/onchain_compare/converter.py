from __future__ import annotations

from .common import hex_int, strip_0x
from .constants import DEP_TYPE_TO_INT, HASH_TYPE_TO_INT
from .rpc_models import RpcOutput, RpcTransaction
from .trezor_models import (
    TrezorCellDep,
    TrezorInput,
    TrezorOutput,
    TrezorPrevTx,
    TrezorSignTx,
    TrezorWitness,
    TrezorWitnessArgs,
)


def compute_fee_shannons(
    rpc_tx: RpcTransaction, previous_outputs: list[RpcOutput]
) -> int:
    input_capacity = sum(output.capacity for output in previous_outputs)
    output_capacity = sum(output.capacity for output in rpc_tx.outputs)
    fee = input_capacity - output_capacity
    if fee < 0:
        raise ValueError("transaction outputs exceed resolved input capacity")
    return fee


def validate_version_and_headers(rpc_tx: RpcTransaction) -> None:
    if rpc_tx.version != "0x0":
        raise ValueError("current Trezor CKB signer only supports transaction version 0")


def rpc_output_to_trezor(output: RpcOutput) -> TrezorOutput:
    converted = TrezorOutput(
        capacity=output.capacity,
        lock_code_hash=strip_0x(output.lock.code_hash),
        lock_hash_type=HASH_TYPE_TO_INT[output.lock.hash_type],
        lock_args=strip_0x(output.lock.args),
        type_code_hash=strip_0x(output.type.code_hash) if output.type else None,
        type_hash_type=HASH_TYPE_TO_INT[output.type.hash_type] if output.type else None,
        type_args=strip_0x(output.type.args) if output.type else None,
        data=output.data if output.data != "0x" else None,
    )
    return converted


def rpc_input_to_trezor(value) -> TrezorInput:
    return TrezorInput(
        tx_hash=strip_0x(value.tx_hash),
        index=value.index,
        since=value.since,
    )


def rpc_cell_dep_to_trezor(value) -> TrezorCellDep:
    return TrezorCellDep(
        tx_hash=strip_0x(value.tx_hash),
        index=value.index,
        dep_type=DEP_TYPE_TO_INT[value.dep_type],
    )


def rpc_prev_tx_to_trezor(value: RpcTransaction) -> TrezorPrevTx:
    return TrezorPrevTx(
        version=hex_int(value.version),
        header_deps=[strip_0x(item) for item in value.header_deps],
        inputs=[rpc_input_to_trezor(item) for item in value.inputs],
        outputs=[rpc_output_to_trezor(item) for item in value.outputs],
        cell_deps=[rpc_cell_dep_to_trezor(item) for item in value.cell_deps],
    )


def _read_u32_le(raw: bytes, offset: int) -> int:
    return int.from_bytes(raw[offset : offset + 4], "little")


def _parse_molecule_bytes(value: bytes) -> bytes:
    if len(value) < 4:
        raise ValueError("invalid Molecule Bytes field")
    size = _read_u32_le(value, 0)
    data = value[4:]
    if len(data) != size:
        raise ValueError("Molecule Bytes length mismatch")
    return data


def parse_witness_args_for_signing(witness_hex: str) -> TrezorWitnessArgs:
    raw = bytes.fromhex(strip_0x(witness_hex))
    if not raw:
        return TrezorWitnessArgs(lock_size=65)
    if len(raw) < 16:
        raise ValueError("signing witness is not a valid WitnessArgs table")

    total_size = _read_u32_le(raw, 0)
    offsets = [_read_u32_le(raw, offset) for offset in (4, 8, 12)]
    if total_size != len(raw):
        raise ValueError("WitnessArgs total size mismatch")
    if offsets != sorted(offsets) or offsets[0] < 16 or offsets[-1] > len(raw):
        raise ValueError("invalid WitnessArgs offsets")

    lock = _parse_molecule_bytes(raw[offsets[0] : offsets[1]])
    input_type = (
        _parse_molecule_bytes(raw[offsets[1] : offsets[2]])
        if offsets[1] != offsets[2]
        else None
    )
    output_type = (
        _parse_molecule_bytes(raw[offsets[2] : total_size])
        if offsets[2] != total_size
        else None
    )
    return TrezorWitnessArgs(
        lock_size=len(lock),
        input_type=f"0x{input_type.hex()}" if input_type is not None else None,
        output_type=f"0x{output_type.hex()}" if output_type is not None else None,
    )


def rpc_witnesses_to_trezor(
    rpc_tx: RpcTransaction, sign_group_input_indices: list[int]
) -> list[TrezorWitness]:
    if not sign_group_input_indices:
        raise ValueError("signing group must contain at least one input")
    first_signing_index = sign_group_input_indices[0]
    witnesses = []
    for index, witness in enumerate(rpc_tx.witnesses):
        if index == first_signing_index:
            witnesses.append(
                TrezorWitness(witness_args=parse_witness_args_for_signing(witness))
            )
        else:
            witnesses.append(TrezorWitness(raw=witness))
    if first_signing_index >= len(witnesses):
        raise ValueError("signing witness is missing from transaction witness vector")
    return witnesses


def rpc_transaction_to_trezor_sign_tx(
    rpc_tx: RpcTransaction,
    *,
    previous_outputs: list[RpcOutput],
    previous_transactions: dict[str, RpcTransaction] | None = None,
    sign_group_input_indices: list[int] | None = None,
    network: str,
    path: str,
) -> TrezorSignTx:
    validate_version_and_headers(rpc_tx)
    if previous_transactions is None:
        previous_transactions = {}
    fee = compute_fee_shannons(rpc_tx, previous_outputs)
    if sign_group_input_indices is None:
        sign_group_input_indices = list(range(len(rpc_tx.inputs)))
    return TrezorSignTx(
        network=network,
        path=path,
        inputs=[rpc_input_to_trezor(inp) for inp in rpc_tx.inputs],
        outputs=[rpc_output_to_trezor(output) for output in rpc_tx.outputs],
        cell_deps=[rpc_cell_dep_to_trezor(dep) for dep in rpc_tx.cell_deps],
        fee=fee,
        header_deps=[strip_0x(item) for item in rpc_tx.header_deps],
        witnesses=rpc_witnesses_to_trezor(rpc_tx, sign_group_input_indices),
        sign_group_input_indices=sign_group_input_indices,
        prev_txs={
            strip_0x(tx_hash): rpc_prev_tx_to_trezor(prev_tx)
            for tx_hash, prev_tx in previous_transactions.items()
        },
    )


def lock_matches_expected(output: RpcOutput, expected_lock: dict[str, str]) -> bool:
    lock = output.lock
    return (
        lock.code_hash.lower() == expected_lock["code_hash"].lower()
        and lock.hash_type == expected_lock["hash_type"]
        and lock.args.lower() == expected_lock["args"].lower()
    )


def resolve_signing_group(
    previous_outputs: list[RpcOutput], expected_lock: dict[str, str]
) -> list[int]:
    if not previous_outputs:
        raise ValueError("transaction has no inputs")

    indexes = []
    for index, output in enumerate(previous_outputs):
        if lock_matches_expected(output, expected_lock):
            indexes.append(index)
    if not indexes:
        raise ValueError(
            "unsupported transaction for current Trezor signer: "
            "transaction does not contain target address lock"
        )
    return indexes


def validate_all_inputs_match_lock(
    previous_outputs: list[RpcOutput], expected_lock: dict[str, str]
) -> None:
    mismatches = []
    for index, output in enumerate(previous_outputs):
        lock = output.lock
        if (
            lock.code_hash.lower() != expected_lock["code_hash"].lower()
            or lock.hash_type != expected_lock["hash_type"]
            or lock.args.lower() != expected_lock["args"].lower()
        ):
            mismatches.append(index)
    if mismatches:
        joined = ", ".join(str(i) for i in mismatches)
        raise ValueError(
            "unsupported transaction for this first-pass framework: "
            f"input indexes [{joined}] do not belong to the target address lock"
        )
