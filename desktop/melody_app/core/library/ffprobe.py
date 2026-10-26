"""ffprobe / ffmpeg 封装：读取标签、抽取内嵌封面、转码 WAV。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000


def _candidate_dirs() -> list[str]:
    """按优先级返回可能存放 ffmpeg/ffprobe 的目录。

    打包版把二进制放在 PyInstaller 的 ``_internal``（`sys._MEIPASS`）或 exe 同级；
    开发环境可用仓库内 ``vendor/ffmpeg/bin``，或通过 ``MELODY_FFMPEG_DIR`` 指定。
    """
    dirs: list[str] = []
    env_dir = os.environ.get("MELODY_FFMPEG_DIR")
    if env_dir:
        dirs.append(env_dir)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(str(meipass))
    if getattr(sys, "frozen", False):
        dirs.append(os.path.dirname(sys.executable))

    try:
        repo_root = Path(__file__).resolve().parents[4]
        dirs.append(str(repo_root / "vendor" / "ffmpeg" / "bin"))
    except IndexError:  # pragma: no cover - 极端打包布局
        pass

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    dirs.append(os.path.join(program_files, "ffmpeg", "bin"))
    return dirs


def _tool(name: str) -> str | None:
    executable = name + (".exe" if os.name == "nt" else "")
    for folder in _candidate_dirs():
        candidate = os.path.join(folder, executable)
        if os.path.isfile(candidate):
            return candidate
    found = shutil.which(name)
    if found:
        return found
    # 旧版本把 ffmpeg.exe 直接放在 Program Files 根目录。
    candidate = os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"), executable
    )
    return candidate if os.path.exists(candidate) else None


FFPROBE = _tool("ffprobe")
FFMPEG = _tool("ffmpeg")


def tool_source(path: str | None) -> str:
    """判断工具来源，供设置页展示：内置 / 自定义 / 系统。"""
    if not path:
        return "未找到"
    if getattr(sys, "frozen", False):
        return "内置"
    env_dir = os.environ.get("MELODY_FFMPEG_DIR")
    if env_dir and os.path.abspath(path).startswith(os.path.abspath(env_dir)):
        return "自定义目录"
    if "vendor" in os.path.normpath(path).split(os.sep):
        return "内置目录"
    return "系统 PATH"


def tool_status() -> dict:
    """供设置页展示的工具状态。"""
    return {
        "ffprobe": FFPROBE,
        "ffmpeg": FFMPEG,
        "ok": bool(FFPROBE and FFMPEG),
    }


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


def _track_number(raw: str | None) -> int | None:
    if not raw:
        return None
    return _int(str(raw).split("/")[0])


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

    track_no = _track_number(tags.get("track") or tags.get("tracknumber"))
    disc_no = _track_number(tags.get("disc") or tags.get("discnumber"))

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
        "disc_no": disc_no,
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
            [
                FFMPEG, "-y", "-v", "error", "-i", path, "-an",
                "-map", "0:v:0", "-frames:v", "1", output_path,
            ]
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
            [
                FFMPEG, "-y", "-v", "error", "-i", source, "-vn",
                "-ac", "2", "-ar", "44100", "-acodec", "pcm_s16le", target,
            ],
            timeout=300,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and os.path.exists(target)


def remux_to_file(source: str, target: str) -> bool:
    """远程 mp3/wav 先下载到本地缓存（不重编码），再交给 QMediaPlayer。"""
    if not FFMPEG:
        return False
    try:
        result = _run(
            [FFMPEG, "-y", "-v", "error", "-i", source, "-vn", "-c:a", "copy", target],
            timeout=600,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return result.returncode == 0 and os.path.exists(target)
