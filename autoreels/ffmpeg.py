"""FFmpeg wrappers.

Everything visual happens here. Kept separate from the render stage so the
motion maths can be read and tested on its own.
"""

from __future__ import annotations

import os
import shutil
import subprocess


class FFmpegMissing(RuntimeError):
    pass


class FFmpegFailed(RuntimeError):
    def __init__(self, args: list[str], stderr: str):
        tail = "\n".join(stderr.strip().splitlines()[-15:])
        super().__init__(f"ffmpeg failed:\n  {' '.join(args[:6])} ...\n{tail}")


def require(binary: str = "ffmpeg") -> str:
    path = shutil.which(binary)
    if not path:
        raise FFmpegMissing(
            f"{binary!r} not found on PATH. autoreels renders with FFmpeg.\n"
            "  macOS:  brew install ffmpeg\n"
            "  Debian: sudo apt install ffmpeg\n"
            "  Windows: winget install Gyan.FFmpeg\n"
            "Everything up to the render stage works without it — "
            "use `autoreels script` to get the script and storyboard only."
        )
    return path


def run(args: list[str]) -> None:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        raise FFmpegFailed(args, result.stderr)


def escape_filter_path(path: str) -> str:
    """Escape a path for use inside a filtergraph argument."""
    return os.path.abspath(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def kenburns_filter(
    motion: str,
    frames: int,
    width: int,
    height: int,
    fps: int,
    *,
    supersample: int = 2,
) -> str:
    """Build the scale -> crop -> zoompan chain for one still image.

    The image is scaled well above the output size before zoompan runs; without
    that headroom zoompan quantises its crop to whole source pixels and the
    motion visibly stutters.
    """
    big_w, big_h = width * supersample, height * supersample
    frames = max(frames, 2)

    centre_x = "iw/2-(iw/zoom/2)"
    centre_y = "ih/2-(ih/zoom/2)"

    if motion == "zoom_in":
        zoom, x, y = f"min(1+0.0016*on,1.18)", centre_x, centre_y
    elif motion == "zoom_out":
        zoom, x, y = f"max(1.18-0.0016*on,1.0)", centre_x, centre_y
    elif motion == "pan_right":
        zoom, x, y = "1.14", f"(iw-iw/zoom)*on/{frames}", centre_y
    elif motion == "pan_left":
        zoom, x, y = "1.14", f"(iw-iw/zoom)*(1-on/{frames})", centre_y
    elif motion == "pan_up":
        zoom, x, y = "1.14", centre_x, f"(ih-ih/zoom)*(1-on/{frames})"
    elif motion == "pan_down":
        zoom, x, y = "1.14", centre_x, f"(ih-ih/zoom)*on/{frames}"
    else:  # static — a hair of drift so the frame never looks frozen
        zoom, x, y = "min(1+0.0003*on,1.03)", centre_x, centre_y

    return (
        f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase,"
        f"crop={big_w}:{big_h},"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={fps},"
        f"setsar=1,format=yuv420p"
    )


def render_clip(
    ffmpeg: str,
    image: str,
    dest: str,
    *,
    duration: float,
    motion: str,
    width: int,
    height: int,
    fps: int,
) -> str:
    frames = int(round(duration * fps))
    run([
        ffmpeg, "-y", "-loglevel", "error",
        "-loop", "1", "-framerate", str(fps), "-t", f"{duration:.3f}", "-i", image,
        "-vf", kenburns_filter(motion, frames, width, height, fps),
        "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", str(fps), "-an",
        dest,
    ])
    return dest


def concat_clips(ffmpeg: str, clips: list[str], dest: str, work_dir: str) -> str:
    listing = os.path.join(work_dir, "clips.txt")
    with open(listing, "w", encoding="utf-8") as handle:
        for clip in clips:
            handle.write(f"file '{os.path.abspath(clip)}'\n")
    run([
        ffmpeg, "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", listing,
        "-c", "copy", dest,
    ])
    return dest


def build_voice_track(
    ffmpeg: str,
    segments: list[tuple[str, float, float]],
    dest: str,
    total_duration: float,
) -> str | None:
    """Place each narration file at its beat's start time on one track."""
    segments = [(p, s, d) for p, s, d in segments if p and os.path.exists(p)]
    if not segments:
        return None

    args = [ffmpeg, "-y", "-loglevel", "error"]
    for path, _, _ in segments:
        args += ["-i", path]

    chains = []
    labels = []
    for index, (_, start, _) in enumerate(segments):
        label = f"s{index}"
        chains.append(
            f"[{index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=mono,"
            f"adelay={int(start * 1000)}[{label}]"
        )
        labels.append(f"[{label}]")

    chains.append(
        "".join(labels)
        + f"amix=inputs={len(segments)}:normalize=0:dropout_transition=0,"
        + f"apad,atrim=0:{total_duration:.3f},asetpts=N/SR/TB[out]"
    )

    args += [
        "-filter_complex", ";".join(chains),
        "-map", "[out]", "-c:a", "aac", "-b:a", "192k", dest,
    ]
    run(args)
    return dest


def finalise(
    ffmpeg: str,
    *,
    video: str,
    subtitles: str,
    dest: str,
    voice: str | None,
    music: str,
    music_volume: float,
    duration: float,
) -> str:
    """Burn captions, mix voice and music, write the deliverable."""
    args = [ffmpeg, "-y", "-loglevel", "error", "-i", video]
    audio_inputs: list[str] = []

    if voice:
        args += ["-i", voice]
        audio_inputs.append("voice")
    if music and os.path.exists(music):
        args += ["-stream_loop", "-1", "-i", music]
        audio_inputs.append("music")

    chains = [f"[0:v]subtitles=filename='{escape_filter_path(subtitles)}'[v]"]

    if audio_inputs == ["voice"]:
        chains.append(f"[1:a]atrim=0:{duration:.3f},asetpts=N/SR/TB[a]")
    elif audio_inputs == ["music"]:
        chains.append(
            f"[1:a]volume={music_volume},afade=t=out:st={max(duration - 1.0, 0):.3f}:d=1,"
            f"atrim=0:{duration:.3f},asetpts=N/SR/TB[a]"
        )
    elif audio_inputs == ["voice", "music"]:
        chains.append(f"[2:a]volume={music_volume},afade=t=out:st={max(duration - 1.0, 0):.3f}:d=1[m]")
        chains.append(
            f"[1:a][m]amix=inputs=2:normalize=0:dropout_transition=0,"
            f"atrim=0:{duration:.3f},asetpts=N/SR/TB[a]"
        )

    args += ["-filter_complex", ";".join(chains), "-map", "[v]"]
    if audio_inputs:
        args += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    else:
        args += ["-an"]
    args += [
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-t", f"{duration:.3f}", dest,
    ]
    run(args)
    return dest
