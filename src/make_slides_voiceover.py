#!/usr/bin/env python3
"""Synthesize per-slide narration for the deck with macOS `say` (free, offline).

Parses artifacts/slides_voiceover.md (`## Slide N` blocks, `>` quoted lines),
voices each slide to artifacts/slides_audio/slide_N.mp3, and writes a
durations.json mapping slide -> seconds (probed with ffprobe) so the recorder
can hold each slide for exactly its narration length.

Usage:
  .venv/bin/python src/make_slides_voiceover.py --voice Daniel --rate 172
"""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VO_MD = ROOT / "artifacts" / "slides_voiceover.md"
OUT_DIR = ROOT / "artifacts" / "slides_audio"


def require(tool: str) -> str:
    p = shutil.which(tool)
    if not p:
        sys.exit(f"'{tool}' not found (need macOS `say`, `ffmpeg`, `ffprobe`).")
    return p


def parse_slides(md: str) -> list[tuple[int, str]]:
    parts = re.split(r"^## Slide (\d+).*$", md, flags=re.MULTILINE)
    out: list[tuple[int, str]] = []
    for i in range(1, len(parts), 2):
        num = int(parts[i])
        body = parts[i + 1]
        quoted = [ln.lstrip()[1:].strip() for ln in body.splitlines() if ln.lstrip().startswith(">")]
        text = " ".join(q for q in quoted if q)
        if text:
            out.append((num, text))
    return out


def synth(text: str, voice: str, rate: int, mp3: Path) -> None:
    with tempfile.NamedTemporaryFile(suffix=".aiff", delete=False) as tmp:
        aiff = Path(tmp.name)
    try:
        subprocess.run(["say", "-v", voice, "-r", str(rate), "-o", str(aiff), text], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff),
                        "-codec:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
    finally:
        aiff.unlink(missing_ok=True)


def duration(mp3: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(mp3)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()), 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Daniel")
    ap.add_argument("--rate", type=int, default=172)
    args = ap.parse_args()
    for t in ("say", "ffmpeg", "ffprobe"):
        require(t)

    slides = parse_slides(VO_MD.read_text())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    durations: dict[str, float] = {}
    for num, text in slides:
        mp3 = OUT_DIR / f"slide_{num}.mp3"
        synth(text, args.voice, args.rate, mp3)
        d = duration(mp3)
        durations[str(num)] = d
        print(f"slide {num:>2}: {d:5.2f}s  <- {text[:56]}...")

    (OUT_DIR / "durations.json").write_text(json.dumps(durations, indent=2))
    total = sum(durations.values())
    print(f"\n{len(slides)} slides, total narration {total:.1f}s "
          f"({total/60:.1f} min), voice={args.voice}")


if __name__ == "__main__":
    main()
