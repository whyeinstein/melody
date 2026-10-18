"""播放队列：展示顺序（items）与播放顺序（order）分离，支持随机 / 循环。"""

from __future__ import annotations

import random
from enum import Enum

from PyQt5.QtCore import QObject, pyqtSignal

from ..models import Song


class RepeatMode(str, Enum):
    OFF = "off"  # 播完列表即停
    ALL = "all"  # 列表循环
    ONE = "one"  # 单曲循环

    @property
    def label(self) -> str:
        return {"off": "顺序播放", "all": "列表循环", "one": "单曲循环"}[self.value]

    @classmethod
    def from_value(cls, value: str) -> "RepeatMode":
        try:
            return cls(value)
        except ValueError:
            return cls.OFF


class PlayQueue(QObject):
    changed = pyqtSignal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[Song] = []
        self._order: list[int] = []  # 播放顺序：items 的下标序列
        self._position = -1
        self._shuffle = False
        self._repeat = RepeatMode.OFF

    # ------------------------------------------------------------------ 读取
    @property
    def items(self) -> list[Song]:
        return list(self._items)

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    def __len__(self) -> int:
        return len(self._items)

    @property
    def current_index(self) -> int:
        """当前曲目在 items 中的下标（无则 -1）。"""
        if 0 <= self._position < len(self._order):
            return self._order[self._position]
        return -1

    @property
    def current(self) -> Song | None:
        index = self.current_index
        return self._items[index] if 0 <= index < len(self._items) else None

    def ordered_items(self) -> list[Song]:
        return [self._items[i] for i in self._order if 0 <= i < len(self._items)]

    def index_of_song(self, song_id: int) -> int:
        for index, song in enumerate(self._items):
            if song.id == song_id:
                return index
        return -1

    # ------------------------------------------------------------------ 设置
    def set_queue(self, songs: list[Song], start: int = 0) -> None:
        self._items = list(songs)
        size = len(self._items)
        start = min(max(0, start), size - 1) if size else 0
        self._order = list(range(size))
        if size and self._shuffle:
            rest = [i for i in self._order if i != start]
            random.shuffle(rest)
            self._order = [start] + rest
        self._position = self._order.index(start) if size else -1
        self.changed.emit()

    def set_shuffle(self, shuffle: bool) -> None:
        shuffle = bool(shuffle)
        if shuffle == self._shuffle:
            return
        self._shuffle = shuffle
        current = self.current_index
        self._rebuild_order(current)
        self.changed.emit()

    def set_repeat(self, mode: RepeatMode) -> None:
        self._repeat = mode
        self.changed.emit()

    def cycle_repeat(self) -> RepeatMode:
        order = [RepeatMode.OFF, RepeatMode.ALL, RepeatMode.ONE]
        self._repeat = order[(order.index(self._repeat) + 1) % len(order)]
        self.changed.emit()
        return self._repeat

    def _rebuild_order(self, keep_index: int) -> None:
        self._order = list(range(len(self._items)))
        if self._shuffle and keep_index >= 0:
            rest = [i for i in self._order if i != keep_index]
            random.shuffle(rest)
            self._order = [keep_index] + rest
        self._position = self._order.index(keep_index) if keep_index >= 0 else -1

    # ------------------------------------------------------------------ 跳转
    def jump_to(self, item_index: int) -> Song | None:
        if not (0 <= item_index < len(self._items)):
            return None
        try:
            self._position = self._order.index(item_index)
        except ValueError:
            self._position = 0
        self.changed.emit()
        return self.current

    def jump_to_song(self, song_id: int) -> Song | None:
        index = self.index_of_song(song_id)
        return self.jump_to(index) if index >= 0 else None

    def next(self, auto: bool = False) -> Song | None:
        if not self._order:
            return None
        if auto and self._repeat is RepeatMode.ONE:
            return self.current
        position = self._position + 1
        if position >= len(self._order):
            if self._repeat is RepeatMode.ALL or not auto:
                position = 0
            else:
                return None
        self._position = position
        self.changed.emit()
        return self.current

    def previous(self) -> Song | None:
        if not self._order:
            return None
        position = self._position - 1
        if position < 0:
            position = len(self._order) - 1
        self._position = position
        self.changed.emit()
        return self.current

    # ------------------------------------------------------------------ 增删
    def append(self, songs: list[Song]) -> int:
        existing = {song.id for song in self._items}
        fresh = [song for song in songs if song.id not in existing]
        if not fresh:
            return 0
        current_index = self.current_index
        start = len(self._items)
        self._items.extend(fresh)
        appended = list(range(start, len(self._items)))
        if self._shuffle:
            random.shuffle(appended)
            self._order.extend(appended)
        else:
            # 顺序播放时让 order 与 items 保持同构。
            self._order = list(range(len(self._items)))
            self._position = current_index if current_index >= 0 else -1
        self.changed.emit()
        return len(fresh)

    def remove_at(self, item_index: int) -> None:
        if not (0 <= item_index < len(self._items)):
            return
        current_index = self.current_index
        removed_current = item_index == current_index
        self._items.pop(item_index)
        new_order: list[int] = []
        for index in self._order:
            if index == item_index:
                continue
            new_order.append(index - 1 if index > item_index else index)
        self._order = new_order
        if removed_current:
            self._position = min(max(self._position, 0), len(self._order) - 1)
        else:
            new_current = current_index - 1 if current_index > item_index else current_index
            self._position = self._order.index(new_current) if new_current >= 0 else -1
        self.changed.emit()

    def clear(self) -> None:
        self._items = []
        self._order = []
        self._position = -1
        self.changed.emit()
