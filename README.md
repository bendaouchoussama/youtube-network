# YouTube Shorts maker — Blue Lock fan channel

One command makes one vertical YouTube Short (1080×1920, ~30–40 s) with:
- a **chat hook** (a viewer asks "Manga Bot" a question, the bot answers)
- fast **text cards** (rankings, theories, moments)
- **AI voice** (Microsoft Edge TTS, free)
- **background music** (random track from `assets/music/`)
- a ready **title, description and hashtags** in `upload.txt`

## Setup (once)

1. Install Python 3.10+ and FFmpeg (https://ffmpeg.org/download.html).
2. `pip install -r requirements.txt`
3. Add music files to `assets/music/` (YouTube Audio Library is safe).
4. For AI-written scripts, set your Claude API key: `export ANTHROPIC_API_KEY=...`
   (Windows: `set ANTHROPIC_API_KEY=...`).
5. Edit `config.json`: channel name, `@handle`, voice, colors.

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
| `voice`, `voice_rate` | Edge TTS voice, e.g. `en-US-GuyNeural`, `en-US-AriaNeural`, `en-GB-RyanNeural` |
| `music_volume` | 0.05 (quiet) – 0.3 (loud) |
| `accent_color`, `background_color`, `text_color` | colors |
| `target_seconds` | how long the AI aims for |

## Stay safe on YouTube

- Use your own words and your own/licensed images — not manga page scans.
- Point viewers to official reading (K MANGA / Kodansha) or your own channel.
- Only use music you have the rights to.
