"""Record a replay of the CLI, not a screen recording.

Every line of terminal text in the output is real captured stdout from running the
command, never hand written, and each segment is held for a time derived from the
command's measured wall clock so a slow command looks slow. The segments are
ordered as the argument the project makes: the baseline that stays quiet first,
then the headline lead, then the uncomfortable survivorship number, then the
boundary, then the receipts that guard it all.

A manifest records every command with its exit code and duration, so the replay is
auditable. The import is warmed once before timing so the first segment does not
pay for it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "video"
ENV_PYTHONPATH = str(ROOT / "src")

# (label shown as a comment, argv). Ordered as the argument, not the feature list.
SEGMENTS = [
    ("baseline: a steady board, no false alarm", ["-m", "flowmetrics.cli", "check",
                                                  "--generate", "steady"]),
    ("the headline: WIP leads the average by 8 weeks", ["-m", "flowmetrics.cli", "check"]),
    ("the uncomfortable number: the average understated by 68%",
     ["experiments/exp_survivorship.py"]),
    ("the boundary: a burst looks the same at alarm time",
     ["experiments/exp_indistinguishable_onset.py"]),
    ("the receipts: every figure re-measured and guarded",
     ["tools/check_numbers.py"]),
]

_W = 900
_BG = (22, 24, 28)
_PROMPT = (90, 200, 120)
_CMD = (230, 230, 230)
_OUT = (180, 190, 200)
_COMMENT = (120, 130, 140)
_LINE_H = 22
_PAD = 16


def _font(size: int):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


FONT = _font(14)


def _run(argv):
    cmd = [sys.executable, *argv]
    start = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True,
        env={"PYTHONPATH": ENV_PYTHONPATH, "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    dur = time.perf_counter() - start
    out = (proc.stdout + proc.stderr).rstrip("\n")
    return out, proc.returncode, dur


def _render(lines: list[tuple]) -> Image.Image:
    height = _PAD * 2 + _LINE_H * max(len(lines), 1)
    img = Image.new("RGB", (_W, height), _BG)
    d = ImageDraw.Draw(img)
    y = _PAD
    for color, text in lines:
        d.text((_PAD, y), text, font=FONT, fill=color)
        y += _LINE_H
    return img


def run() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    # Warm the import so the first timed segment does not pay for it.
    _run(["-m", "flowmetrics.cli", "--help"])

    lines: list[tuple] = []
    frames: list[Image.Image] = []
    durations: list[int] = []
    manifest = {"segments": []}

    def snapshot(hold_ms: int):
        frames.append(_render(list(lines)))
        durations.append(hold_ms)

    for comment, argv in SEGMENTS:
        out, code, dur = _run(argv)
        shown = "python " + " ".join(a if not a.startswith("-m") else "-m" for a in argv)
        lines.append((_COMMENT, f"# {comment}"))
        lines.append((_PROMPT, "$ " + shown))
        snapshot(500)  # the typed command
        for ln in out.splitlines():
            lines.append((_OUT, "  " + ln[:110]))
        lines.append((_PROMPT, f"  -> exit {code}"))
        # Pace the output reveal by measured wall time, clamped to stay watchable.
        hold = int(min(2600, max(900, dur * 1000)))
        snapshot(hold)
        lines.append((_OUT, ""))
        manifest["segments"].append(
            {"comment": comment, "command": shown, "exit_code": code,
             "duration_s": round(dur, 3)}
        )
        # Keep the transcript from growing unbounded: cap to the last 20 lines.
        if len(lines) > 20:
            lines = lines[-20:]

    # Normalize frame heights to the tallest so the GIF does not jump.
    max_h = max(f.height for f in frames)
    norm = []
    for f in frames:
        canvas = Image.new("RGB", (_W, max_h), _BG)
        canvas.paste(f, (0, 0))
        norm.append(canvas)

    gif = OUT / "demo.gif"
    norm[0].save(gif, save_all=True, append_images=norm[1:], duration=durations,
                 loop=0, optimize=True)

    # Also an MP4 for quality, built from the same frames.
    try:
        _write_mp4(norm, durations)
    except Exception as exc:  # pragma: no cover - ffmpeg optional
        manifest["mp4_error"] = str(exc)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    size_kb = gif.stat().st_size // 1024
    print(f"wrote {gif} ({size_kb} KiB, {len(frames)} frames) and the manifest")
    return manifest


def _write_mp4(frames, durations):  # pragma: no cover - exercised only with ffmpeg
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    listing = []
    for i, (f, dur) in enumerate(zip(frames, durations)):
        p = tmp / f"f{i:03d}.png"
        f.save(p)
        listing.append(f"file '{p}'")
        listing.append(f"duration {dur / 1000:.3f}")
    listing.append(f"file '{tmp / f'f{len(frames) - 1:03d}.png'}'")
    concat = tmp / "list.txt"
    concat.write_text("\n".join(listing))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
         "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-pix_fmt", "yuv420p",
         str(OUT / "demo.mp4")],
        check=True, capture_output=True,
    )
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    run()
