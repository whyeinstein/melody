"""路径与配置。"""

from __future__ import annotations

import os

APP_NAME = "Melody"
APP_VERSION = "0.2.0"
APP_TAGLINE = "本地音乐库"


def app_data_dir() -> str:
    override = os.environ.get("MELODY_DATA_DIR")
    if override:
        os.makedirs(override, exist_ok=True)
        return override
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> str:
    return os.path.join(app_data_dir(), "melody.db")


def cache_dir() -> str:
    path = os.path.join(app_data_dir(), "cache")
    os.makedirs(path, exist_ok=True)
    return path


def covers_dir() -> str:
    path = os.path.join(app_data_dir(), "covers")
    os.makedirs(path, exist_ok=True)
    return path


def credentials_dir() -> str:
    """DPAPI 加密后的远程库凭据目录。"""
    path = os.path.join(app_data_dir(), "credentials")
    os.makedirs(path, exist_ok=True)
    return path


AUDIO_EXTENSIONS = {
    ".mp3",
    ".flac",
    ".wav",
    ".ogg",
    ".oga",
    ".opus",
    ".m4a",
    ".aac",
    ".wma",
    ".ape",
    ".wv",
    ".aiff",
    ".aif",
    ".m4b",
    ".dsf",
    ".dff",
}


def is_audio_file(name: str) -> bool:
    return os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS
