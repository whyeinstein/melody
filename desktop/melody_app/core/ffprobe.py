"""ffprobe / ffmpeg 封装：读取标签、抽取内嵌封面。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess

CREATE_NO_WINDOW = 0x08000000


def _tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), name + ".exe")
    return candidate if os.path.exists(candidate) else None


FFPROBE = _tool("ffprobe")
FFMPEG = _tool("ffmpeg")


def _run(cmd: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
    )


def _tags_ci(tags: dict | None) -> dict[str, str]:
    if not tags:
        return {}
    return {str(k).lower(): str(v) for k, v in tags.items() if v is not None}


def _int(value, default=None):
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def probe(path: str) -> dict | None:
    """返回统一结构的标签信息；失败返回 None。"""
    if not FFPROBE:
        raise RuntimeError("未找到 ffprobe，请确认 ffmpeg 已加入 PATH")
    try:
        result = _run(
            [
                FFPROBE,
                "-v",
                "error",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ]
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    try:
        payload = json.loads(result.stdout.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None

    fmt = payload.get("format") or {}
    audio_stream = next(
        (s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), None
    )
    if audio_stream is None:
        return None

    # Ogg/Opus 等容器把标签放在音频流的 tags 里，format.tags 可能为空，两者合并。
    tags = _tags_ci(audio_stream.get("tags"))
    tags = {**tags, **_tags_ci(fmt.get("tags"))}

    track_raw = tags.get("track") or tags.get("tracknumber")
    track_no = None
    if track_raw:
        track_no = _int(str(track_raw).split("/")[0])

    year_raw = tags.get("date") or tags.get("year")
    year = None
    if year_raw:
        digits = "".join(ch for ch in str(year_raw)[:4] if ch.isdigit())
        year = _int(digits) if digits else None

    duration_ms = None
    duration = fmt.get("duration") or audio_stream.get("duration")
    if duration:
        duration_ms = int(float(duration) * 1000)

    return {
        "title": tags.get("title"),
        "artist": tags.get("artist") or tags.get("album_artist"),
        "album": tags.get("album"),
        "album_artist": tags.get("album_artist"),
        "genre": tags.get("genre"),
        "year": year,
        "track_no": track_no,
        "duration_ms": duration_ms,
        "bitrate": _int(fmt.get("bit_rate")),
        "sample_rate": _int(audio_stream.get("sample_rate")),
        "channels": _int(audio_stream.get("channels")),
        "codec": audio_stream.get("codec_name"),
        "has_picture": any(s.get("codec_type") == "video" for s in payload.get("streams", [])),
    }


def extract_cover(path: str, output_path: str) -> bool:
    """把内嵌封面导出为 jpg；没有封面返回 False。"""
    if not FFMPEG:
        return False
    try:
        result = _run(
            [FFMPEG, "-y", "-v", "error", "-i", path, "-an", "-map", "0:v:0", "-frames:v", "1", output_path]
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and os.path.exists(output_path)


def transcode_to_wav(source: str, target: str) -> bool:
    """把任意格式转成 WAV，供 QtMultimedia 稳定播放。"""
    if not FFMPEG:
        return False
    try:
        result = _run(
            [FFMPEG, "-y", "-v", "error", "-i", source, "-vn", "-ac", "2", "-ar", "44100",
             "-acodec", "pcm_s16le", target],
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and os.path.exists(target)
