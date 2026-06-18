from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import hex_int, strip_0x


@dataclass(frozen=True)
class RpcScript:
    code_hash: str
    hash_type: str
    args: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RpcScript":
        return cls(
            code_hash=data["code_hash"],
            hash_type=data["hash_type"],
            args=data["args"],
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "code_hash": self.code_hash,
            "hash_type": self.hash_type,
            "args": self.args,
        }


@dataclass(frozen=True)
class RpcInput:
    tx_hash: str
    index: int
    since: int

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RpcInput":
        previous_output = data["previous_output"]
        return cls(
            tx_hash=previous_output["tx_hash"],
            index=hex_int(previous_output["index"]),
            since=hex_int(data.get("since", "0x0")),
        )


@dataclass(frozen=True)
class RpcOutput:
    capacity: int
    lock: RpcScript
    type: RpcScript | None
    data: str = "0x"

    @classmethod
    def from_json(cls, data: dict[str, Any], output_data: str = "0x") -> "RpcOutput":
        type_script = data.get("type")
        return cls(
            capacity=hex_int(data["capacity"]),
            lock=RpcScript.from_json(data["lock"]),
            type=RpcScript.from_json(type_script) if type_script is not None else None,
            data=output_data,
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "capacity": hex(self.capacity),
            "lock": self.lock.to_json(),
            "type": self.type.to_json() if self.type is not None else None,
        }


@dataclass(frozen=True)
class RpcCellDep:
    tx_hash: str
    index: int
    dep_type: str

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RpcCellDep":
        out_point = data["out_point"]
        return cls(
            tx_hash=out_point["tx_hash"],
            index=hex_int(out_point["index"]),
            dep_type=data["dep_type"],
        )


@dataclass(frozen=True)
class RpcTransaction:
    hash: str
    version: str
    cell_deps: list[RpcCellDep]
    header_deps: list[str]
    inputs: list[RpcInput]
    outputs: list[RpcOutput]
    witnesses: list[str]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RpcTransaction":
        outputs_data = data.get("outputs_data", [])
        outputs = data["outputs"]
        if len(outputs_data) != len(outputs):
            raise ValueError("outputs_data length must match outputs length")
        return cls(
            hash=data.get("hash", ""),
            version=data.get("version", "0x0"),
            cell_deps=[RpcCellDep.from_json(dep) for dep in data.get("cell_deps", [])],
            header_deps=list(data.get("header_deps", [])),
            inputs=[RpcInput.from_json(inp) for inp in data.get("inputs", [])],
            outputs=[
                RpcOutput.from_json(output, output_data=outputs_data[index])
                for index, output in enumerate(outputs)
            ],
            witnesses=list(data.get("witnesses", [])),
        )

    @staticmethod
    def output_from_json(data: dict[str, Any]) -> RpcOutput:
        return RpcOutput.from_json(data, output_data=data.get("output_data", "0x"))

    def input_out_points(self) -> list[tuple[str, int]]:
        return [(inp.tx_hash, inp.index) for inp in self.inputs]


def rpc_tx_hash_for_trezor(value: str) -> str:
    return strip_0x(value)

