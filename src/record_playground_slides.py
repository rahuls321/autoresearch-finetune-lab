#!/usr/bin/env python3
"""Record the local Gradio playground for the deck finale — one webm per narration
segment (slides 16-19), at 1280x720 so it matches the deck video.

Segments:
  16 intro          — show the loaded UI, drift the cursor over the inputs
  17 clean match    — pick preset, Decide, hold on the 'approve' result
  18 over-invoiced  — pick preset, Decide, hold on the 'review' result
  19 under-delivered— pick preset, Decide, hold on the 'manual review' result

Each segment records in its own context (one webm) and is held for roughly its
narration duration so the retime factor stays near 1. Requires the playground
server running on --port (model preloaded).

Usage:
  .venv/bin/python src/record_playground_slides.py --port 7860 \
      --work artifacts/demo_video/_slides
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "artifacts" / "slides_audio"

CURSOR_JS = r"""
(() => {
  if (document.getElementById('__cur')) return;
  const c = document.createElement('div');
  c.id='__cur';
  c.style.cssText='position:fixed;z-index:999999;width:22px;height:22px;margin:-11px 0 0 -11px;'
    +'border-radius:50%;background:rgba(45,212,191,.35);border:2px solid #2dd4bf;'
    +'box-shadow:0 0 10px rgba(45,212,191,.8);pointer-events:none;left:640px;top:360px;';
  document.body.appendChild(c);
  window.__moveCur=(x,y)=>{c.style.left=x+'px';c.style.top=y+'px';};
  window.__clickCur=()=>{
    const c=document.getElementById('__cur');
    const r=document.createElement('div');
    r.style.cssText='position:fixed;z-index:999998;width:10px;height:10px;margin:-5px 0 0 -5px;'
      +'border-radius:50%;border:2px solid #2dd4bf;pointer-events:none;'
      +'left:'+c.style.left+';top:'+c.style.top+';opacity:1;transition:all .45s ease-out;';
    document.body.appendChild(r);
    requestAnimationFrame(()=>{r.style.width='56px';r.style.height='56px';r.style.margin='-28px 0 0 -28px';r.style.opacity='0';});
    setTimeout(()=>r.remove(),500);
  };
})();
"""


def durations() -> dict[int, float]:
    d = json.loads((AUDIO_DIR / "durations.json").read_text())
    return {int(k): float(v) for k, v in d.items()}


def glide(page, x, y, steps=26, pause=0.012):
    cur = page.evaluate("() => { const c=document.getElementById('__cur'); return [parseFloat(c.style.left), parseFloat(c.style.top)]; }")
    x0, y0 = cur
    for i in range(1, steps + 1):
        nx = x0 + (x - x0) * i / steps
        ny = y0 + (y - y0) * i / steps
        page.evaluate("([x,y])=>window.__moveCur(x,y)", [nx, ny])
        page.mouse.move(nx, ny)
        time.sleep(pause)


def click_loc(page, locator):
    box = locator.bounding_box()
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    glide(page, cx, cy)
    page.evaluate("()=>window.__clickCur()")
    time.sleep(0.15)
    locator.click()
    time.sleep(0.3)


def new_ctx(browser, work: Path):
    ctx = browser.new_context(
        viewport={"width": 1280, "height": 720},
        record_video_dir=str(work),
        record_video_size={"width": 1280, "height": 720},
        device_scale_factor=1,
    )
    page = ctx.new_page()
    return ctx, page


def prep(page, url):
    page.goto(url, wait_until="networkidle", timeout=90000)
    # Tighten Gradio so the decision + table fit the 720 viewport.
    page.add_style_tag(content="footer{display:none!important} .gradio-container{padding-top:4px!important} .prose h1{font-size:1.3rem!important}")
    page.wait_for_timeout(700)
    page.evaluate(CURSOR_JS)
    page.wait_for_timeout(300)


def decide_and_hold(page, preset_name, hold_s):
    preset = page.get_by_label("Load an example")
    click_loc(page, preset)
    page.wait_for_timeout(350)
    opt = page.get_by_role("option", name=preset_name)
    click_loc(page, opt)
    page.wait_for_timeout(500)
    decide = page.get_by_role("button", name="Decide")
    click_loc(page, decide)
    page.wait_for_function("() => document.body.innerText.includes('Decision:')", timeout=90000)
    page.evaluate("() => window.scrollTo({top:0, behavior:'smooth'})")
    page.wait_for_timeout(400)
    glide(page, 820, 150)
    page.wait_for_timeout(int(hold_s * 1000))


def save(page, ctx, work: Path, idx: int):
    vid = page.video
    ctx.close()
    dst = work / f"slide{idx:02d}.webm"
    vid.save_as(str(dst))
    print(f"[pg] segment {idx} -> {dst.name} ({dst.stat().st_size} bytes)")


def run(port: int, work: Path):
    url = f"http://127.0.0.1:{port}/"
    work.mkdir(parents=True, exist_ok=True)
    durs = durations()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # Warm-up throwaway context (avoids Playwright's 0-byte first recording).
        warm, wp = new_ctx(browser, work / "_warm")
        try:
            prep(wp, url)
        finally:
            warm.close()

        # 16 — intro: show loaded UI, drift cursor over the input panel
        ctx, page = new_ctx(browser, work)
        prep(page, url)
        for (x, y) in [(300, 220), (320, 360), (300, 500), (820, 140)]:
            glide(page, x, y)
            page.wait_for_timeout(500)
        page.wait_for_timeout(int(max(0, durs[16] - 4) * 1000))
        save(page, ctx, work, 16)

        # 17 — clean match -> approve
        ctx, page = new_ctx(browser, work)
        prep(page, url)
        decide_and_hold(page, "Clean match (should approve)", durs[17] - 4.5)
        save(page, ctx, work, 17)

        # 18 — over-invoiced -> review
        ctx, page = new_ctx(browser, work)
        prep(page, url)
        decide_and_hold(page, "Over-invoiced +12% (review)", durs[18] - 4.5)
        save(page, ctx, work, 18)

        # 19 — under-delivered -> manual review (hold longer; longest narration)
        ctx, page = new_ctx(browser, work)
        prep(page, url)
        decide_and_hold(page, "Under-delivered -50% (discrepancy)", durs[19] - 4.5)
        save(page, ctx, work, 19)

        browser.close()
    print("[pg] all playground segments saved")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7860)
    ap.add_argument("--work", type=Path, default=Path("artifacts/demo_video/_slides"))
    a = ap.parse_args()
    run(a.port, a.work)
