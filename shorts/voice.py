"""Text-to-speech for each scene."""

import asyncio
import subprocess
from pathlib import Path


def audio_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def _edge_tts(text: str, voice: str, rate: str, out: Path) -> None:
    import edge_tts

    asyncio.run(edge_tts.Communicate(text, voice, rate=rate).save(str(out)))


def _silence(text: str, out: Path) -> None:
    # Offline preview: silent track as long as the line would take to say (~2.6 words/sec).
    seconds = max(1.5, len(text.split()) / 2.6)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
         "-t", f"{seconds:.2f}", "-c:a", "libmp3lame", str(out)],
        check=True,
    )


def speak(text: str, out: Path, cfg: dict) -> float:
    """Write the spoken `text` to `out` (mp3) and return its length in seconds."""
    engine = cfg.get("voice_engine", "edge")
    if engine == "edge":
        _edge_tts(text, cfg.get("voice", "en-US-GuyNeural"), cfg.get("voice_rate", "+0%"), out)
    elif engine == "silent":
        _silence(text, out)
    else:
        raise ValueError(f"Unknown voice_engine {engine!r} (use 'edge' or 'silent')")
    return audio_duration(out)
