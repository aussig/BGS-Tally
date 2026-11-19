"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from time import sleep
from unittest.mock import patch
from pathlib import Path
import json


class TestPrefs:
    """Test plugin preferences behavior."""

    def test_prefs_initialization(self, harness) -> None:
        """Test basic harness initialization and preference loading."""
        assert harness is not None

        file:Path = Path(harness.plugin.plugin_dir, "..", "data", "prefs_structure.json")
        with file.open("r", encoding="utf-8") as f:
            raw:list = json.load(f)

        assert len(harness.plugin.prefs.prefs) == len(raw)
        assert len(harness.plugin.prefs.prefs[0].sections) == len(raw[0].get("sections", []))
        assert len(harness.plugin.prefs.prefs[0].sections[0].prefs) == len(raw[0].get("sections", [{}])[0].get("prefs", []))

    def test_prefs_frame(self, harness) -> None:
        """Test preference frame creation."""
        assert harness is not None

        harness.plugin.prefs.get_prefs_frame(harness.parent)
        assert(harness.plugin.prefs.frame is not None)

    def test_purge_archive_by_ticktime(self, harness, tmp_path, monkeypatch) -> None:
        """Archived activity older than the cutoff is deleted, newer is kept."""
        from datetime import UTC, datetime, timedelta
        from bgstally.constants import DATETIME_FORMAT_ACTIVITY

        archive:Path = tmp_path / "activitydata" / "archive"
        archive.mkdir(parents=True)
        now:datetime = datetime.now(UTC)
        for name, age in (("old", 400), ("new", 300)):
            (archive / f"{name}.json").write_text(json.dumps({"ticktime": (now - timedelta(days=age)).strftime(DATETIME_FORMAT_ACTIVITY)}))
        (archive / "bad.json").write_text("{}")

        monkeypatch.setattr(harness.plugin, "plugin_dir", str(tmp_path))
        assert harness.plugin.activity_manager.purge_archive(365) == 1
        assert sorted(f.name for f in archive.iterdir()) == ["bad.json", "new.json"]
