"""后台扫描：遍历来源目录 → ffprobe 解析 → 写入数据库 → 清理消失文件。

线程模型：
- 扫描线程（本 QThread）持有**独立的 SQLite 连接**，避免与界面线程共用同一连接；
- ffprobe 用 4 个线程并发，但子线程里**不访问数据库**（扫描前已把已有文件状态读进内存字典）；
- 数据库写入只在扫描线程内串行执行。
"""

from __future__ import annotations

import hashlib
import os
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QThread, pyqtSignal

from ...config import covers_dir, is_audio_file
from ..db import Database
from ..models import Source
from ..repositories.songs import SongsRepo
from . import ffprobe

SKIPPED_DIRS = {"$recycle.bin", "system volume information", "node_modules", ".git"}


class ScanWorker(QThread):
    progress = pyqtSignal(int, int, str)  # 已处理, 总数, 当前文件
    finished_scan = pyqtSignal(dict)  # {"added", "updated", "removed", "failed", "source_id"}
    failed = pyqtSignal(str)

    def __init__(self, db_path: str, source: Source) -> None:
        super().__init__()
        self._db_path = db_path
        self._source = source

    # ------------------------------------------------------------------ 遍历
    def _collect(self) -> list[str]:
        root = str(self._source.path or "")
        files: list[str] = []
        for current, dirs, names in os.walk(root):
            dirs[:] = [
                d for d in dirs if not d.startswith(".") and d.lower() not in SKIPPED_DIRS
            ]
            for name in names:
                if is_audio_file(name):
                    files.append(os.path.join(current, name))
        return files

    def run(self) -> None:  # noqa: D401 - QThread 入口
        if self._source.kind != "local":
            self.failed.emit("远程库暂不支持扫描")
            return
        root = str(self._source.path or "")
        if not os.path.isdir(root):
            self.failed.emit(f"目录不存在：{root}")
            return
        try:
            files = self._collect()
        except OSError as error:
            self.failed.emit(str(error))
            return

        database = Database(self._db_path)
        songs = SongsRepo(database)
        try:
            stats = self._scan_files(songs, files)
        finally:
            database.close()
        self.finished_scan.emit(stats)

    def _scan_files(self, songs: SongsRepo, files: list[str]) -> dict:
        total = len(files)
        stats = {
            "source_id": self._source.id,
            "added": 0,
            "updated": 0,
            "removed": 0,
            "failed": 0,
        }
        seen: list[str] = []
        covers = covers_dir()
        existing = songs.find_files_for_source(self._source.id)

        def process(path: str) -> dict | None:
            try:
                stat = os.stat(path)
            except OSError:
                return None
            mtime = int(stat.st_mtime * 1000)
            known = existing.get(path.lower())
            if known and known[1] == stat.st_size and known[2] == mtime:
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
                "source_id": self._source.id,
                "title": title,
                "artist": info.get("artist"),
                "album": info.get("album"),
                "album_artist": info.get("album_artist"),
                "genre": info.get("genre"),
                "year": info.get("year"),
                "track_no": info.get("track_no"),
                "disc_no": info.get("disc_no"),
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
                is_new = result["path"].lower() not in existing
                songs.upsert_scan(result)
                stats["added" if is_new else "updated"] += 1

        songs.commit()
        stats["removed"] = songs.remove_missing_source_files(self._source.id, seen)
        songs.commit()
        return stats
