from __future__ import annotations

import os
import shutil
from pathlib import Path


def resolve_trezorctl(configured: str | None, *, project_root: Path) -> str:
    if configured and configured != "auto":
        return configured

    env_match = os.environ.get("TREZORCTL")
    if env_match:
        return env_match

    path_match = shutil.which("trezorctl")
    if path_match is not None:
        return path_match

    for workspace_root in project_root.parents:
        sibling_venv = workspace_root / "trezor-firmware" / ".venv" / "bin" / "trezorctl"
        if sibling_venv.exists():
            return str(sibling_venv)

    raise FileNotFoundError(
        "trezorctl executable was not found. Install trezorctl on PATH, set "
        "TREZORCTL, pass --trezorctl /path/to/trezorctl, or set "
        "'trezorctl' in ckb-pytest/pytest.local.json."
    )
