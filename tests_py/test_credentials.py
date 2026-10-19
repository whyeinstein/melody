"""Windows DPAPI 凭据存储测试（仅 Windows）。"""

from __future__ import annotations

import os
import shutil
import sys
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop"))

from melody_app.core.credentials import CredentialStore, protect, unprotect  # noqa: E402


def make_temp_dir(prefix: str = "cred") -> str:
    base = os.path.join(os.getcwd(), ".cache", "tests")
    os.makedirs(base, exist_ok=True)
    path = os.path.join(base, f"{prefix}-{uuid.uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=True)
    return path


@unittest.skipUnless(os.name == "nt", "DPAPI 仅在 Windows 上可用")
class CredentialStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = make_temp_dir()
        self.store = CredentialStore(os.path.join(self.temp, "credentials"))

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def test_protect_roundtrip(self) -> None:
        secret = "p@ss-密码-123"
        blob = protect(secret)
        self.assertNotIn(b"p@ss", blob)
        self.assertEqual(unprotect(blob), secret)

    def test_save_load_delete(self) -> None:
        self.assertIsNone(self.store.load(7))
        self.assertFalse(self.store.has(7))

        self.store.save(7, "s3cret")
        self.assertTrue(self.store.has(7))
        self.assertEqual(self.store.load(7), "s3cret")

        self.store.delete(7)
        self.assertFalse(self.store.has(7))
        self.assertIsNone(self.store.load(7))

    def test_file_does_not_contain_plaintext(self) -> None:
        self.store.save(3, "very-secret-password")
        path = os.path.join(self.store.directory, "source-3.bin")
        with open(path, "rb") as handle:
            raw = handle.read()
        self.assertNotIn(b"very-secret-password", raw)

    def test_empty_password_removes_existing(self) -> None:
        self.store.save(5, "abc")
        self.store.save(5, "")
        self.assertFalse(self.store.has(5))

    def test_unicode_password(self) -> None:
        self.store.save(9, "密码🔒")
        self.assertEqual(self.store.load(9), "密码🔒")


if __name__ == "__main__":
    unittest.main()
