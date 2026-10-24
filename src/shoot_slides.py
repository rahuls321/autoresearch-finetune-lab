#!/usr/bin/env python3
"""Screenshot each slide of the reveal.js deck for a visual check.

Usage: .venv/bin/python src/shoot_slides.py --port 8809 --n 15 --outdir artifacts/slides_shots
"""
from __future__ import annotations
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def run(port: int, n: int, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{port}/slides/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(600)
        page.evaluate("() => window.Reveal && window.Reveal.configure({transition:'none'})")
        el = page.query_selector(".reveal")
        for i in range(n):
            page.wait_for_timeout(350)
            shot = outdir / f"slide_{i+1:02d}.png"
            (el or page).screenshot(path=str(shot))
            print(f"shot {shot.name}")
            page.evaluate("() => window.Reveal && window.Reveal.next()")
        browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8809)
    ap.add_argument("--n", type=int, default=15)
    ap.add_argument("--outdir", type=Path, default=Path("artifacts/slides_shots"))
    a = ap.parse_args()
    run(a.port, a.n, a.outdir)
