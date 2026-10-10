"""Draw scene frames with Pillow and assemble the vertical video with FFmpeg."""

import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from .script import Scene, ShortScript
from .voice import speak

W, H = 1080, 1920
FPS = 30
PAD_SECONDS = 0.25  # small breath between scenes

FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]


def _font(size: int, cfg: dict) -> ImageFont.FreeTypeFont:
    for path in [cfg.get("font")] + FONT_CANDIDATES:
        if path and Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fit_text(draw, text, cfg, max_width, max_lines, start=110, minimum=56):
    size = start
    while True:
        font = _font(size, cfg)
        lines = _wrap(draw, text, font, max_width)
        if len(lines) <= max_lines or size <= minimum:
            return font, lines
        size -= 6


def _background(cfg, image_path=None) -> Image.Image:
    bg = Image.new("RGB", (W, H), cfg.get("background_color", "#0B1020"))
    if image_path and Path(image_path).exists():
        img = Image.open(image_path).convert("RGB")
        scale = max(W / img.width, H / img.height)
        img = img.resize((int(img.width * scale) + 1, int(img.height * scale) + 1))
        left, top = (img.width - W) // 2, (img.height - H) // 2
        img = img.crop((left, top, left + W, top + H)).filter(ImageFilter.GaussianBlur(2))
        bg = ImageEnhance.Brightness(img).enhance(0.45)
    else:
        # Soft diagonal glow in the accent colour.
        glow = Image.new("RGB", (W, H), cfg.get("accent_color", "#1E6BFF"))
        mask = Image.linear_gradient("L").resize((W, H)).rotate(35, expand=False)
        bg = Image.composite(glow, bg, mask.point(lambda v: int(v * 0.35)))
    return bg


def _header_footer(draw, cfg, index, total):
    accent = cfg.get("accent_color", "#1E6BFF")
    label = cfg.get("manga", "").upper()
    font = _font(46, cfg)
    tw = draw.textlength(label, font=font)
    draw.rounded_rectangle((W / 2 - tw / 2 - 36, 150, W / 2 + tw / 2 + 36, 236), radius=43, fill=accent)
    draw.text((W / 2, 193), label, font=font, fill="white", anchor="mm")
    # progress dots
    gap, r = 34, 9
    x0 = W / 2 - gap * (total - 1) / 2
    for i in range(total):
        fill = "white" if i == index else (95, 105, 140)
        draw.ellipse((x0 + i * gap - r, 290 - r, x0 + i * gap + r, 290 + r), fill=fill)
    draw.text((W / 2, H - 170), cfg.get("handle", ""), font=_font(44, cfg), fill=(220, 225, 240), anchor="mm")


def draw_card(scene: Scene, cfg, index, total) -> Image.Image:
    img = _background(cfg, scene.image).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    _header_footer(draw, cfg, index, total)
    font, lines = _fit_text(draw, scene.on_screen, cfg, W - 160, max_lines=6)
    line_h = font.size * 1.18
    y = H / 2 - line_h * len(lines) / 2 + line_h / 2
    for line in lines:
        draw.text((W / 2, y), line, font=font, fill=cfg.get("text_color", "white"),
                  anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, 200))
        y += line_h
    return img.convert("RGB")


def _bubble(draw, text, cfg, right: bool, top: float, fill, label=None) -> float:
    font = _font(54, cfg)
    max_w = W * 0.68
    lines = _wrap(draw, text, font, max_w - 80)
    line_h = font.size * 1.25
    bw = max(draw.textlength(l, font=font) for l in lines) + 80
    bh = line_h * len(lines) + 60
    x1 = W - 70 - bw if right else 70
    if label:
        draw.text((x1 + 10, top - 20), label, font=_font(36, cfg), fill=(200, 205, 225), anchor="ls")
    draw.rounded_rectangle((x1, top, x1 + bw, top + bh), radius=42, fill=fill)
    y = top + 30 + line_h / 2
    for line in lines:
        draw.text((x1 + 40, y), line, font=font, fill="white", anchor="lm")
        y += line_h
    return top + bh


