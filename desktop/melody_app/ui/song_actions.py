"""歌曲右键菜单：播放、加入歌单、收藏、定位文件。"""

from __future__ import annotations

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMenu

from ..core.models import Song
from .widgets.common import reveal_in_explorer


def show_song_context_menu(
    parent,
    ctx,
    song: Song,
    global_pos,
    on_play=None,
) -> None:
    menu = QMenu(parent)

    if on_play is not None:
        play_action = menu.addAction("播放")
        play_action.triggered.connect(lambda: on_play(song))
        menu.addSeparator()

    add_menu = menu.addMenu("添加到歌单")
    playlists = ctx.playlists.list()
    if playlists:
        for playlist in playlists:
            action = add_menu.addAction(playlist.name)
            action.triggered.connect(
                lambda _checked=False, pid=playlist.id, name=playlist.name: _add_to_playlist(
                    ctx, pid, name, song
                )
            )
    else:
        empty_action = add_menu.addAction("（暂无歌单，请在「歌单」页新建）")
        empty_action.setEnabled(False)

    favorite_action = menu.addAction("取消收藏" if song.favorite else "收藏")
    favorite_action.triggered.connect(lambda: _toggle_favorite(ctx, song))

    menu.addSeparator()
    reveal_action = menu.addAction("在资源管理器中显示")
    reveal_action.triggered.connect(lambda: reveal_in_explorer(song.path))

    menu.addSeparator()
    info_action = menu.addAction(
        f"{song.format_text or '未知格式'} · {song.duration_text}"
    )
    info_action.setEnabled(False)
    info_font = QFont()
    info_font.setPointSize(max(8, info_font.pointSize() - 1))
    info_action.setFont(info_font)

    chosen = menu.exec_(global_pos)
    if chosen is None and menu.parent() is not None:
        menu.deleteLater()


def _add_to_playlist(ctx, playlist_id: int, name: str, song: Song) -> None:
    added = ctx.playlists.add_songs(playlist_id, [song.id])
    if added:
        ctx.toast(f"已添加到歌单「{name}」")
    else:
        ctx.toast(f"「{name}」中已有这首歌")
    ctx.playlists_changed.emit()


def _toggle_favorite(ctx, song: Song) -> None:
    favorite = not song.favorite
    ctx.songs.set_favorite(song.id, favorite)
    ctx.toast("已收藏" if favorite else "已取消收藏")
    ctx.favorite_changed.emit(song.id, favorite)
