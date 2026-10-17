"""Tests for data/runs/merge_cache.py Zip-Slip and validation defenses."""

from __future__ import annotations

import io
import stat
import tempfile
import zipfile
from pathlib import Path

import pytest

from data.runs.merge_cache import merge_zip


def test_merge_valid_entry():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        zip_path = tmp_path / "test_valid.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("ab/abcdef123456.json", '{"response": "ok"}')

        added, rejected = merge_zip(zip_path, cache_dir)
        assert added == 1
        assert (cache_dir / "ab" / "abcdef123456.json").exists()

        # Second merge: must NOT overwrite existing
        added2, rejected2 = merge_zip(zip_path, cache_dir)
        assert added2 == 0
        assert rejected2.get("already exists (not overwritten)") == 1


def test_merge_rejects_path_traversal():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        zip_path = tmp_path / "test_traversal.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("../../x.py", "malicious_code = True")

        added, rejected = merge_zip(zip_path, cache_dir)
        assert added == 0
        assert not (tmp_path / "x.py").exists()
        assert not (cache_dir / "x.py").exists()
        assert any("path traversal" in r or "not a .json" in r for r in rejected)


def test_merge_rejects_backslash_traversal():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        zip_path = tmp_path / "test_backslash_traversal.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            # Entry with Windows backslashes: 00\..\..\x.json
            zf.writestr(r"00\..\..\x.json", '{"pwned": true}')

        added, rejected = merge_zip(zip_path, cache_dir)
        assert added == 0
        assert not (tmp_path / "x.json").exists()
        assert not (cache_dir / "x.json").exists()
        assert rejected.get("path traversal component (..)") == 1


def test_merge_rejects_absolute_path():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        zip_path = tmp_path / "test_abs.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("/etc/evil.json", '{"bad": true}')
            zf.writestr("C:/evil2.json", '{"bad": true}')

        added, rejected = merge_zip(zip_path, cache_dir)
        assert added == 0
        assert rejected.get("absolute path or drive letter") == 2


def test_merge_rejects_symlink():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        zip_path = tmp_path / "test_symlink.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zinfo = zipfile.ZipInfo("link.json")
            # Set POSIX symlink attribute (S_IFLNK)
            zinfo.create_system = 3  # Unix
            zinfo.external_attr = stat.S_IFLNK << 16
            zf.writestr(zinfo, "/etc/passwd")

        added, rejected = merge_zip(zip_path, cache_dir)
        assert added == 0
        assert rejected.get("symlink entry") == 1
        assert not (cache_dir / "link.json").exists()


def test_merge_rejects_non_json_and_oversized():
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        zip_path = tmp_path / "test_ext_size.zip"

        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("script.sh", "echo bad")
            zf.writestr("image.png", b"\x89PNG")
            # 6MB payload (exceeds 5MB cap)
            zinfo_big = zipfile.ZipInfo("oversized.json")
            zinfo_big.file_size = 6 * 1024 * 1024
            zf.writestr(zinfo_big, b"0" * (6 * 1024 * 1024))

        added, rejected = merge_zip(zip_path, cache_dir)
        assert added == 0
        assert rejected.get("not a .json file") == 2
        assert rejected.get("file size exceeds 5MB limit") == 1
        assert not (cache_dir / "script.sh").exists()
        assert not (cache_dir / "oversized.json").exists()
