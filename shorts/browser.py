"""Record a web page in a phone-sized browser while it scrolls, for "web" scenes."""

import subprocess
from pathlib import Path

CAPTURE_FPS = 15
VIEWPORT = {"width": 540, "height": 960}  # 9:16, captured at 2x = 1080x1920


def _ease(t: float) -> float:
    return t * t * (3 - 2 * t)  # smooth start and stop


def record_page(url: str, seconds: float, out: Path, cfg: dict, scroll_px=None, wait: float = 1.5) -> Path:
    """Open `url`, scroll down over `seconds`, and save a 1080x1920 video to `out`.

    scroll_px: how far to scroll (default: the whole page, up to 6000 px). 0 = no scrolling.
    """
    from playwright.sync_api import sync_playwright

    if "://" not in url and Path(url).exists():
        url = Path(url).resolve().as_uri()  # local HTML file

    frames_dir = out.with_suffix("")
    frames_dir.mkdir(parents=True, exist_ok=True)
    frames = max(1, round(seconds * CAPTURE_FPS))

    with sync_playwright() as p:
        launch = {"executable_path": cfg["browser_path"]} if cfg.get("browser_path") else {}
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2, is_mobile=True, has_touch=True)
        page.goto(url, wait_until="load", timeout=45_000)
        page.wait_for_timeout(wait * 1000)
        if scroll_px is None:
            page_h = page.evaluate("document.documentElement.scrollHeight")
            scroll_px = min(max(0, page_h - VIEWPORT["height"]), 6000)
        for i in range(frames):
            y = scroll_px * _ease(i / max(1, frames - 1))
            page.evaluate(f"window.scrollTo(0, {y:.0f})")
            page.screenshot(path=str(frames_dir / f"f_{i:05d}.png"))
        browser.close()

    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-framerate", str(CAPTURE_FPS), "-i", str(frames_dir / "f_%05d.png"),
         "-vf", "scale=1080:1920,fps=30", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )
    return out
