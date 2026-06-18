from __future__ import annotations

from hashlib import blake2b

from .trezor_models import (
    TrezorCellDep,
    TrezorInput,
    TrezorOutput,
    TrezorPrevTx,
    TrezorSignTx,
    TrezorWitness,
    TrezorWitnessArgs,
)


SECP256K1_BLAKE160_CODE_HASH = (
    "9bd7e06f3ecf4be0f2fcd2188b23f1b9fcc88e5d4b65a8637b17723bbda3cce8"
)
MOCK_DAO_WITHDRAW2_SINCE = 0x2000000000000000


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "little")


def _strip_0x(value: str) -> str:
    return value[2:] if value.startswith("0x") else value


def _bytes(value: str | None) -> bytes:
    if not value:
        return b""
    return bytes.fromhex(_strip_0x(value))


def _molecule_bytes(value: bytes) -> bytes:
    return _u32(len(value)) + value


def _ckb_hash(value: bytes) -> bytes:
    return blake2b(value, digest_size=32, person=b"ckb-default-hash").digest()


def _serialize_script(code_hash: str, hash_type: int, args: str) -> bytes:
    code_hash_bytes = _bytes(code_hash)
    args_bytes = _molecule_bytes(_bytes(args))
    offset_code_hash = 16
    offset_hash_type = offset_code_hash + 32
    offset_args = offset_hash_type + 1
    total_size = offset_args + len(args_bytes)
    return (
        _u32(total_size)
        + _u32(offset_code_hash)
        + _u32(offset_hash_type)
        + _u32(offset_args)
        + code_hash_bytes
        + bytes([hash_type])
        + args_bytes
    )


def _serialize_input(value: TrezorInput) -> bytes:
    return _u64(value.since) + _bytes(value.tx_hash) + _u32(value.index)


def _serialize_output(value: TrezorOutput) -> bytes:
    lock = _serialize_script(value.lock_code_hash, value.lock_hash_type, value.lock_args)
    type_script = (
        _serialize_script(
            value.type_code_hash,
            value.type_hash_type or 0,
            value.type_args or "",
        )
        if value.type_code_hash is not None
        else b""
    )
    offset_capacity = 16
    offset_lock = offset_capacity + 8
    offset_type = offset_lock + len(lock)
    total_size = offset_type + len(type_script)
    return (
        _u32(total_size)
        + _u32(offset_capacity)
        + _u32(offset_lock)
        + _u32(offset_type)
        + _u64(value.capacity)
        + lock
        + type_script
    )


def _serialize_cell_dep(value: TrezorCellDep) -> bytes:
    return _bytes(value.tx_hash) + _u32(value.index) + bytes([value.dep_type])


def _serialize_fixvec(items: list[bytes]) -> bytes:
    return _u32(len(items)) + b"".join(items)


def _serialize_dynvec(items: list[bytes]) -> bytes:
    if not items:
        return _u32(4)
    header_size = 4 + len(items) * 4
    offsets = []
    current_offset = header_size
    for item in items:
        offsets.append(current_offset)
        current_offset += len(item)
    return _u32(current_offset) + b"".join(_u32(offset) for offset in offsets) + b"".join(items)


def raw_tx_hash(
    *,
    inputs: list[TrezorInput],
    outputs: list[TrezorOutput],
    cell_deps: list[TrezorCellDep],
    version: int = 0,
    header_deps: list[str] | None = None,
) -> str:
    header_deps = header_deps or []
    version_bytes = _u32(version)
    cell_deps_bytes = _serialize_fixvec([_serialize_cell_dep(item) for item in cell_deps])
    header_deps_bytes = _serialize_fixvec([_bytes(item) for item in header_deps])
    inputs_bytes = _serialize_fixvec([_serialize_input(item) for item in inputs])
    outputs_bytes = _serialize_dynvec([_serialize_output(item) for item in outputs])
    outputs_data_bytes = _serialize_dynvec(
        [_molecule_bytes(_bytes(item.data)) for item in outputs]
    )

    offset_version = 4 + 6 * 4
    offset_cell_deps = offset_version + 4
    offset_header_deps = offset_cell_deps + len(cell_deps_bytes)
    offset_inputs = offset_header_deps + len(header_deps_bytes)
    offset_outputs = offset_inputs + len(inputs_bytes)
    offset_outputs_data = offset_outputs + len(outputs_bytes)
    total_size = offset_outputs_data + len(outputs_data_bytes)
    raw_tx = (
        _u32(total_size)
        + _u32(offset_version)
        + _u32(offset_cell_deps)
        + _u32(offset_header_deps)
        + _u32(offset_inputs)
        + _u32(offset_outputs)
        + _u32(offset_outputs_data)
        + version_bytes
        + cell_deps_bytes
        + header_deps_bytes
        + inputs_bytes
        + outputs_bytes
        + outputs_data_bytes
    )
    return _ckb_hash(raw_tx).hex()


def synthetic_prev_tx_for_outputs(
    outputs: list[TrezorOutput],
    *,
    inputs: list[TrezorInput] | None = None,
    cell_deps: list[TrezorCellDep] | None = None,
    version: int = 0,
    header_deps: list[str] | None = None,
) -> tuple[str, TrezorPrevTx]:
    inputs = inputs or []
    cell_deps = cell_deps or []
    header_deps = header_deps or []
    tx_hash = raw_tx_hash(
        inputs=inputs,
        outputs=outputs,
        cell_deps=cell_deps,
        version=version,
        header_deps=header_deps,
    )
    return (
        tx_hash,
        TrezorPrevTx(
            version=version,
            inputs=inputs,
            outputs=outputs,
            cell_deps=cell_deps,
            header_deps=header_deps,
        ),
    )


def mock_dao_withdraw2_sign_tx(
    *,
    network: str,
    path: str,
    lock_args: str,
    input_capacity: int = 100_000_000_000,
    output_capacity: int = 100_100_000_000,
) -> TrezorSignTx:
    """Build a local-only DAO withdraw2-shaped tx where DAO compensation makes out > in."""
    previous_output = TrezorOutput(
        capacity=input_capacity,
        lock_code_hash=SECP256K1_BLAKE160_CODE_HASH,
        lock_hash_type=1,
        lock_args=lock_args,
    )
    previous_tx_hash, previous_tx = synthetic_prev_tx_for_outputs([previous_output])
    output = TrezorOutput(
        capacity=output_capacity,
        lock_code_hash=SECP256K1_BLAKE160_CODE_HASH,
        lock_hash_type=1,
        lock_args=lock_args,
    )
    return TrezorSignTx(
        network=network,
        path=path,
        inputs=[
            TrezorInput(
                tx_hash=previous_tx_hash,
                index=0,
                since=MOCK_DAO_WITHDRAW2_SINCE,
            )
        ],
        outputs=[output],
        cell_deps=[],
        fee=0,
        witnesses=[TrezorWitness(witness_args=TrezorWitnessArgs())],
        sign_group_input_indices=[0],
        prev_txs={previous_tx_hash: previous_tx},
    )
