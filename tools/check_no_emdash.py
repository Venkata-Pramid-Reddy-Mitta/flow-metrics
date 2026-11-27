#!/usr/bin/env python
"""Fail the build if an em dash, en dash or figure dash reached a text file.

House rule for this repository: no em dashes anywhere in prose or code. They are
the single most reliable tell of machine-written text, so banning them (and the
en and figure dashes that get substituted for them) is cheap insurance that the
documents read as a person's. This runs as part of ``make lint`` so drift over a
long editing session is caught the same minute it happens.

Exit 0 clean, exit 1 with a file:line list on any hit.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Defined by codepoint, not literal, so this guard file contains none of the
# glyphs it bans and therefore does not flag itself.
BANNED = {
    chr(0x2014): "em dash",
    chr(0x2013): "en dash",
    chr(0x2012): "figure dash",
    chr(0x2015): "horizontal bar",
}

TEXT_SUFFIXES = {
    ".py", ".md", ".toml", ".cfg", ".txt", ".yml", ".yaml", ".ini", ".json",
}
# SVGs are machine rendered from a source fence and may legitimately carry glyphs
# from label text, so they are checked for banned dashes too but listed here for
# clarity. Everything generated under docs/report is git-ignored and skipped.
EXTRA_FILES = {"Makefile"}

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "htmlcov"}


def _iter_text_files() -> list[Path]:
    out: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in EXTRA_FILES:
            out.append(path)
    return sorted(out)


def scan() -> list[str]:
    hits: list[str] = []
    for path in _iter_text_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for glyph, name in BANNED.items():
                col = line.find(glyph)
                if col != -1:
                    rel = path.relative_to(REPO_ROOT)
                    hits.append(f"{rel}:{lineno}:{col + 1}: {name} (U+{ord(glyph):04X})")
    return hits


def main() -> int:
    hits = scan()
    if hits:
        print("Banned dash glyphs found:")
        for h in hits:
            print(f"  {h}")
        return 1
    print("no banned dashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
