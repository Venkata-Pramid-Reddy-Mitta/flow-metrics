"""Shared helpers for the experiment scripts.

Kept tiny and in one place so every experiment reads the same fixtures through the
same analysis path. An experiment that rolled its own analysis could publish a
number the rest of the tool does not agree with.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

OUT_DIR = ROOT / "docs" / "experiments"


def write_result(name: str, payload: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def print_table(title: str, rows: list[tuple]) -> None:
    print(title)
    for label, value in rows:
        print(f"  {label:<42} {value}")
