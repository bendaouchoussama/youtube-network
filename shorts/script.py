"""Short-video scripts: the data model, loading from JSON, and AI generation."""

from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Scene(BaseModel):
    # "chat": a question bubble and a bot answer bubble (the hook).
    # "card": big on-screen text over a background (or your own image).
    type: Literal["chat", "card"]
    voice: str = Field(description="What the AI voice says in this scene. 1-2 short sentences.")
    on_screen: str = Field(description="Big text shown on screen. Max ~12 words.")
    question: Optional[str] = Field(default=None, description="Chat scenes only: the viewer's question.")
    answer: Optional[str] = Field(default=None, description="Chat scenes only: the bot's reply.")
    image: Optional[str] = Field(default=None, description="Optional path to your own image (fan art you made, licensed art).")


class ShortScript(BaseModel):
    title: str = Field(description="YouTube title, under 70 characters, ends with #shorts")
    description: str = Field(description="YouTube description, 2-3 lines")
    hashtags: list[str]
    scenes: list[Scene]


SYSTEM_PROMPT = """You write scripts for a YouTube Shorts fan channel about the manga {manga}.

Rules:
- Total spoken length about {seconds} seconds (roughly {words} words across all scenes).
- Scene 1 is type "chat": a viewer asks {bot_name} a question about the topic, and the bot gives a punchy one-line answer that hooks the viewer.
- Middle scenes are type "card": one idea per scene, fast, exciting, spoiler warnings where needed.
- The last scene is type "card" with on_screen exactly "{cta_on_screen}" and voice exactly "{cta_voice}".
- Write original commentary, rankings and analysis. Never quote long passages of the manga and never tell viewers to read it on unofficial or pirate sites.
- Plain English, short sentences, written to be spoken aloud.
- Leave the "image" field empty."""


def load_script(path: Path) -> ShortScript:
    return ShortScript.model_validate_json(Path(path).read_text(encoding="utf-8"))


def save_script(script: ShortScript, path: Path) -> None:
    Path(path).write_text(script.model_dump_json(indent=2, exclude_none=True) + "\n", encoding="utf-8")


def generate_script(topic: str, cfg: dict) -> ShortScript:
    """Ask Claude for a script about `topic`. Needs ANTHROPIC_API_KEY (or `ant auth login`)."""
    import anthropic

    seconds = cfg.get("target_seconds", 35)
    system = SYSTEM_PROMPT.format(
        manga=cfg["manga"],
        seconds=seconds,
        words=int(seconds * 2.5),
        bot_name=cfg.get("bot_name", "Manga Bot"),
        cta_on_screen=cfg["cta_on_screen"],
        cta_voice=cfg["cta_voice"],
    )
    client = anthropic.Anthropic()
    response = client.beta.messages.parse(
        model=cfg.get("ai_model", "claude-opus-5-5"),
        max_tokens=16000,
        output_config={"effort": "medium"},
        # If the main model declines, the API retries on a fallback model in the same call.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": f"Topic: {topic}"}],
        output_format=ShortScript,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"The AI did not return a script (stop_reason={response.stop_reason}). Try another topic.")
    return response.parsed_output
