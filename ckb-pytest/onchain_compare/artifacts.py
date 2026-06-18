from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import sanitize_name


class ArtifactStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def case_dir(self, nodeid: str) -> Path:
        path = self.base_dir / sanitize_name(nodeid.replace("::", "-"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_json(self, case_dir: Path, filename: str, payload: Any) -> Path:
        path = case_dir / filename
        path.write_text(json.dumps(payload, indent=2) + "\n")
        return path

    def write_text(self, case_dir: Path, filename: str, text: str) -> Path:
        path = case_dir / filename
        path.write_text(text)
        return path
