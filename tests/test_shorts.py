import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from make_short import slugify  # noqa: E402
from shorts import voice  # noqa: E402
from shorts.config import load_config  # noqa: E402
from shorts.render import H, W, draw_card, draw_chat, render  # noqa: E402
from shorts.script import ShortScript, generate_script, load_script  # noqa: E402

CONFIG = ROOT / "config.json"
EXAMPLES = sorted((ROOT / "scripts").glob("*.json"))


def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def test_blue_lock_cta_points_to_official_source():
    cfg = load_config(CONFIG)
    assert cfg["manga"] == "Blue Lock"
    assert cfg["cta_on_screen"] == "Read Blue Lock officially on K MANGA"
    assert "K MANGA" in cfg["cta_voice"] and "{" not in cfg["cta_voice"]


def test_other_manga_and_unknown_manga():
    assert "MANGA Plus" in load_config(CONFIG, "one piece")["cta_on_screen"]
    unknown = load_config(CONFIG, "My Indie Comic")
    assert unknown["cta_on_screen"] == "Read My Indie Comic officially on an official manga app"


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_example_scripts_are_valid(path):
    script = load_script(path)
    assert script.manga == "Blue Lock"
    assert script.scenes[0].type == "chat" and script.scenes[0].question and script.scenes[0].answer
    assert script.scenes[-1].on_screen == load_config(CONFIG)["cta_on_screen"]
    assert "#shorts" in script.title


def test_slugify():
    assert slugify("Blue Lock Top 5 Isagi goals!") == "blue-lock-top-5-isagi-goals"
    assert slugify("???") == "short"


def test_frames_are_vertical_and_drawn():
    cfg = load_config(CONFIG)
    script = load_script(ROOT / "scripts" / "isagi-top-moments.json")
    chat = draw_chat(script.scenes[0], cfg, 0, 5, show_answer=True)
    card = draw_card(script.scenes[1], cfg, 1, 5)
    for img in (chat, card):
        assert img.size == (W, H) == (1080, 1920)
        assert len(img.getcolors(maxcolors=1_000_000) or []) > 50  # not a blank frame


def test_unknown_voice_engine(tmp_path):
    with pytest.raises(ValueError):
        voice.speak("hi", tmp_path / "v", {"voice_engine": "nope"})


def test_full_blue_lock_video(tmp_path):
    cfg = dict(load_config(CONFIG), voice_engine="silent")
    script = load_script(ROOT / "scripts" / "rin-vs-isagi.json")
    music = tmp_path / "music.mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=330:duration=5",
                    str(music)], check=True)

    out = render(script, cfg, tmp_path / "work", tmp_path / "blue-lock.mp4", music=str(music))

    info = probe(out)
    kinds = {s["codec_type"]: s for s in info["streams"]}
    assert kinds["video"]["width"] == 1080 and kinds["video"]["height"] == 1920
    assert "audio" in kinds
    seconds = float(info["format"]["duration"])
    assert 15 < seconds < 60  # YouTube Shorts must be under 60 s here


def test_generate_script_asks_for_blue_lock(monkeypatch):
    """The AI call is mocked: checks the request we send and that the result is used."""
    import anthropic

    cfg = load_config(CONFIG)
    fake = load_script(ROOT / "scripts" / "isagi-top-moments.json").model_copy(update={"manga": None})
    seen = {}

    class FakeClient:
        def __init__(self):
            self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

        def parse(self, **kwargs):
            seen.update(kwargs)
            return SimpleNamespace(stop_reason="end_turn", parsed_output=fake)

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    script = generate_script("Top 5 Isagi goals", cfg)

    assert script.manga == "Blue Lock"
    assert seen["model"] == "claude-opus-5-5"
    assert seen["output_format"] is ShortScript
    assert "Blue Lock" in seen["system"] and "K MANGA" in seen["system"]
    assert "pirate" in seen["system"]
    assert seen["messages"][0]["content"] == "Topic: Top 5 Isagi goals"


def test_video_scene_with_recording(tmp_path):
    """A landscape 'screen recording' shorter than the voice gets looped and fitted to 9:16."""
    rec = tmp_path / "rec.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30:duration=2",
                    "-pix_fmt", "yuv420p", str(rec)], check=True)
    script = ShortScript.model_validate({
        "manga": "Blue Lock", "title": "t #shorts", "description": "d", "hashtags": ["shorts"],
        "scenes": [
            {"type": "video", "video": str(rec), "on_screen": "My reaction",
             "voice": "This line is longer than the two second recording, so the clip has to loop."},
            {"type": "video", "video": str(rec), "video_fit": "fill", "on_screen": "Zoomed", "voice": "Fill mode."},
        ],
    })
    cfg = dict(load_config(CONFIG), voice_engine="silent")
    out = render(script, cfg, tmp_path / "work", tmp_path / "rec-short.mp4")
    info = probe(out)
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    assert (video["width"], video["height"]) == (1080, 1920)
    assert float(info["format"]["duration"]) > 4  # longer than the 2 s recording: it looped


def test_missing_recording_is_reported(tmp_path):
    script = ShortScript.model_validate({
        "title": "t", "description": "d", "hashtags": [],
        "scenes": [{"type": "video", "video": "nope.mp4", "on_screen": "x", "voice": "x"}],
    })
    cfg = dict(load_config(CONFIG), voice_engine="silent")
    with pytest.raises(FileNotFoundError, match="nope.mp4"):
        render(script, cfg, tmp_path / "work", tmp_path / "x.mp4")


@pytest.mark.skipif(not shutil.which("espeak-ng"), reason="espeak-ng not installed")
def test_espeak_voice_is_not_silent(tmp_path):
    out, seconds = voice.speak("Isagi scores again", tmp_path / "v", {"voice_engine": "espeak"})
    assert out.suffix == ".wav" and 0.5 < seconds < 5
    vol = subprocess.run(["ffmpeg", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    max_db = float(vol.split("max_volume:")[1].split("dB")[0])
    assert max_db > -30
