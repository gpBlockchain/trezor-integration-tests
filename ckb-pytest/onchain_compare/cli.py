from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, replace
from pathlib import Path

from .case_file import OnchainTestCase, load_case_file
from .common import ensure_0x, strip_0x
from .constants import DEFAULT_PATH, DEFAULT_TESTNET_ADDRESS
from .runner import case_output_dir, default_run_dir, run_onchain_case
from .trezorctl_cli import (
    get_address_with_trezorctl,
    sign_message_with_trezorctl,
    verify_message_with_trezorctl,
)
from .trezorctl_locator import resolve_trezorctl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch an on-chain CKB transaction and compare Trezor signing."
    )
    parser.add_argument("--case-file", type=Path, default=None)
    parser.add_argument("--case-name", action="append", default=None)
    parser.add_argument("--network", choices=["Mainnet", "Testnet"], default="Testnet")
    parser.add_argument("--rpc-url", default=None)
    parser.add_argument("--tx-hash", default=None)
    parser.add_argument("--address", default=DEFAULT_TESTNET_ADDRESS)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--transport", default="auto")
    parser.add_argument("--trezorctl", default="auto")
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument("--no-sign", action="store_true")
    parser.add_argument(
        "--trezorctl-action",
        choices=["get-address", "sign-message", "verify-message"],
        default=None,
        help="Run a direct CKB trezorctl command instead of on-chain compare.",
    )
    parser.add_argument("--message", default=None)
    parser.add_argument("--signature", default=None)
    parser.add_argument("--verify-address", default=None)
    parser.add_argument("--show-display", action="store_true")
    parser.add_argument("--chunkify", action="store_true")
    parser.add_argument(
        "--signature-policy",
        choices=["ignore", "compare", "require"],
        default="compare",
        help="compare reports signature match; require also fails when absent/mismatched.",
    )
    return parser.parse_args()


def default_trezorctl_action_dir(action: str) -> Path:
    return Path("runs") / f"trezorctl-{action}"


def run_direct_trezorctl_action(args: argparse.Namespace) -> int:
    if args.trezorctl_action is None:
        raise ValueError("trezorctl action is required")
    out_dir = args.out_dir or default_trezorctl_action_dir(args.trezorctl_action)

    if args.trezorctl_action == "get-address":
        result = get_address_with_trezorctl(
            transport=args.transport,
            coin=args.network,
            path=args.path,
            work_dir=out_dir,
            trezorctl=args.trezorctl,
            show_display=args.show_display,
            chunkify=args.chunkify,
        )
    elif args.trezorctl_action == "sign-message":
        if args.message is None:
            raise ValueError("--message is required for sign-message")
        result = sign_message_with_trezorctl(
            transport=args.transport,
            coin=args.network,
            path=args.path,
            message=args.message,
            work_dir=out_dir,
            trezorctl=args.trezorctl,
            chunkify=args.chunkify,
        )
    else:
        if args.verify_address is None:
            raise ValueError("--verify-address is required for verify-message")
        if args.signature is None:
            raise ValueError("--signature is required for verify-message")
        if args.message is None:
            raise ValueError("--message is required for verify-message")
        result = verify_message_with_trezorctl(
            transport=args.transport,
            coin=args.network,
            address=args.verify_address,
            signature=args.signature,
            message=args.message,
            work_dir=out_dir,
            trezorctl=args.trezorctl,
            chunkify=args.chunkify,
        )

    result_json = asdict(result)
    (out_dir / "trezorctl.result.json").write_text(
        json.dumps(result_json, indent=2) + "\n"
    )
    print(json.dumps(result_json, indent=2))
    print(f"Wrote artifacts: {out_dir}")
    return 0


def main() -> int:
    args = parse_args()
    if args.trezorctl_action is not None or not args.no_sign:
        args.trezorctl = resolve_trezorctl(
            args.trezorctl,
            project_root=Path(__file__).resolve().parents[1],
        )
    if args.trezorctl_action is not None:
        return run_direct_trezorctl_action(args)

    if args.case_file is not None:
        cases = load_case_file(args.case_file, selected_names=args.case_name)
        base_out_dir = args.out_dir or Path("runs")
        exit_code = 0
        for case in cases:
            if args.chunkify:
                case = replace(case, chunkify=True)
            try:
                case_exit_code = run_onchain_case(
                    case,
                    no_sign=args.no_sign,
                    out_dir=case_output_dir(base_out_dir, case),
                )
            except Exception as exc:
                print(f"[{case.name}] error: {exc}", file=sys.stderr)
                case_exit_code = 1
            exit_code = max(exit_code, case_exit_code)
        return exit_code

    if args.tx_hash is None:
        raise ValueError("either --tx-hash or --case-file is required")

    case = OnchainTestCase(
        name=strip_0x(args.tx_hash)[:16],
        network=args.network,
        tx_hash=ensure_0x(args.tx_hash),
        address=args.address,
        path=args.path,
        rpc_url=args.rpc_url,
        transport=args.transport,
        trezorctl=args.trezorctl,
        signature_policy=args.signature_policy,
        chunkify=args.chunkify,
    )
    out_dir = args.out_dir or default_run_dir(args.tx_hash)
    return run_onchain_case(case, no_sign=args.no_sign, out_dir=out_dir)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
