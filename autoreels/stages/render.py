"""Stage 5 — render the storyboard to a vertical MP4."""

from __future__ import annotations

import os

from .. import captions, ffmpeg
from ..config import Config
from ..models import Storyboard
from . import storyboard as storyboard_stage


def render(board: Storyboard, config: Config, run_dir: str, dest: str) -> str:
    binary = ffmpeg.require(config.ffmpeg)
    work = os.path.join(run_dir, f"work-{board.variant}")
    os.makedirs(work, exist_ok=True)

    clips: list[str] = []
    for shot in board.shots:
        clip = os.path.join(work, f"clip{shot.index:02d}.mp4")
        ffmpeg.render_clip(
            binary,
            shot.image_path,
            clip,
            duration=shot.duration,
            motion=shot.motion,
            width=board.width,
            height=board.height,
            fps=board.fps,
        )
        shot.clip_path = clip
        clips.append(clip)

    silent = ffmpeg.concat_clips(binary, clips, os.path.join(work, "silent.mp4"), work)

    subtitle_file = captions.build(
        board.shots,
        os.path.join(work, "captions.ass"),
        width=board.width,
        height=board.height,
        font=config.caption_font,
    )

    duration = board.duration()
    voice = ffmpeg.build_voice_track(
        binary,
        storyboard_stage.audio_segments(board),
        os.path.join(work, "voice.m4a"),
        duration,
    )
    board.audio_path = voice or ""

    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    return ffmpeg.finalise(
        binary,
        video=silent,
        subtitles=subtitle_file,
        dest=dest,
        voice=voice,
        music=board.music_path,
        music_volume=config.music_volume,
        duration=duration,
    )
