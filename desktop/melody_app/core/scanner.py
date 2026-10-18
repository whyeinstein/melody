"""后台扫描：遍历目录 → ffprobe 解析 → 写入数据库 → 清理消失文件。"""

from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QThread, pyqtSignal

from ..config import covers_dir, is_audio_file
from . import ffprobe
from .db import Database

SKIPPED_DIRS = {"$recycle.bin", "system volume information", "node_modules", ".git"}


class ScanWorker(QThread):
    progress = pyqtSignal(int, int, str)  # 已处理, 总数, 当前文件
    finished_scan = pyqtSignal(dict)  # {"added", "updated", "removed", "failed"}
    failed = pyqtSignal(str)

    def __init__(self, database: Database, folder_id: int, root: str) -> None:
        super().__init__()
        self._db = database
        self._folder_id = folder_id
        self._root = root

    def _collect(self) -> list[str]:
        files: list[str] = []
        for current, dirs, names in os.walk(self._root):
            dirs[:] = [
                d for d in dirs if not d.startswith(".") and d.lower() not in SKIPPED_DIRS
            ]
            for name in names:
                if is_audio_file(name):
                    files.append(os.path.join(current, name))
        return files

    def run(self) -> None:  # noqa: D401 - QThread 入口
        try:
            files = self._collect()
        except OSError as error:
            self.failed.emit(str(error))
            return

        total = len(files)
        stats = {"added": 0, "updated": 0, "removed": 0, "failed": 0}
        seen: list[str] = []
        covers = covers_dir()

        def process(path: str) -> dict | None:
            try:
                stat = os.stat(path)
            except OSError:
                return None
            existing = self._db.find_song_file(path)
            mtime = int(stat.st_mtime * 1000)
            if existing and existing[1] == stat.st_size and existing[2] == mtime:
                return {"path": path, "unchanged": True}
            try:
                info = ffprobe.probe(path)
            except Exception:  # noqa: BLE001 - 单个文件失败不影响整体
                info = None
            if info is None:
                return {"path": path, "failed": True}
            title = info.get("title") or os.path.splitext(os.path.basename(path))[0]
            cover_path = None
            if info.get("has_picture"):
                digest = hashlib.sha1(f"{path}:{mtime}".encode("utf-8")).hexdigest()[:16]
                candidate = os.path.join(covers, digest + ".jpg")
                if os.path.exists(candidate) or ffprobe.extract_cover(path, candidate):
                    cover_path = candidate
            return {
                "path": path,
                "size": stat.st_size,
                "mtime_ms": mtime,
                "folder_id": self._folder_id,
                "title": title,
                "artist": info.get("artist"),
                "album": info.get("album"),
                "album_artist": info.get("album_artist"),
                "genre": info.get("genre"),
                "year": info.get("year"),
                "track_no": info.get("track_no"),
                "duration_ms": info.get("duration_ms"),
                "bitrate": info.get("bitrate"),
                "sample_rate": info.get("sample_rate"),
                "channels": info.get("channels"),
                "format": os.path.splitext(path)[1].lstrip(".").lower(),
                "cover_path": cover_path,
            }

        processed = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            for result in pool.map(process, files):
                processed += 1
                if processed % 25 == 0 or processed == total:
                    self.progress.emit(processed, total, result["path"] if result else "")
                if result is None:
                    stats["failed"] += 1
                    continue
                seen.append(result["path"])
                if result.get("unchanged"):
                    continue
                if result.get("failed"):
                    stats["failed"] += 1
                    continue
                is_new = self._db.find_song_file(result["path"]) is None
                self._db.upsert_song(result)
                stats["added" if is_new else "updated"] += 1

        self._db.commit()
        stats["removed"] = self._db.remove_missing(self._folder_id, seen)
        self.finished_scan.emit(stats)
