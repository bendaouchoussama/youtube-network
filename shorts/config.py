"""Load config.json and fill in the per-manga call to action."""

import json
from pathlib import Path
from typing import Optional

DEFAULT_SOURCE = "an official manga app"


def official_source(cfg: dict, manga: str) -> str:
    sources = {k.lower(): v for k, v in cfg.get("official_sources", {}).items()}
    return sources.get(manga.lower(), DEFAULT_SOURCE)


def load_config(path: Path, manga: Optional[str] = None) -> dict:
    """Read the config. `manga` overrides the default manga from config.json."""
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    return with_manga(cfg, manga or cfg["manga"])


def with_manga(cfg: dict, manga: str) -> dict:
    cfg = dict(cfg, manga=manga)
    fields = {"manga": manga, "source": official_source(cfg, manga)}
    cfg["cta_on_screen"] = cfg["cta_on_screen"].format(**fields)
    cfg["cta_voice"] = cfg["cta_voice"].format(**fields)
    return cfg
