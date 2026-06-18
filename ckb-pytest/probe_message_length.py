from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from onchain_compare.constants import DEFAULT_PATH, DEFAULT_TESTNET_ADDRESS
from onchain_compare.trezorctl_cli import build_transport_args
from onchain_compare.trezorctl_locator import resolve_trezorctl


ProbeMode = Literal["sign", "verify"]
ProbeStatus = Literal["within_limit", "limit_error", "cancelled", "unknown_error"]

DEFAULT_SIGNATURE = "0x" + "11" * 65
LIMIT_ERROR_PATTERNS = (
    "Encoded message is too long",
    "NoiseInvalidMessage",
    "Data must be bytes and less or equal",
)
CANCEL_PATTERNS = (
    "Cancelled",
    "Action cancelled",
    "FailureType.ActionCancelled",
)


@dataclass(frozen=True)
class ProbeResult:
    mode: ProbeMode
    length: int
    returncode: int
    stdout: str
    status: ProbeStatus


@dataclass(frozen=True)
class BoundaryResult:
    mode: ProbeMode
    max_ok: int
    first_error: int
    probes: list[ProbeResult]


def classify_probe_output(returncode: int, stdout: str) -> ProbeStatus:
    if any(pattern in stdout for pattern in LIMIT_ERROR_PATTERNS):
        return "limit_error"
    if any(pattern in stdout for pattern in CANCEL_PATTERNS):
        return "cancelled"
    if returncode == 0:
        return "within_limit"
    return "unknown_error"


def build_probe_command(
    *,
    mode: ProbeMode,
    trezorctl: str,
    transport: str,
    coin: str,
    path: str,
    length: int,
    address: str,
    signature: str,
) -> list[str]:
    message = "a" * length
    command = [trezorctl, *build_transport_args(transport), "ckb"]
    if mode == "sign":
        command.extend(["sign-message", "--coin", coin, "-n", path, message])
    else:
        command.extend(["verify-message", "--coin", coin, address, signature, message])
    return command


def run_probe(
    *,
    mode: ProbeMode,
    trezorctl: str,
    transport: str,
    coin: str,
    path: str,
    length: int,
    address: str,
    signature: str,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> ProbeResult:
    command = build_probe_command(
        mode=mode,
        trezorctl=trezorctl,
        transport=transport,
        coin=coin,
        path=path,
        length=length,
        address=address,
        signature=signature,
    )
    completed = run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return ProbeResult(
        mode=mode,
        length=length,
        returncode=completed.returncode,
        stdout=completed.stdout,
        status=classify_probe_output(completed.returncode, completed.stdout),
    )


def find_boundary(
    *,
    mode: ProbeMode,
    low: int,
    high: int,
    probe: Callable[[int], ProbeResult],
    check_low: bool = False,
) -> BoundaryResult:
    if low < 0 or high <= low:
        raise ValueError("expected 0 <= low < high")

    probes: list[ProbeResult] = []

    if check_low:
        low_result = probe(low)
        probes.append(low_result)
        if low_result.status != "within_limit":
            raise RuntimeError(
                f"low={low} must be within_limit, got {low_result.status}: {low_result.stdout.strip()}"
            )

    high_result = probe(high)
    probes.append(high_result)
    if high_result.status != "limit_error":
        raise RuntimeError(
            f"high={high} must be limit_error, got {high_result.status}: {high_result.stdout.strip()}"
        )

    ok = low
    err = high
    while ok + 1 < err:
        mid = (ok + err) // 2
        result = probe(mid)
        probes.append(result)
        if result.status == "within_limit":
            ok = mid
        elif result.status == "limit_error":
            err = mid
        elif result.status == "cancelled":
            raise RuntimeError(f"probe length={mid} was cancelled on device")
        else:
            raise RuntimeError(
                f"probe length={mid} returned unknown_error: {result.stdout.strip()}"
            )

    return BoundaryResult(mode=mode, max_ok=ok, first_error=err, probes=probes)


def print_probe_result(result: ProbeResult, *, show_output: bool) -> None:
    print(
        f"[{result.mode}] length={result.length} "
        f"returncode={result.returncode} status={result.status}"
    )
    if show_output and result.stdout.strip():
        print(result.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Probe CKB sign-message / verify-message length boundaries with trezorctl."
    )
    parser.add_argument("length", nargs="?", type=int, help="single probe length")
    parser.add_argument("--mode", choices=["sign", "verify"], default="sign")
    parser.add_argument("--search", action="store_true", help="binary search boundary")
    parser.add_argument("--low", type=int, default=65000, help="known-good lower bound")
    parser.add_argument("--high", type=int, default=65536, help="known-bad upper bound")
    parser.add_argument("--check-low", action="store_true", help="probe low before search")
    parser.add_argument("--transport", default="auto")
    parser.add_argument("--trezorctl", default="auto")
    parser.add_argument("--coin", default="Testnet", choices=["Mainnet", "Testnet"])
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--address", default=DEFAULT_TESTNET_ADDRESS)
    parser.add_argument("--signature", default=DEFAULT_SIGNATURE)
    parser.add_argument("--show-output", action="store_true")
    args = parser.parse_args()

    trezorctl = resolve_trezorctl(args.trezorctl, project_root=Path(__file__).resolve().parent)

    def probe(length: int) -> ProbeResult:
        result = run_probe(
            mode=args.mode,
            trezorctl=trezorctl,
            transport=args.transport,
            coin=args.coin,
            path=args.path,
            length=length,
            address=args.address,
            signature=args.signature,
        )
        print_probe_result(result, show_output=args.show_output)
        return result

    if args.search:
        boundary = find_boundary(
            mode=args.mode,
            low=args.low,
            high=args.high,
            probe=probe,
            check_low=args.check_low,
        )
        print(
            f"\n{boundary.mode} boundary: "
            f"max_ok={boundary.max_ok}, first_error={boundary.first_error}, "
            f"probes={len(boundary.probes)}"
        )
        return 0

    if args.length is None:
        parser.error("length is required unless --search is used")

    result = probe(args.length)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
