"""Text-to-speech for each scene."""

import asyncio
import subprocess
import sys
from pathlib import Path

VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor" / "OmniVoice"


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _edge_tts(text: str, cfg: dict, out: Path) -> None:
    import edge_tts

    voice, rate = cfg.get("voice", "en-US-GuyNeural"), cfg.get("voice_rate", "+0%")
    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(out)))


_omnivoice = {}


def _omnivoice_model(cfg: dict):
    """Load OmniVoice once per run (first run downloads the model from Hugging Face)."""
    if "model" not in _omnivoice:
        import torch

        try:
            from omnivoice import OmniVoice
        except ImportError:
            # Use the copy bundled in vendor/OmniVoice (git submodule).
            sys.path.insert(0, str(VENDOR_DIR))
            from omnivoice import OmniVoice

        device = cfg.get("omnivoice_device", "auto")
        if device == "auto":
            if torch.cuda.is_available():
                device = "cuda:0"
            elif torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"
        dtype = torch.float32 if device == "cpu" else torch.float16
        print(f"  loading OmniVoice on {device}...")
        try:
            _omnivoice["model"] = OmniVoice.from_pretrained(
                cfg.get("omnivoice_model", "k2-fsa/OmniVoice"), device_map=device, dtype=dtype
            )
        except Exception as exc:
            raise SystemExit(
                f"\nCould not load the OmniVoice model: {exc}\n"
                "- The first run downloads it from Hugging Face: check your internet connection.\n"
                "- If Hugging Face is blocked for you, run: export HF_ENDPOINT=https://hf-mirror.com\n"
                "- Or set \"voice_engine\": \"edge\" in config.json to use Edge TTS instead."
            ) from exc
    return _omnivoice["model"]


def _omnivoice_tts(text: str, cfg: dict, out: Path) -> None:
    import soundfile as sf

    model = _omnivoice_model(cfg)
    kwargs = {
        "speed": cfg.get("omnivoice_speed", 1.0),
        "num_step": cfg.get("omnivoice_steps", 32),
    }
    if cfg.get("omnivoice_ref_audio"):
        # Voice cloning: your own 3-10 s recording.
        kwargs["ref_audio"] = cfg["omnivoice_ref_audio"]
        if cfg.get("omnivoice_ref_text"):
            kwargs["ref_text"] = cfg["omnivoice_ref_text"]
    elif cfg.get("omnivoice_instruct"):
        # Voice design, e.g. "male, young adult, american accent".
        kwargs["instruct"] = cfg["omnivoice_instruct"]
    audio = model.generate(text=text, **kwargs)
    sf.write(str(out), audio[0], model.sampling_rate or 24000)


def _espeak(text: str, cfg: dict, out: Path) -> None:
    # Offline robot-style voice (install: apt install espeak-ng / brew install espeak-ng).
    subprocess.run(["espeak-ng", "-v", cfg.get("espeak_voice", "en-us"), "-s", str(cfg.get("espeak_speed", 165)),
                    "-w", str(out), text], check=True)


def _silence(text: str, out: Path) -> None:
    # Offline preview: silent track as long as the line would take to say (~2.6 words/sec).
    seconds = max(1.5, len(text.split()) / 2.6)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{seconds:.2f}", str(out)],
        check=True,
    )


ENGINES = {
    "edge": (_edge_tts, ".mp3"),
    "omnivoice": (_omnivoice_tts, ".wav"),
    "espeak": (_espeak, ".wav"),
    "silent": (lambda text, cfg, out: _silence(text, out), ".wav"),
}


def speak(text: str, out_stem: Path, cfg: dict) -> tuple[Path, float]:
    """Say `text` into `out_stem` + the engine's extension. Returns (file, seconds)."""
    engine = cfg.get("voice_engine", "edge")
    if engine not in ENGINES:
        raise ValueError(f"Unknown voice_engine {engine!r} (use one of: {', '.join(ENGINES)})")
    fn, ext = ENGINES[engine]
    out = out_stem.with_suffix(ext)
    fn(text, cfg, out)
    return out, audio_duration(out)
