"""WebDAV 远程扫描：列目录 → 通过本地代理用 ffprobe 读标签 → 写入 songs。"""

from __future__ import annotations

import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtCore import QThread, pyqtSignal

from ...config import covers_dir
from ..db import Database
from ..models import Source
from ..repositories.songs import SongsRepo
from ..sources.webdav_client import WebDavClient, WebDavConfig, WebDavError
from ..sources.webdav_proxy import WebDavProxy
from . import ffprobe


class RemoteScanWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished_scan = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(
        self,
        db_path: str,
        source: Source,
        password: str = "",
        max_workers: int = 4,
    ) -> None:
        super().__init__()
        self._db_path = db_path
        self._source = source
        self._password = password
        self._max_workers = max(1, int(max_workers))

    # ------------------------------------------------------------------ 入口
    def run(self) -> None:  # noqa: D401 - QThread 入口
        config = self._source.config or {}
        client = WebDavClient(
            WebDavConfig(
                base_url=self._source.path or "",
                username=str(config.get("username", "")),
                password=self._password,
                verify_tls=bool(config.get("verify_tls", True)),
            )
        )
        ok, message = client.test_connection()
        if not ok:
            self.failed.emit(message)
            return
        try:
            entries = client.list_tree()
        except WebDavError as error:
            self.failed.emit(str(error))
            return
        except Exception as error:  # noqa: BLE001 - 网络异常统一提示
            self.failed.emit(f"列目录失败：{error}")
            return

        database = Database(self._db_path)
        songs = SongsRepo(database)
        proxy = WebDavProxy(client)
        try:
            proxy.start()
            stats = self._scan(songs, entries, proxy)
        except Exception as error:  # noqa: BLE001 - 扫描失败不影响已有库
            self.failed.emit(f"扫描远程库失败：{error}")
            return
        finally:
            proxy.stop()
            database.close()
        self.finished_scan.emit(stats)

    # ------------------------------------------------------------------ 扫描
    def _scan(
        self,
        songs: SongsRepo,
        entries: list,
        proxy: WebDavProxy,
    ) -> dict:
        stats = {
            "source_id": self._source.id,
            "added": 0,
            "updated": 0,
            "removed": 0,
            "failed": 0,
        }
        existing = songs.find_files_for_source(self._source.id)
        covers = covers_dir()
        total = len(entries)

        def process(entry) -> dict | None:
            known = existing.get(entry.path.lower())
            if known and known[1] == entry.size:
                if entry.modified_ms == 0 or known[2] == entry.modified_ms:
                    return {"path": entry.path, "unchanged": True}
            url = proxy.url_for(entry.path)
            try:
                info = ffprobe.probe(url)
            except Exception:  # noqa: BLE001 - 单个文件失败不影响整体
                info = None
            if info is None:
                return {"path": entry.path, "failed": True}

            title = info.get("title") or os.path.splitext(os.path.basename(entry.path))[0]
            cover_path = None
            if info.get("has_picture"):
                digest = hashlib.sha1(
                    f"{self._source.id}:{entry.path}:{entry.modified_ms}".encode("utf-8")
                ).hexdigest()[:16]
                candidate = os.path.join(covers, "remote-" + digest + ".jpg")
                if os.path.exists(candidate) or ffprobe.extract_cover(url, candidate):
                    cover_path = candidate

            extension = os.path.splitext(entry.path)[1].lstrip(".").lower()
            return {
                "path": entry.path,
                "size": entry.size,
                "mtime_ms": entry.modified_ms or int(time.time() * 1000),
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
                "format": extension,
                "cover_path": cover_path,
            }

        processed = 0
        seen: list[str] = []
        if total:
            with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
                for result in pool.map(process, entries):
                    processed += 1
                    if processed % 10 == 0 or processed == total:
                        self.progress.emit(
                            processed, total, result["path"] if result else ""
                        )
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
