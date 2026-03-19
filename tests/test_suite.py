"""
Test suite for EDMC Neutron Dancer plugin using pytest.

Run with: .venv/bin/python -m pytest tests/test_plugin.py -v --tb=short 2>&1 | tail -30
Run with: .venv_win\\Scripts\\python.exe -m pytest tests\\test_plugin.py -v --tb=short
"""

import pytest # type: ignore
import sys
import os
from pathlib import Path
from typing import Generator, Optional
from time import sleep
from unittest.mock import Mock, patch, MagicMock
import json
import time
import logging
import tkinter as tk

# Setup path for imports
plugin_dir:Path = Path(__file__).parent
sys.path.insert(0, str(plugin_dir))

# Config is already mocked by conftest.py
from harness import TestHarness
from load import journal_entry

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@pytest.fixture
def harness() -> Generator:
    """Provide a fresh test harness for each test."""
    test_harness = TestHarness()
    test_harness.register_journal_handler(journal_entry)
    yield test_harness
    # Cleanup if needed


class TestStartup:
    """Test plugin startup behavior."""

    def test_harness_initialization(self) -> None:
        """Test basic harness initialization."""
        harness = TestHarness()
        assert True == True