from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .trezor_json import to_trezorctl_json
from .trezor_models import (
    TrezorAddressResult,
    TrezorMessageSignResult,
    TrezorMessageVerifyResult,
    TrezorSignResult,
    TrezorSignTx,
)
from .trezorctl_cli import (
    build_transport_args,
    build_get_address_command,
    build_sign_message_command,
    build_trezorctl_command,
    build_verify_message_command,
    parse_get_address_output,
    parse_sign_message_output,
    parse_trezorctl_output,
    parse_verify_message_output,
)


@dataclass(frozen=True)
class TrezorCtlCompleted:
    command: list[str]
    returncode: int
    stdout: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class TrezorCtlClient:
    DEBUG_STRING_LIMIT = 256

    def __init__(
        self,
        *,
        transport: str,
        trezorctl: str = "trezorctl",
        artifact_dir: Path,
        run: Callable[..., Any] = subprocess.run,
        debug: bool = False,
        debug_writer: Callable[[str], None] = print,
    ) -> None:
        self.transport = transport
        self.trezorctl = trezorctl
        self.artifact_dir = artifact_dir
        self.run = run
        self.debug = debug
        self.debug_writer = debug_writer

    def _debug_payload(self, value: Any) -> Any:
        if isinstance(value, str) and len(value) > self.DEBUG_STRING_LIMIT:
            return (
                value[: self.DEBUG_STRING_LIMIT]
                + f"... <truncated {len(value) - self.DEBUG_STRING_LIMIT} chars>"
            )
        if isinstance(value, list):
            return [self._debug_payload(item) for item in value]
        if isinstance(value, dict):
            return {key: self._debug_payload(item) for key, item in value.items()}
        return value

    def _run(self, command: list[str], operation: str, metadata: dict[str, Any] | None = None) -> TrezorCtlCompleted:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        payload = {"operation": operation, "command": command}
        if metadata:
            payload.update(metadata)
        (self.artifact_dir / "trezorctl.command.json").write_text(
            json.dumps(payload, indent=2) + "\n"
        )
        if self.debug:
            self.debug_writer(
                "[trezorctl_client] input\n"
                + json.dumps(self._debug_payload(payload), indent=2)
            )
        completed = self.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            env=os.environ.copy(),
        )
        (self.artifact_dir / "trezorctl.output.txt").write_text(completed.stdout)
        if self.debug:
            self.debug_writer(
                "[trezorctl_client] output\n"
                + json.dumps(
                    self._debug_payload(
                        {
                            "returncode": completed.returncode,
                            "stdout": completed.stdout,
                        }
                    ),
                    indent=2,
                )
            )
        return TrezorCtlCompleted(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
        )

    def get_features(self) -> TrezorCtlCompleted:
        return self._run(
            [self.trezorctl, *build_transport_args(self.transport), "get-features"],
            "get-features",
        )

    def run_raw(self, args: list[str], *, operation: str) -> TrezorCtlCompleted:
        return self._run(
            [self.trezorctl, *build_transport_args(self.transport), *args],
            operation,
        )

    def ckb_get_address(
        self,
        *,
        coin: str,
        path: str,
        show_display: bool = False,
        chunkify: bool = False,
    ) -> TrezorAddressResult:
        completed = self._run(
            build_get_address_command(
                trezorctl=self.trezorctl,
                transport=self.transport,
                coin=coin,
                path=path,
                show_display=show_display,
                chunkify=chunkify,
            ),
            "ckb get-address",
            {"coin": coin, "path": path},
        )
        if not completed.ok:
            raise RuntimeError(completed.stdout.strip())
        return parse_get_address_output(completed.stdout)

    def ckb_sign_message(
        self,
        *,
        coin: str,
        path: str,
        message: str,
        chunkify: bool = False,
    ) -> TrezorMessageSignResult:
        completed = self._run(
            build_sign_message_command(
                trezorctl=self.trezorctl,
                transport=self.transport,
                coin=coin,
                path=path,
                message=message,
                chunkify=chunkify,
            ),
            "ckb sign-message",
            {"coin": coin, "path": path},
        )
        if not completed.ok:
            raise RuntimeError(completed.stdout.strip())
        return parse_sign_message_output(completed.stdout)

    def ckb_verify_message(
        self,
        *,
        coin: str,
        address: str,
        signature: str,
        message: str,
        chunkify: bool = False,
    ) -> TrezorMessageVerifyResult:
        completed = self._run(
            build_verify_message_command(
                trezorctl=self.trezorctl,
                transport=self.transport,
                coin=coin,
                address=address,
                signature=signature,
                message=message,
                chunkify=chunkify,
            ),
            "ckb verify-message",
            {"coin": coin, "address": address},
        )
        if not completed.ok:
            raise RuntimeError(completed.stdout.strip())
        return parse_verify_message_output(completed.stdout)

    def ckb_sign_tx(
        self,
        *,
        coin: str,
        path: str,
        tx: TrezorSignTx,
        chunkify: bool = False,
    ) -> TrezorSignResult:
        from .trezor_models import TrezorCtlRequest

        tx_json_path = self.artifact_dir / "trezor.sign_tx.json"
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        tx_json_path.write_text(json.dumps(to_trezorctl_json(tx), indent=2) + "\n")
        request = TrezorCtlRequest(
            transport=self.transport,
            coin=coin,
            path=path,
            tx=tx,
            trezorctl=self.trezorctl,
            chunkify=chunkify,
        )
        completed = self._run(
            build_trezorctl_command(request, tx_json_path),
            "ckb sign-tx",
            {"coin": coin, "path": path},
        )
        if not completed.ok:
            raise RuntimeError(completed.stdout.strip())
        return parse_trezorctl_output(completed.stdout)
