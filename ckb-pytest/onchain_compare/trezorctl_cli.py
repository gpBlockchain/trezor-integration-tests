from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Callable

from .trezor_json import to_trezorctl_json
from .trezor_models import (
    TrezorAddressResult,
    TrezorCtlRequest,
    TrezorMessageSignResult,
    TrezorMessageVerifyResult,
    TrezorSignResult,
)

COMMAND_ARG_DISPLAY_LIMIT = 512


def command_for_console(command: list[str]) -> str:
    displayed = []
    for arg in command:
        if len(arg) > COMMAND_ARG_DISPLAY_LIMIT:
            hidden = len(arg) - COMMAND_ARG_DISPLAY_LIMIT
            arg = arg[:COMMAND_ARG_DISPLAY_LIMIT] + f"...<truncated {hidden} chars>"
        displayed.append(shlex.quote(arg))
    return " ".join(displayed)


def build_transport_args(transport: str | None) -> list[str]:
    if transport is None:
        return []
    normalized = transport.strip().lower()
    if normalized in {"", "auto"}:
        return []
    return ["-p", transport]


def parse_trezorctl_output(output: str) -> TrezorSignResult:
    signature_match = re.search(r"Signature:\s*(0x[0-9a-fA-F]{130})", output)
    tx_hash_match = re.search(r"TX Hash:\s*(0x[0-9a-fA-F]{64})", output)
    if signature_match is None:
        raise ValueError("trezorctl output did not include a 65-byte Signature")
    if tx_hash_match is None:
        raise ValueError("trezorctl output did not include a 32-byte TX Hash")
    return TrezorSignResult(
        signature=signature_match.group(1).lower(),
        tx_hash=tx_hash_match.group(1).lower(),
    )


def parse_json_or_text_dict(output: str) -> dict[str, Any]:
    text = output.strip()
    if not text:
        raise ValueError("trezorctl output is empty")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        result = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            result[key.strip().lower()] = value.strip()
        if result:
            return result
        raise


def parse_sign_message_output(output: str) -> TrezorMessageSignResult:
    parsed = parse_json_or_text_dict(output)
    try:
        return TrezorMessageSignResult(
            message=parsed["message"],
            address=parsed["address"],
            signature=parsed["signature"].lower(),
        )
    except KeyError as exc:
        raise ValueError(f"trezorctl sign-message output missing field: {exc}") from exc


def parse_verify_message_output(output: str) -> TrezorMessageVerifyResult:
    for line in reversed(output.splitlines()):
        text = line.strip()
        if text in {"True", "true", "1"}:
            return TrezorMessageVerifyResult(valid=True)
        if text in {"False", "false", "0"}:
            return TrezorMessageVerifyResult(valid=False)
    text = output.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("trezorctl verify-message output did not contain a boolean") from exc
    if isinstance(parsed, bool):
        return TrezorMessageVerifyResult(valid=parsed)
    raise ValueError("trezorctl verify-message output did not contain a boolean")


def parse_get_address_output(output: str) -> TrezorAddressResult:
    for line in reversed(output.splitlines()):
        candidate = line.strip()
        if candidate.startswith(("ckb1", "ckt1")):
            return TrezorAddressResult(address=candidate)
    raise ValueError("trezorctl get-address output did not include a CKB address")


def run_trezorctl_command(
    command: list[str],
    work_dir: Path,
    *,
    operation: str,
    metadata: dict[str, Any] | None = None,
    run: Callable[..., Any] = subprocess.run,
) -> str:
    work_dir.mkdir(parents=True, exist_ok=True)
    command_payload = {"operation": operation, "command": command}
    if metadata:
        command_payload.update(metadata)
    (work_dir / "trezorctl.command.json").write_text(
        json.dumps(command_payload, indent=2) + "\n"
    )
    completed = run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=os.environ.copy(),
    )
    (work_dir / "trezorctl.output.txt").write_text(completed.stdout)
    if completed.returncode != 0:
        raise RuntimeError(completed.stdout.strip())
    return completed.stdout


def build_get_address_command(
    *,
    trezorctl: str,
    transport: str,
    coin: str,
    path: str,
    show_display: bool = False,
    chunkify: bool = False,
) -> list[str]:
    command = [
        trezorctl,
        *build_transport_args(transport),
        "ckb",
        "get-address",
        "--coin",
        coin,
        "-n",
        path,
    ]
    if show_display:
        command.append("-d")
    if chunkify:
        command.append("-C")
    return command


