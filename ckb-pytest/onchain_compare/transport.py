from __future__ import annotations

import re
import subprocess


def parse_trezorctl_list_transport(output: str) -> str | None:
    for line in output.splitlines():
        match = re.match(r"^(\S+)\s+-\s+", line.strip())
        if match:
            return match.group(1)
    return None


def resolve_transport(configured: str, *, trezorctl: str) -> str:
    if configured.strip().lower() not in {"", "auto"}:
        return configured

    completed = subprocess.run(
        [trezorctl, "list"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    transport = parse_trezorctl_list_transport(completed.stdout)
    return transport or configured
