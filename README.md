# YouTube Shorts maker — Blue Lock fan channel

One command makes one vertical YouTube Short (1080×1920, ~30–40 s) with:
- a **chat hook** (a viewer asks "Manga Bot" a question, the bot answers)
- fast **text cards** (rankings, theories, moments)
- **AI voice**: [OmniVoice](https://github.com/k2-fsa/OmniVoice) (open source, runs on your PC; default) or Microsoft Edge TTS (free, online)
- **background music** (random track from `assets/music/`)
- a ready **title, description and hashtags** in `upload.txt`

## Setup (once)

1. Install Python 3.10+ and FFmpeg (https://ffmpeg.org/download.html).
2. `pip install -r requirements.txt`
3. Install OmniVoice (the default voice). Its code is already inside this project in
   `vendor/OmniVoice` (git submodule):
   - Get the code: clone with `git clone --recursive <this repo>`, or in an existing clone run
     `git submodule update --init`
   - Install PyTorch for your computer: https://pytorch.org/get-started/locally/
     (NVIDIA GPU is fastest; Apple Silicon and plain CPU also work, CPU is slower)
   - `pip install -e vendor/OmniVoice`
   - The first video downloads the voice model from Hugging Face (a few GB, one time only).
   - No GPU / too slow? Set `"voice_engine": "edge"` in `config.json`.
   - Update OmniVoice later: `git submodule update --remote vendor/OmniVoice`
4. Add music files to `assets/music/` (YouTube Audio Library is safe).
5. For AI-written scripts, set your Claude API key: `export ANTHROPIC_API_KEY=...`
   (Windows: `set ANTHROPIC_API_KEY=...`).
6. Edit `config.json`: channel name, `@handle`, voice, colors.

## Make a video

```bash
# AI writes the script, then the video is made
python make_short.py "Top 5 Isagi goals"

# Check/edit the script first, then render it
python make_short.py "Why Rin hates Isagi" --script-only
python make_short.py --script output/why-rin-hates-isagi/script.json

# Render a script you wrote yourself (no API key needed)
python make_short.py --script scripts/isagi-top-moments.json
```

The result is in `output/<topic>/`:
- `<topic>.mp4` — upload this to YouTube Shorts
- `upload.txt` — title, description, hashtags
- `script.json` — the script (edit and re-render any time)

`--silent` makes a preview without voice (useful offline). `--music file.mp3` picks a specific track.

## Script format

See `scripts/isagi-top-moments.json`. Each scene is either:
- `"type": "chat"` with `question`, `answer`, `on_screen`, `voice`
- `"type": "card"` with `on_screen`, `voice`, and optional `image` (your own art)

## Settings (`config.json`)

| Key | What it does |
|---|---|
| `channel_name`, `handle` | shown at the bottom of every frame |
| `manga` | label at the top, and the topic the AI writes about |
| `cta_on_screen`, `cta_voice` | the last scene (call to action) |
| `voice_engine` | `omnivoice` (default), `edge`, or `silent` |
| `omnivoice_instruct` | Voice design: comma list of gender (`male`/`female`), age (`child`, `teenager`, `young adult`, `middle-aged`, `elderly`), pitch (`very low pitch` … `very high pitch`), accent (`american accent`, `british accent`, …), `whisper` |
| `omnivoice_ref_audio`, `omnivoice_ref_text` | Clone a voice instead: path to a 3–10 s clean recording of **your own voice** (+ what you say in it; leave text empty to auto-transcribe). Overrides `omnivoice_instruct` |
| `omnivoice_speed` | 1.0 normal, 1.1–1.2 good for Shorts |
| `omnivoice_steps` | 32 best quality, 16 faster |
| `omnivoice_device` | `auto`, `cuda:0`, `mps`, or `cpu` |
| `voice`, `voice_rate` | Edge TTS only, e.g. `en-US-GuyNeural`, `en-GB-RyanNeural` |
| `music_volume` | 0.05 (quiet) – 0.3 (loud) |
| `accent_color`, `background_color`, `text_color` | colors |
| `target_seconds` | how long the AI aims for |

## Stay safe on YouTube

- Use your own words and your own/licensed images — not manga page scans.
- Point viewers to official reading (K MANGA / Kodansha) or your own channel.
- Only use music you have the rights to.
- Only clone your own voice (or a voice you have permission to use).
