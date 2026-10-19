"""Windows DPAPI 凭据存储：密码加密后落盘，仅当前 Windows 用户可解密。

不把密码写进 SQLite / 配置文件，也不写日志。
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes

CRYPTPROTECT_UI_FORBIDDEN = 0x1


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _blob(data: bytes) -> _DataBlob:
    if not data:
        return _DataBlob(0, ctypes.cast(ctypes.create_string_buffer(0), ctypes.POINTER(ctypes.c_char)))
    buffer = ctypes.create_string_buffer(data, len(data))
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))


def _dpapi(data: bytes, protect: bool) -> bytes:
    if os.name != "nt":
        raise RuntimeError("凭据加密依赖 Windows DPAPI，当前系统不支持")

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    blob_pointer = ctypes.POINTER(_DataBlob)

    if protect:
        func = crypt32.CryptProtectData
    else:
        func = crypt32.CryptUnprotectData
    func.argtypes = [
        blob_pointer,  # pDataIn
        ctypes.c_void_p,  # ppszDataDescr / description
        ctypes.c_void_p,  # pOptionalEntropy
        ctypes.c_void_p,  # pvReserved
        ctypes.c_void_p,  # pPromptStruct
        wintypes.DWORD,  # dwFlags
        blob_pointer,  # pDataOut
    ]
    func.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    input_blob = _blob(data)
    output_blob = _DataBlob()
    ok = func(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not ok:
        raise OSError("DPAPI 加解密失败")
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if output_blob.pbData:
            kernel32.LocalFree(output_blob.pbData)


def protect(secret: str) -> bytes:
    return _dpapi(secret.encode("utf-8"), protect=True)


def unprotect(blob: bytes) -> str:
    return _dpapi(blob, protect=False).decode("utf-8")


class CredentialStore:
    """按来源 id 保存密码：``<数据目录>/credentials/source-<id>.bin``。"""

    def __init__(self, directory: str) -> None:
        self._directory = directory

    @property
    def directory(self) -> str:
        return self._directory

    def _path(self, source_id: int) -> str:
        return os.path.join(self._directory, f"source-{int(source_id)}.bin")

    def save(self, source_id: int, password: str) -> None:
        """保存密码；传空字符串等同于删除。"""
        if not password:
            self.delete(source_id)
            return
        os.makedirs(self._directory, exist_ok=True)
        with open(self._path(source_id), "wb") as handle:
            handle.write(protect(password))

    def load(self, source_id: int) -> str | None:
        path = self._path(source_id)
        if not os.path.isfile(path):
            return None
        with open(path, "rb") as handle:
            return unprotect(handle.read())

    def has(self, source_id: int) -> bool:
        return os.path.isfile(self._path(source_id))

    def delete(self, source_id: int) -> None:
        try:
            os.remove(self._path(source_id))
        except FileNotFoundError:
            pass
