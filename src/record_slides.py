#!/usr/bin/env python3
"""Record the reveal.js deck into a narrated MP4, slide-by-slide, frame-accurate.

For each slide we record its own webm held for (narration_duration + PAD) seconds,
with a short slide-in transition at the start, then retime the webm to exactly the
target duration (CFR 30fps) and concatenate. Finally we concat the per-slide
narration mp3s and mux. This mirrors the demo pipeline (record_dashboard.py) which
already produced frame-accurate sync.

Usage:
  .venv/bin/python src/record_slides.py --port 8820 \
      --outdir artifacts/demo_video --work artifacts/demo_video/_slides
"""
from __future__ import annotations
import argparse, json, re, subprocess, tempfile, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "artifacts" / "slides_audio"
PAD = 0.6            # extra hold per slide so the transition isn't clipped
LEAD = 0.35         # time the transition animation takes before the slide settles


def durations() -> dict[int, float]:
    d = json.loads((AUDIO_DIR / "durations.json").read_text())
    return {int(k): float(v) for k, v in d.items()}


def record_slide(browser, url, work: Path, idx: int, hold: float) -> Path:
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=str(work),
        record_video_size={"width": 1280, "height": 720},
        device_scale_factor=1,
    )
    page = ctx.new_page()
    # Jump straight to slide idx (0-based for reveal), with transition on entry.
    page.goto(f"{url}#/{idx-1}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(int((hold + PAD) * 1000))
    vid = page.video
    ctx.close()
    dst = work / f"slide{idx:02d}.webm"
    vid.save_as(str(dst))
    print(f"[rec] slide {idx:>2} held {hold+PAD:4.1f}s -> {dst.name}")
    return dst


def probe_duration(path: Path) -> float:
    # Container header first (works for our CFR mp4s).
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True)
    val = out.stdout.strip()
    if val and val != "N/A":
        try:
            return float(val)
        except ValueError:
            pass
    # Playwright webm: ffprobe's strict header probe can fail even though ffmpeg
    # decodes fine. Decode to null and read the final time= from stderr.
    out = subprocess.run(
        ["ffmpeg", "-i", str(path), "-f", "null", "-"],
        capture_output=True, text=True)
    last = None
    for m in re.finditer(r"time=(\d+):(\d+):(\d+\.\d+)", out.stderr):
        h, mnt, s = m.groups()
        last = int(h) * 3600 + int(mnt) * 60 + float(s)
    if last:
        return last
    raise RuntimeError(f"could not determine duration of {path}\n{out.stderr[-400:]}")


def retime(src: Path, target: float, dst: Path) -> None:
    actual = probe_duration(src)
    factor = target / actual if actual > 0 else 1.0
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
         "-vf", f"setpts={factor:.6f}*PTS,fps=30,scale=1280:720",
         "-an", "-r", "30", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-preset", "medium", "-crf", "20", str(dst)],
        check=True)
    print(f"[retime] {src.name}: {actual:.2f}s -> {target:.2f}s (x{factor:.3f})")


def concat_videos(parts: list[Path], dst: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
        lst = Path(f.name)
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", str(lst), "-c", "copy", str(dst)], check=True)
    finally:
        lst.unlink(missing_ok=True)


def concat_audio(parts: list[Path], dst: Path) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for p in parts:
            f.write(f"file '{p.resolve()}'\n")
        lst = Path(f.name)
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat",
                        "-safe", "0", "-i", str(lst), "-codec:a", "libmp3lame",
                        "-q:a", "2", str(dst)], check=True)
    finally:
        lst.unlink(missing_ok=True)


def mux(video: Path, audio: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(dst)],
        check=True)


def run(port: int, outdir: Path, work: Path, skip_record: bool = False, only: int = 0) -> None:
    url = f"http://127.0.0.1:{port}/slides/index.html"
    work.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    durs = durations()
    n = len(durs)

    if only:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # A warm-up throwaway context avoids Playwright's occasional 0-byte
            # first recording.
            warm = browser.new_context(record_video_dir=str(work / "_warm"))
            wp = warm.new_page(); wp.goto(url, wait_until="networkidle", timeout=60000)
            wp.wait_for_timeout(500); warm.close()
            record_slide(browser, url, work, only, durs[only])
            browser.close()
        print(f"[rec] re-recorded slide {only}")
        return

    if skip_record:
        raw = [(i, work / f"slide{i:02d}.webm") for i in range(1, n + 1)]
        missing = [p for _, p in raw if not p.exists()]
        if missing:
            raise SystemExit(f"--skip-record but missing: {missing}")
        print(f"[rec] reusing {n} existing webms in {work}")
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            raw = []
            for i in range(1, n + 1):
                raw.append((i, record_slide(browser, url, work, i, durs[i])))
            browser.close()

    retimed: list[Path] = []
    for i, src in raw:
        dst = work / f"slide{i:02d}_cfr.mp4"
        # video target = narration + small tail so audio never gets clipped
        retime(src, durs[i] + 0.25, dst)
        retimed.append(dst)

    silent = outdir / "slides_video_silent.mp4"
    concat_videos(retimed, silent)
    print(f"[concat] video -> {silent}  ({probe_duration(silent):.1f}s)")

    audio_parts = [AUDIO_DIR / f"slide_{i}.mp3" for i in range(1, n + 1)]
    narration = outdir / "slides_narration.mp3"
    concat_audio(audio_parts, narration)
    print(f"[concat] audio -> {narration}  ({probe_duration(narration):.1f}s)")

    final = outdir / "lazydecider_slides.mp4"
    mux(silent, narration, final)
    print(f"[done] {final}  ({probe_duration(final):.1f}s)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8820)
    ap.add_argument("--outdir", type=Path, default=Path("artifacts/demo_video"))
    ap.add_argument("--work", type=Path, default=Path("artifacts/demo_video/_slides"))
    ap.add_argument("--skip-record", action="store_true", help="reuse existing webms")
    ap.add_argument("--only", type=int, default=0, help="re-record just this slide number")
    a = ap.parse_args()
    run(a.port, a.outdir, a.work, a.skip_record, a.only)
