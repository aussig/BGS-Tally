"""
Test suite for faction manager module of BGS-Tally.
"""
import pytest # type: ignore
import shutil
from pathlib import Path
from time import sleep
from datetime import timedelta
from unittest.mock import Mock, patch, MagicMock
import filecmp

@pytest.fixture
def pre_start():
    """Reset factions.json before the plugin starts."""
    def init(request, harness) -> None:
        # Make sure we always start with a consistent factions.json
        Path(Path(__file__).parent / "otherdata" / "factions.json").unlink(missing_ok=True)
        factions_init_file:str = getattr(request, 'param', 'factions_init.json')
        if factions_init_file != 'None':
            shutil.copy(Path(__file__).parent / "config" / factions_init_file,
                        Path(__file__).parent / "otherdata" / "factions.json")

    return init

class TestFactions:
    """Test faction management functionality."""

    @pytest.mark.parametrize('harness', ['None', 'factions_init.json'], indirect=True)
    def test_initialization(self, harness) -> None:
        fm = harness.plugin.faction_manager
        assert fm.factions == []

    def test_add_favourite(self, harness) -> None:
        fm = harness.plugin.faction_manager

        assert fm.is_favourite("Faction A") is False
        fm.set_favourite("Faction A", True)
        assert fm.is_favourite("Faction A") is True

    def test_remove_favourite(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        assert fm.is_favourite("Faction A") is True
        fm.set_favourite("Faction A", False)
        assert fm.is_favourite("Faction A") is False

    def test_dupe_favourite(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        fm.set_favourite("Faction A", True)
        assert fm.is_favourite("Faction A") is True

    def test_remove_not_present(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", False)
        assert fm.is_favourite("Faction A") is False

    def test_save(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        fm.set_favourite("Faction B", True)
        fm.save()
        saved_file = Path(harness.plugin.plugin_dir) / "otherdata" / "factions.json"
        assert saved_file.exists()
        with open(saved_file) as f:
            assert f.read() == "[\"Faction A\", \"Faction B\"]"

        # Create a new instance to load the data
        fm2 = harness.plugin.faction_manager.__class__(harness.plugin)
        assert fm2.is_favourite("Faction A") is True
        assert fm2.is_favourite("Faction B") is True

    def test_load(self, harness) -> None:
        fm = harness.plugin.faction_manager

        fm.set_favourite("Faction A", True)
        fm.set_favourite("Faction B", True)
        fm.save()

        # Create a new instance to load the data
        fm2 = harness.plugin.faction_manager.__class__(harness.plugin)
        fm2.load()
        assert fm2.is_favourite("Faction A") is True
        assert fm2.is_favourite("Faction B") is True