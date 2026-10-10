#!/usr/bin/env python3
"""Make one YouTube Short per command.

  python make_short.py "Top 5 Isagi goals"            # AI writes the script, then renders
  python make_short.py "Top 5 Isagi goals" --script-only   # only write the script to edit first
  python make_short.py --script scripts/isagi-top-moments.json   # render a script you wrote/edited
  python make_short.py "Luffy's best fights" --manga "One Piece"  # any manga
"""

import argparse
import re
import sys
from pathlib import Path

from shorts.config import load_config
from shorts.render import render
from shorts.script import generate_script, load_script, save_script

ROOT = Path(__file__).resolve().parent


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "short"


def main() -> int:
    p = argparse.ArgumentParser(description="Make a vertical YouTube Short with AI voice and background music.")
    p.add_argument("topic", nargs="?", help="What the Short is about, e.g. \"Why Rin hates Isagi\"")
    p.add_argument("--script", help="Render this script JSON instead of asking the AI")
    p.add_argument("--script-only", action="store_true", help="Write the AI script and stop (edit it, then use --script)")
    p.add_argument("--manga", help="Which manga (default: \"manga\" in config.json)")
    p.add_argument("--music", help="Use this music file instead of a random one from assets/music/")
    p.add_argument("--config", default=str(ROOT / "config.json"))
    p.add_argument("--silent", action="store_true", help="No voice (offline preview of the visuals and timing)")
    args = p.parse_args()

    if not args.topic and not args.script:
        p.error("give a topic or --script FILE")

    script = load_script(Path(args.script)) if args.script else None
    cfg = load_config(Path(args.config), args.manga or (script and script.manga))
    if args.silent:
        cfg["voice_engine"] = "silent"

    if script:
        script.manga = cfg["manga"]
        slug = slugify(Path(args.script).stem)
    else:
        print(f"Writing a {cfg['manga']} script for: {args.topic}")
        script = generate_script(args.topic, cfg)
        slug = slugify(f"{cfg['manga']} {args.topic}")

    out_dir = ROOT / "output" / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    save_script(script, out_dir / "script.json")
    (out_dir / "upload.txt").write_text(
        f"TITLE:\n{script.title}\n\nDESCRIPTION:\n{script.description}\n\n"
        + " ".join(f"#{h.lstrip('#')}" for h in script.hashtags) + "\n",
        encoding="utf-8",
    )
    if args.script_only:
        print(f"Script saved: {out_dir / 'script.json'}")
        print(f"Edit it, then run: python make_short.py --script {out_dir / 'script.json'}")
        return 0

    print("Rendering video...")
    video = render(script, cfg, out_dir / "work", out_dir / f"{slug}.mp4", music=args.music)
    print(f"\nDone! Video: {video}")
    print(f"Title/description/hashtags: {out_dir / 'upload.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
