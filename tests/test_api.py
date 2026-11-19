"""
Unit tests for api.py.
"""
import pytest # type: ignore

from bgstally.api import API, EVENTS_FILTER_DEFAULTS
from tests.edmc.requests import MockResponse

APPROVED_EVENTS:dict = {'Docked': {}, 'FSDJump': {}, 'MarketSell': {}}


class TestDiscovery:
    """Tests for API discovery."""

    def approved_api(self, harness) -> API:
        api:API = harness.plugin.api_manager.apis[0]
        api.events = dict(APPROVED_EVENTS)
        api.user_approved = True
        harness.plugin.api_manager.api_updated = False
        return api


    def test_unreachable_api_keeps_approval(self, harness) -> None:
        api:API = self.approved_api(harness)

        api.discovery_received(False, None, None)
        assert api.events == APPROVED_EVENTS

        api.discovery_received(True, MockResponse(200, json_data={'events': APPROVED_EVENTS}), None)
        assert api.user_approved is True
        assert harness.plugin.api_manager.api_updated is False


    def test_server_error_keeps_approval(self, harness) -> None:
        api:API = self.approved_api(harness)

        api.discovery_received(False, MockResponse(503), None)
        assert api.events == APPROVED_EVENTS
        assert api.user_approved is True


    def test_invalid_discovery_data_keeps_approval(self, harness) -> None:
        api:API = self.approved_api(harness)

        api.discovery_received(True, MockResponse(200, content='<html>Not JSON</html>'), None)
        assert api.events == APPROVED_EVENTS
        assert api.user_approved is True


    def test_missing_discovery_endpoint_uses_defaults(self, harness) -> None:
        api:API = self.approved_api(harness)

        api.discovery_received(False, MockResponse(404), None)
        assert api.events == EVENTS_FILTER_DEFAULTS


    def test_disallowed_discovery_method_uses_defaults(self, harness) -> None:
        api:API = self.approved_api(harness)

        api.discovery_received(False, MockResponse(405), None)
        assert api.events == EVENTS_FILTER_DEFAULTS


    def test_changed_events_need_approval(self, harness) -> None:
        api:API = self.approved_api(harness)

        api.discovery_received(True, MockResponse(200, json_data={'events': {**APPROVED_EVENTS, 'MarketBuy': {}}}), None)
        assert api.user_approved is False
        assert harness.plugin.api_manager.api_updated is True
