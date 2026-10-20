"""
Test suite for market module of BGS-Tally.
"""
import pytest # type: ignore
from pathlib import Path
import shutil
from time import sleep
from unittest.mock import patch

@pytest.fixture
def pre_start():
    """Reset Market.json before the plugin starts."""
    def init(request, harness) -> None:
        Path(Path(__file__).parent / "journal_folder" / "Market.json").unlink(missing_ok=True)
        market_init_file:str = getattr(request, 'param', 'market_init.json')
        if market_init_file != 'None':
            shutil.copy(Path(__file__).parent / "journal_config" / market_init_file,
                        Path(__file__).parent / "journal_folder" / "Market.json")

    return init

class TestMethods:
    """Test methods in bsgatally/market.py."""

    def test_not_available(self, harness) -> None:
        """Test not available."""
        assert harness is not None
        res:bool = harness.plugin.market.available(1111111111)

        assert res == False

    def test_available(self, harness) -> None:
        """Test available."""
        assert harness is not None

        res:bool = harness.plugin.market.available(4292118787)
        assert res == True

    def test_load(self, harness) -> None:
        """Test load."""
        assert harness is not None
        res:bool = harness.plugin.market.available(4292118787)
        assert res == True

        assert harness.plugin.market.name == "Nakamura's Syntheticals"
        assert harness.plugin.market.id == 4292118787
        assert len(harness.plugin.market.commodities) == 44

    def test_get_commodity(self, harness) -> None:
        """Test get_commodity."""
        assert harness is not None
        res:bool = harness.plugin.market.available(4292118787)
        assert res == True

        assert harness.plugin.market.get_commodity('cmmcomposite')['SellPrice'] == 5972
        assert harness.plugin.market.get_commodity('steel')['BuyPrice'] == 0
        assert harness.plugin.market.get_commodity('titanium')['StockBracket'] == 2
