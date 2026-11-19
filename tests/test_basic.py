"""
Test suite for BGS-Tally plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
from time import sleep
from unittest.mock import patch

class TestStartup:
    """Test plugin startup behavior."""

    def test_harness_initialization(self, harness) -> None:
        """Test basic harness initialization."""
        assert harness is not None
        assert harness.config.get_str('BGST_Status', default='On') == 'Yes'

    @pytest.mark.live_requests
    def test_harness_live_initialization(self, harness) -> None:
        """Test basic harness initialization."""
        assert harness is not None
        assert harness.config.get_str('BGST_Status', default='On') == 'Yes'
