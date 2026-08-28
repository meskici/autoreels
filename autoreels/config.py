"""Environment-driven configuration.

Nothing here is required to run the pipeline: every provider has a keyless
fallback so `autoreels make <handle>` produces a video out of the box.
Keys only upgrade quality (real LLM scripting, real TTS voice).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines from .env without overriding real env vars."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


@dataclass
class Config:
    # --- Shopify -----------------------------------------------------------
    shopify_store: str = ""          # e.g. kapyacraft.myshopify.com
    shopify_token: str = ""          # Admin API access token (shpat_...)
    shopify_api_version: str = "2025-01"

    # --- Scriptwriting -----------------------------------------------------
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    model: str = "claude-opus-5"

    # --- Voiceover ---------------------------------------------------------
    tts_provider: str = "auto"       # auto | elevenlabs | openai | none
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    elevenlabs_model: str = "eleven_multilingual_v2"
    openai_api_key: str = ""
    openai_tts_model: str = "gpt-4o-mini-tts"
    openai_tts_voice: str = "alloy"

    # --- Render ------------------------------------------------------------
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    width: int = 1080
    height: int = 1920
    fps: int = 30
    caption_font: str = "DejaVu Sans"
    music_volume: float = 0.12

    # --- Paths -------------------------------------------------------------
    runs_dir: str = "runs"
    brand: str = "kapya"
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, dotenv: str = ".env") -> "Config":
        _load_dotenv(dotenv)
        env = os.environ.get
        return cls(
            shopify_store=env("SHOPIFY_STORE", ""),
            shopify_token=env("SHOPIFY_ADMIN_TOKEN", ""),
            shopify_api_version=env("SHOPIFY_API_VERSION", "2025-01"),
            anthropic_api_key=env("ANTHROPIC_API_KEY", ""),
            anthropic_base_url=env("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/"),
            model=env("AUTOREELS_MODEL", "claude-opus-5"),
            tts_provider=env("AUTOREELS_TTS", "auto"),
            elevenlabs_api_key=env("ELEVENLABS_API_KEY", ""),
            elevenlabs_voice_id=env("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),
            elevenlabs_model=env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            openai_api_key=env("OPENAI_API_KEY", ""),
            openai_tts_model=env("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            openai_tts_voice=env("OPENAI_TTS_VOICE", "alloy"),
            ffmpeg=env("FFMPEG_BIN", "ffmpeg"),
            ffprobe=env("FFPROBE_BIN", "ffprobe"),
            width=int(env("AUTOREELS_WIDTH", "1080")),
            height=int(env("AUTOREELS_HEIGHT", "1920")),
            fps=int(env("AUTOREELS_FPS", "30")),
            caption_font=env("AUTOREELS_FONT", "DejaVu Sans"),
            music_volume=float(env("AUTOREELS_MUSIC_VOLUME", "0.12")),
            runs_dir=env("AUTOREELS_RUNS_DIR", "runs"),
            brand=env("AUTOREELS_BRAND", "kapya"),
        )

    def resolved_tts(self) -> str:
        if self.tts_provider != "auto":
            return self.tts_provider
        if self.elevenlabs_api_key:
            return "elevenlabs"
        if self.openai_api_key:
            return "openai"
        return "none"