def build_sign_message_command(
    *,
    trezorctl: str,
    transport: str,
    coin: str,
    path: str,
    message: str,
    chunkify: bool = False,
) -> list[str]:
    command = [
        trezorctl,
        *build_transport_args(transport),
        "ckb",
        "sign-message",
        "--coin",
        coin,
        "-n",
        path,
    ]
    if chunkify:
        command.append("-C")
    command.append(message)
    return command


def build_verify_message_command(
    *,
    trezorctl: str,
    transport: str,
    coin: str,
    address: str,
    signature: str,
    message: str,
    chunkify: bool = False,
) -> list[str]:
    command = [
        trezorctl,
        *build_transport_args(transport),
        "ckb",
        "verify-message",
        "--coin",
        coin,
    ]
    if chunkify:
        command.append("-C")
    command.extend([address, signature, message])
    return command


def get_address_with_trezorctl(
    *,
    transport: str,
    coin: str,
    path: str,
    work_dir: Path,
    trezorctl: str = "trezorctl",
    show_display: bool = False,
    chunkify: bool = False,
    run: Callable[..., Any] = subprocess.run,
) -> TrezorAddressResult:
    command = build_get_address_command(
        trezorctl=trezorctl,
        transport=transport,
        coin=coin,
        path=path,
        show_display=show_display,
        chunkify=chunkify,
    )
    output = run_trezorctl_command(
        command,
        work_dir,
        operation="get-address",
        metadata={"transport": transport, "coin": coin, "path": path},
        run=run,
    )
    return parse_get_address_output(output)


def sign_message_with_trezorctl(
    *,
    transport: str,
    coin: str,
    path: str,
    message: str,
    work_dir: Path,
    trezorctl: str = "trezorctl",
    chunkify: bool = False,
    run: Callable[..., Any] = subprocess.run,
) -> TrezorMessageSignResult:
    command = build_sign_message_command(
        trezorctl=trezorctl,
        transport=transport,
        coin=coin,
        path=path,
        message=message,
        chunkify=chunkify,
    )
    output = run_trezorctl_command(
        command,
        work_dir,
        operation="sign-message",
        metadata={"transport": transport, "coin": coin, "path": path},
        run=run,
    )
    return parse_sign_message_output(output)


def verify_message_with_trezorctl(
    *,
    transport: str,
    coin: str,
    address: str,
    signature: str,
    message: str,
    work_dir: Path,
    trezorctl: str = "trezorctl",
    chunkify: bool = False,
    run: Callable[..., Any] = subprocess.run,
) -> TrezorMessageVerifyResult:
    command = build_verify_message_command(
        trezorctl=trezorctl,
        transport=transport,
        coin=coin,
        address=address,
        signature=signature,
        message=message,
        chunkify=chunkify,
    )
    output = run_trezorctl_command(
        command,
        work_dir,
        operation="verify-message",
        metadata={"transport": transport, "coin": coin, "address": address},
        run=run,
    )
    return parse_verify_message_output(output)


def build_trezorctl_command(request: TrezorCtlRequest, tx_json_path: Path) -> list[str]:
    command = [
        request.trezorctl,
        *build_transport_args(request.transport),
        "ckb",
        "sign-tx",
        "--coin",
        request.coin,
        "-n",
        request.path,
    ]
    if request.chunkify:
        command.append("-C")
    command.append(str(tx_json_path))
    return command


def sign_with_trezorctl(
    request: TrezorCtlRequest,
    work_dir: Path,
    *,
    run: Callable[..., Any] = subprocess.run,
) -> TrezorSignResult:
    work_dir.mkdir(parents=True, exist_ok=True)
    tx_json_path = work_dir / "trezor.sign_tx.json"
    tx_json_path.write_text(json.dumps(to_trezorctl_json(request.tx), indent=2) + "\n")

    command = build_trezorctl_command(request, tx_json_path)
    print("[trezorctl] command")
    print(command_for_console(command))
    print(f"[trezorctl] command artifact: {work_dir / 'trezorctl.command.json'}")
    output = run_trezorctl_command(
        command,
        work_dir,
        operation="sign-tx",
        metadata={
            "transport": request.transport,
            "coin": request.coin,
            "path": request.path,
            "trezorctl": request.trezorctl,
            "chunkify": request.chunkify,
        },
        run=run,
    )
    return parse_trezorctl_output(output)
