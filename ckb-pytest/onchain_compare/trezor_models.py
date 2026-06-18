from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TrezorInput:
    tx_hash: str
    index: int
    since: int = 0


@dataclass(frozen=True)
class TrezorOutput:
    capacity: int
    lock_code_hash: str
    lock_hash_type: int
    lock_args: str
    type_code_hash: str | None = None
    type_hash_type: int | None = None
    type_args: str | None = None
    data: str | None = None


@dataclass(frozen=True)
class TrezorCellDep:
    tx_hash: str
    index: int
    dep_type: int


@dataclass(frozen=True)
class TrezorWitnessArgs:
    lock_size: int = 65
    input_type: str | None = None
    output_type: str | None = None


@dataclass(frozen=True)
class TrezorWitness:
    witness_args: TrezorWitnessArgs | None = None
    raw: str | None = None


@dataclass(frozen=True)
class TrezorPrevTx:
    version: int
    inputs: list[TrezorInput]
    outputs: list[TrezorOutput]
    cell_deps: list[TrezorCellDep]
    header_deps: list[str]


@dataclass(frozen=True)
class TrezorSignTx:
    network: str
    path: str
    inputs: list[TrezorInput]
    outputs: list[TrezorOutput]
    cell_deps: list[TrezorCellDep]
    fee: int
    header_deps: list[str] = field(default_factory=list)
    witnesses: list[TrezorWitness] = field(default_factory=list)
    sign_group_input_indices: list[int] = field(default_factory=list)
    prev_txs: dict[str, TrezorPrevTx] = field(default_factory=dict)


@dataclass(frozen=True)
class TrezorSignResult:
    signature: str
    tx_hash: str


@dataclass(frozen=True)
class TrezorAddressResult:
    address: str


@dataclass(frozen=True)
class TrezorMessageSignResult:
    message: str
    address: str
    signature: str


@dataclass(frozen=True)
class TrezorMessageVerifyResult:
    valid: bool


@dataclass(frozen=True)
class TrezorCtlRequest:
    transport: str
    coin: str
    path: str
    tx: TrezorSignTx
    trezorctl: str = "trezorctl"
    chunkify: bool = False


@dataclass(frozen=True)
class CompareResult:
    tx_hash_matches: bool
    signature_matches: bool | None
    trezor_tx_hash: str
    chain_tx_hash: str
    trezor_signature: str
    chain_signature: str | None
