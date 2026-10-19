"""音乐库服务：来源管理、扫描调度、曲库工具（统计/失效文件/缓存）。"""

from __future__ import annotations

import os

from PyQt5.QtCore import QObject, pyqtSignal

from ...config import cache_dir, covers_dir
from ..models import LibraryStats, Source
from ..repositories.songs import SongsRepo
from ..repositories.sources import SourcesRepo
from ..sources import MusicSource, create_source_adapter
from .scanner import ScanWorker


def _dir_size(path: str) -> int:
    total = 0
    try:
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isfile(full):
                total += os.path.getsize(full)
    except OSError:
        return total
    return total


class LibraryService(QObject):
    scan_progress = pyqtSignal(int, int, str)  # 已处理, 总数, 当前文件
    scan_finished = pyqtSignal(dict)  # {"source_id", "added", "updated", "removed", "failed"}
    scan_failed = pyqtSignal(str)
    scan_state_changed = pyqtSignal(bool)
    sources_changed = pyqtSignal()
    library_changed = pyqtSignal()

    def __init__(self, songs: SongsRepo, sources: SourcesRepo) -> None:
        super().__init__()
        self._songs = songs
        self._sources = sources
        self._queue: list[Source] = []
        self._workers: list[ScanWorker] = []
        self._active = False

    # ------------------------------------------------------------------ 来源
    def sources(self, include_disabled: bool = True) -> list[Source]:
        return self._sources.list(include_disabled=include_disabled)

    def enabled_sources(self) -> list[Source]:
        return self._sources.list(include_disabled=False)

    def adapters(self) -> dict[int, MusicSource]:
        return {
            source.id: create_source_adapter(source, self._songs)
            for source in self._sources.list()
        }

    def add_local_folder(self, path: str) -> Source:
        if not os.path.isdir(path):
            raise ValueError(f"目录不存在：{path}")
        source = self._sources.add_local(path)
        self.sources_changed.emit()
        return source

    def add_remote_source(
        self,
        name: str,
        url: str,
        protocol: str = "webdav",
        config: dict | None = None,
    ) -> Source:
        source = self._sources.add_remote(name, url, config=config, protocol=protocol)
        self.sources_changed.emit()
        return source

    def set_source_enabled(self, source_id: int, enabled: bool) -> None:
        self._sources.set_enabled(source_id, enabled)
        self.sources_changed.emit()
        self.library_changed.emit()

    def remove_source(self, source_id: int) -> None:
        self._sources.remove(source_id)
        self.sources_changed.emit()
        self.library_changed.emit()

    # ------------------------------------------------------------------ 扫描
    @property
    def is_scanning(self) -> bool:
        return self._active

    def start_scan(self, source_ids: list[int] | None = None) -> bool:
        if self._active:
            return False
        candidates = [
            source
            for source in self._sources.list(include_disabled=False)
            if source.kind == "local" and (source_ids is None or source.id in source_ids)
        ]
        if not candidates:
            self.scan_failed.emit("没有可扫描的本地来源")
            return False
        self._queue = candidates
        self._active = True
        self.scan_state_changed.emit(True)
        self._start_next()
        return True

    def _start_next(self) -> None:
        if not self._queue:
            self._active = False
            self.scan_state_changed.emit(False)
            self.library_changed.emit()
            return
        source = self._queue.pop(0)
        worker = ScanWorker(self._songs.database_path, source)
        worker.progress.connect(self.scan_progress)
        worker.finished_scan.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda: self._forget_worker(worker))
        self._workers.append(worker)
        worker.start()

    def _forget_worker(self, worker: ScanWorker) -> None:
        if worker in self._workers:
            self._workers.remove(worker)

    def _on_finished(self, stats: dict) -> None:
        self.scan_finished.emit(stats)
        self._start_next()

    def _on_failed(self, message: str) -> None:
        self.scan_failed.emit(message)
        self._start_next()

    # ------------------------------------------------------------------ 工具
    def stats(self) -> LibraryStats:
        return self._songs.stats()

    def check_integrity(self) -> dict:
        """检查文件是否仍然存在，更新 songs.missing；返回统计。"""
        songs = self._songs.query(include_missing=True)
        missing_ids: list[int] = []
        restored_ids: list[int] = []
        missing_total = 0
        for song in songs:
            exists = os.path.exists(song.path)
            if not exists:
                missing_total += 1
                if not song.missing:
                    missing_ids.append(song.id)
            elif song.missing:
                restored_ids.append(song.id)
        self._songs.set_missing(missing_ids, True)
        self._songs.set_missing(restored_ids, False)
        result = {
            "checked": len(songs),
            "missing": missing_total,
            "restored": len(restored_ids),
        }
        self.library_changed.emit()
        return result

    def prune_missing(self) -> int:
        removed = self._songs.delete_missing()
        self.library_changed.emit()
        return removed

    def cache_status(self) -> dict:
        return {
            "transcode_bytes": _dir_size(cache_dir()),
            "cover_bytes": _dir_size(covers_dir()),
        }

    def clear_transcode_cache(self) -> int:
        freed = 0
        folder = cache_dir()
        try:
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isfile(full):
                    freed += os.path.getsize(full)
                    os.remove(full)
        except OSError:
            pass
        return freed

    def clear_cover_cache(self) -> int:
        freed = 0
        folder = covers_dir()
        try:
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if os.path.isfile(full):
                    freed += os.path.getsize(full)
                    os.remove(full)
        except OSError:
            pass
        # 封面文件已删除，清掉数据库里的引用，避免指向不存在的文件。
        self._songs.conn.execute("UPDATE songs SET cover_path = NULL")
        self._songs.commit()
        self.library_changed.emit()
        return freed