def draw_chat(scene: Scene, cfg, index, total, show_answer: bool) -> Image.Image:
    img = _background(cfg).convert("RGBA")
    draw = ImageDraw.Draw(img, "RGBA")
    _header_footer(draw, cfg, index, total)
    bottom = _bubble(draw, scene.question or scene.on_screen, cfg, right=True, top=640,
                     fill=cfg.get("accent_color", "#1E6BFF"))
    if show_answer:
        _bubble(draw, scene.answer or "", cfg, right=False, top=bottom + 120,
                fill=(40, 46, 66), label=cfg.get("bot_name", "Manga Bot"))
    else:
        draw.text((110, bottom + 150), "typing…", font=_font(40, cfg), fill=(170, 175, 200))
    return img.convert("RGB")


def _run(args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _still_clip(png: Path, seconds: float, out: Path, zoom: bool):
    frames = max(1, round(seconds * FPS))
    if zoom:
        vf = (f"scale={W * 2}:{H * 2},zoompan=z='1+0.06*on/{frames}':"
              f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}")
        _run(["-i", str(png), "-vf", vf, "-frames:v", str(frames),
              "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)])
    else:
        _run(["-loop", "1", "-i", str(png), "-t", f"{frames / FPS:.3f}", "-r", str(FPS),
              "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)])


def _pick_music(cfg, music_arg):
    if music_arg:
        return Path(music_arg)
    folder = Path(cfg.get("music_dir", "assets/music"))
    tracks = [p for p in folder.glob("*") if p.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg"}]
    return random.choice(tracks) if tracks else None


def render(script: ShortScript, cfg: dict, workdir: Path, out_path: Path, music=None) -> Path:
    workdir.mkdir(parents=True, exist_ok=True)
    total = len(script.scenes)
    segments, voices = [], []

    for i, scene in enumerate(script.scenes):
        print(f"  scene {i + 1}/{total}: {scene.type} - {scene.on_screen[:50]}")
        mp3 = workdir / f"voice_{i:02d}.mp3"
        seconds = speak(scene.voice, mp3, cfg) + PAD_SECONDS
        voices.append((mp3, seconds))
        if scene.type == "chat":
            a, b = workdir / f"scene_{i:02d}a.png", workdir / f"scene_{i:02d}b.png"
            draw_chat(scene, cfg, i, total, show_answer=False).save(a)
            draw_chat(scene, cfg, i, total, show_answer=True).save(b)
            split = seconds * 0.4
            segments += [(a, split, False), (b, seconds - split, False)]
        else:
            png = workdir / f"scene_{i:02d}.png"
            draw_card(scene, cfg, i, total).save(png)
            segments.append((png, seconds, True))

    clips = []
    for j, (png, seconds, zoom) in enumerate(segments):
        clip = workdir / f"clip_{j:02d}.mp4"
        _still_clip(png, seconds, clip, zoom)
        clips.append(clip)
    concat_list = workdir / "clips.txt"
    concat_list.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    video = workdir / "video.mp4"
    _run(["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(video)])

    # Voice track: each line padded to its scene length so it stays in sync.
    voice_inputs, parts = [], []
    for k, (mp3, seconds) in enumerate(voices):
        voice_inputs += ["-i", str(mp3)]
        parts.append(f"[{k}:a]aresample=44100,apad,atrim=0:{seconds:.3f}[v{k}]")
    labels = "".join(f"[v{k}]" for k in range(len(voices)))
    voice = workdir / "voice.wav"
    _run([*voice_inputs, "-filter_complex",
          ";".join(parts) + f";{labels}concat=n={len(voices)}:v=0:a=1[out]",
          "-map", "[out]", str(voice)])

    length = sum(s for _, s in voices)
    track = _pick_music(cfg, music)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if track:
        print(f"  music: {track.name}")
        vol = cfg.get("music_volume", 0.12)
        fade_start = max(0.0, length - 1.5)
        _run(["-i", str(video), "-i", str(voice), "-stream_loop", "-1", "-i", str(track),
              "-filter_complex",
              f"[2:a]volume={vol},afade=t=out:st={fade_start:.2f}:d=1.5[m];"
              f"[1:a][m]amix=inputs=2:duration=first:normalize=0[a]",
              "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
              "-t", f"{length:.3f}", "-movflags", "+faststart", str(out_path)])
    else:
        print("  music: none (add .mp3 files to assets/music/)")
        _run(["-i", str(video), "-i", str(voice), "-map", "0:v", "-map", "1:a",
              "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{length:.3f}",
              "-movflags", "+faststart", str(out_path)])
    return out_path
