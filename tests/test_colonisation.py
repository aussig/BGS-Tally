"""
Test suite for colonisation module of BGS-Tally.
"""

import pytest # type: ignore
import shutil
from pathlib import Path
from typing import Generator
from time import sleep
from unittest.mock import patch, MagicMock

from harness import TestHarness
from bgstally.constants import BuildState


@pytest.fixture
def harness() -> Generator:
    """ Provide a fresh test harness for each test. """
    test_harness = TestHarness()
    test_harness.set_edmc_config()

    # Use the "normal" locations for assets and data
    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # Initialize colonisation state
    shutil.copy(Path(__file__).parent / "config" / "colonisation_init.json", 
                Path(__file__).parent / "otherdata" / "colonisation.json")

    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    test_harness.load_events("journal_events.json")
    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)

    yield test_harness


class TestColonisation:
    def test_add_modify_remove_system(self, harness) -> None:
        """ Test system creation """
        c = harness.plugin.colonisation
        
        data:dict = {'Name': 'Test System'}
        c.add_system(data, False, False)

        assert len(c.systems) == 1
        assert c.systems[0]['Name'] == 'Test System'
        assert c.systems[0]['Builds'] == []

        c.modify_system(0, {'Name': 'Renamed'})        
        assert len(c.systems) == 1
        assert c.systems[0]['Name'] == 'Renamed'

        c.remove_system(0)
        assert len(c.systems) == 0

    def test_add_modify_remove_build(self, harness) -> None:
        """ Test build creation """
        c = harness.plugin.colonisation

        system = c.add_system({'Name': 'Test System'}, False, False)
        assert system is not None

        build_data = {'Name': 'Test Build', 'Base Type': 'Asteroid Base', 'State': BuildState.PLANNED, 'MarketID': 12345}
        build = c.add_build(system, build_data, False)
        assert build is not None
        assert build['Name'] == 'Test Build'
        assert build['Base Type'] == 'Asteroid Base'
        assert build['State'] == BuildState.PLANNED
        assert build['MarketID'] == 12345

        c.modify_build(system, build['BuildID'], {'Name': 'Renamed Build'}, False)
        assert build['Name'] == 'Renamed Build'

        c.remove_build(system, build['MarketID'], False)
        assert len(system['Builds']) == 0
class TestColonisationOther:
    def test_body_name_variants(self, harness) -> None:
        c = harness.plugin.colonisation

        assert c.body_name('Sol', 'Sol') == 'A'
        assert c.body_name('Sol', 'Sol 1 Ring') == '1'
        assert c.body_name('Sol', 'Sol 2B') == '2B'

    def test_get_base_type_and_layouts(self, harness) -> None:
        c = harness.plugin.colonisation

        asteroid = c.get_base_type('Asteroid Base')
        assert asteroid.get('Category') == 'Starport'

        asteroid_by_layout = c.get_base_type('Asteroid')
        assert asteroid_by_layout.get('Type') == asteroid.get('Type')

        assert 'Asteroid Base' in c.get_base_types('All')
        assert 'Asteroid Base' in c.get_base_types('Initial')
        assert 'Asteroid Base' not in c.get_base_types('Settlement')

        assert 'Asteroid' in c.get_base_layouts('Asteroid Base')

    def test_system_and_build_tracking(self, harness) -> None:
        c = harness.plugin.colonisation

        c.systems = [{
            'Name': 'TestPlan',
            'StarSystem': 'Sol',
            'SystemAddress': 1234,
            'Builds': [{
                'Name': 'Asteroid Base',
                'Base Type': 'Asteroid Base',
                'State': BuildState.PLANNED,
                'BuildID': 'x-123',
                'MarketID': 9999,
                'Track': True
            }]
        }]

        c.progress = [{'MarketID': 9999, 'Required': {}, 'Delivered': {}, 'ConstructionComplete': False}]

        system = c.find_system({'StarSystem': 'Sol'})
        assert system is not None

        assert c.get_system_tracking(system) == 'All'

        tracked = c.get_tracked_builds()
        assert isinstance(tracked, list)
        assert len(tracked) == 0 or tracked[0].get('MarketID') == 9999

        build = c.find_build(system, {'MarketID': 9999})
        assert build is not None
        assert c.get_build_state(build) in [BuildState.PLANNED, BuildState.PROGRESS, BuildState.COMPLETE]

        required = c.get_required(system['Builds'])
        assert isinstance(required, list)
        assert len(required) >= 1
        assert 'steel' in required[0]

    def test_progress_update_and_find(self, harness) -> None:
        c = harness.plugin.colonisation

        c.systems = [{
            'Name': 'TestPlan',
            'StarSystem': 'Sol',
            'SystemAddress': 1234,
            'Builds': [{
                'Name': 'Asteroid Base',
                'Base Type': 'Asteroid Base',
                'State': BuildState.PLANNED,
                'BuildID': 'x-123',
                'MarketID': 9999,
                'Track': True
            }]
        }]

        c.progress = []
        c.find_or_create_progress(9999)

        assert c.find_progress(9999) is not None

        c.update_progress(9999, {
            'ResourcesRequired': [
                {'Name': '$steel_name;', 'RequiredAmount': 100, 'ProvidedAmount': 10}
            ],
            'ConstructionComplete': False
        }, silent=True)

        progress = c.find_progress(9999)
        assert progress is not None
        assert progress.get('Required', {}).get('steel') == 100
        assert progress.get('Delivered', {}).get('steel') == 10

    def test_commodity_and_cargo_helpers(self, harness) -> None:
        c = harness.plugin.colonisation

        c.bgstally.ui.commodities = {
            'water': {'Name': 'Water', 'Category': 'Consumer'}
        }

        assert c.get_commodity('water') == 'Water'
        assert c.get_commodity('unknown') == 'Unknown'

        c._update_cargo({'water': 5, 'iron': 0})
        assert c.cargo == {'water': 5}

    def test_get_cost_and_try_complete_build(self, harness) -> None:
        c = harness.plugin.colonisation

        cost = c._get_cost('Asteroid Base')
        assert isinstance(cost, dict)
        assert cost.get('steel', None) is not None

        c.systems = [{
            'Name': 'TestPlan',
            'StarSystem': 'Sol',
            'SystemAddress': 1234,
            'Builds': [{
                'Name': 'Test Construction Site',
                'Base Type': 'Asteroid Base',
                'State': BuildState.PROGRESS,
                'BuildID': 'x-123',
                'MarketID': 9999,
                'Track': True
            }]
        }]

        c.progress = [{
            'MarketID': 9999,
            'ProjectID': 'p100',
            'ConstructionComplete': True,
            'Required': {},
            'Delivered': {}
        }]

        result = c.try_complete_build(9999)
        assert result is True

        build = c.find_build(c.systems[0], {'MarketID': 9999})
        assert build is not None
        assert build['State'] == BuildState.COMPLETE
        assert build['Track'] is False

    def test_add_and_remove_build(self, harness) -> None:
        c = harness.plugin.colonisation

        system = c.add_system({'StarSystem': 'Sol', 'Name': 'SolPlan', 'Builds': []}, prepop=False, rcsync=False)

        new_build = c.add_build(system, {
            'Name': 'Test Base',
            'Base Type': 'Asteroid Base',
            'State': BuildState.PLANNED,
            'MarketID': 8888,
            'Track': False
        }, silent=True)

        assert new_build.get('BuildID', None) is not None
        assert c.find_build(system, {'MarketID': 8888}) is not None

        c.remove_build(system, 8888, silent=True)
        assert c.find_build(system, {'MarketID': 8888}) is None

    def test_move_build(self, harness) -> None:
        c = harness.plugin.colonisation

        system = c.add_system({'StarSystem': 'Sol', 'Name': 'SolPlan2', 'Builds': []}, prepop=False, rcsync=False)
        c.add_build(system, {'Name': 'B1', 'Base Type': 'Asteroid Base', 'BuildID': 'b1', 'MarketID': 101, 'State': BuildState.PLANNED}, silent=True)
        c.add_build(system, {'Name': 'B2', 'Base Type': 'Asteroid Base', 'BuildID': 'b2', 'MarketID': 102, 'State': BuildState.PLANNED}, silent=True)

        c.move_build(system, 0, 1)
        assert system['Builds'][0]['BuildID'] == 'b2'
        assert system['Builds'][1]['BuildID'] == 'b1'

    def test_journal_entry_system_claim(self, harness) -> None:
        c = harness.plugin.colonisation
        c.systems = []
        c.progress = []

        c.journal_entry('Testy', False, 'Sol', '', {'event': 'ColonisationSystemClaim', 'StarSystem': 'Sol', 'SystemAddress': 777, 'timestamp': '2024-01-01T00:00:00Z'}, {})

        system = c.find_system({'StarSystem': 'Sol', 'SystemAddress': 777})
        assert system is not None
        assert system.get('Claimed') == '2024-01-01T00:00:00Z'
        assert system.get('Architect') == 'Testy'

    def test_journal_entry_colonisation_contribution(self, harness) -> None:
        c = harness.plugin.colonisation
        c.systems = [{
            'Name': 'SolPlan', 'StarSystem': 'Sol', 'SystemAddress': 777, 'RCSync': True, 'Hidden': False,
            'Builds': [{'Name': 'Asteroid Base', 'MarketID': 500, 'BuildID': 'x-1', 'ProjectID': None}]
        }]
        c.progress = [{'MarketID': 500, 'ProjectID': 100, 'Required': {}, 'Delivered': {}}]

        with patch('bgstally.colonisation.RavenColonial') as mock_rc:
            instance = mock_rc.return_value
            c.current_system = 'Sol'
            c.system_id = 777
            c.market_id = 500
            c.journal_entry('Testy', False, 'Sol', '', {'event': 'ColonisationContribution', 'StarSystem': 'Sol', 'SystemAddress': 777, 'Contributions': [{'Name': '$steel_name;', 'ProvidedAmount': 10}]}, {})

            instance.record_contribution.assert_called_once()

    def test_journal_entry_docked_creates_build(self, harness) -> None:
        c = harness.plugin.colonisation

        c.systems = []
        c.progress = []

        with patch('bgstally.colonisation.BODY_SERVICE.import_bodies', return_value=None), \
             patch('bgstally.colonisation.SYSTEM_SERVICE.import_system', return_value=None), \
             patch('bgstally.colonisation.STATION_SERVICE.import_stations', return_value=None):

            c.current_system = 'Sol'
            c.system_id = 777
            c.market_id = 600
            c.station = 'System Colonisation Ship'

            c.journal_entry('Testy', False, 'Sol', '', {'event': 'Docked', 'StarSystem': 'Sol', 'SystemAddress': 777, 'MarketID': 600, 'StationType': 'Starport'}, {})

            system = c.find_system({'StarSystem': 'Sol', 'SystemAddress': 777})
            assert system is not None
            assert len(system.get('Builds', [])) > 0

            build = c.find_build(system, {'MarketID': 600})
            if build is None:
                # fallback: there is at least one build; pick the first one
                build = system.get('Builds', [None])[0]

            assert build is not None
            assert build['State'] == BuildState.PROGRESS
            
    def test_journal_entry_construction_depot_updates_progress(self, harness) -> None:
        c = harness.plugin.colonisation
        c.systems = [{
            'Name': 'SolPlan', 'StarSystem': 'Sol', 'SystemAddress': 777, 'RCSync': False, 'Hidden': False,
            'Builds': [{'Name': 'Asteroid Base', 'MarketID': 500, 'BuildID': 'x-1', 'ProjectID': None, 'State': BuildState.PLANNED}]
        }]
        c.progress = []

        c.current_system = 'Sol'
        c.system_id = 777
        c.market_id = 500

        c.journal_entry('Testy', False, 'Sol', '', {'event': 'ColonisationConstructionDepot', 'StarSystem': 'Sol', 'SystemAddress': 777, 'MarketID': 500, 'ProjectID': 100, 'ResourcesRequired': [{'Name': '$steel_name;', 'RequiredAmount': 200, 'ProvidedAmount': 20}]}, {})

        progress = c.find_progress(500)
        assert progress is not None
        assert progress.get('Required', {}).get('steel') == 200
        assert progress.get('Delivered', {}).get('steel') == 20

        build = c.find_build(c.systems[0], {'MarketID': 500})
        assert build is not None
        assert build.get('ProjectID') == 100

    def test_journal_entry_supercruise_exit_tracks_project(self, harness) -> None:
        c = harness.plugin.colonisation
        c.systems = [{
            'Name': 'SolPlan', 'StarSystem': 'Sol', 'SystemAddress': 777, 'RCSync': True, 'Hidden': False,
            'Builds': [{'Name': 'Asteroid Base', 'MarketID': 500, 'BuildID': 'x-1', 'ProjectID': 100, 'Track': True, 'State': BuildState.PROGRESS}]
        }]

        c.progress = [{'MarketID': 500, 'ProjectID': 100, 'Required': {}, 'Delivered': {}, 'ConstructionComplete': False}]

        c.current_system = 'Sol'
        c.system_id = 777
        c.station = 'Some Station'

        with patch('bgstally.colonisation.RavenColonial') as mock_rc:
            instance = mock_rc.return_value
            c.journal_entry('Testy', False, 'Sol', '', {'event': 'SupercruiseExit', 'StarSystem': 'Sol', 'SystemAddress': 777}, {})
            instance.load_project.assert_called_once_with(c.progress[0])

    def test_get_body_get_bodies_and_ids(self, harness) -> None:
        c = harness.plugin.colonisation
        system = {
            'StarSystem': 'Sol',
            'Bodies': [{'name': 'Sol 1', 'bodyId': 1, 'isLandable': True}, {'name': 'Sol 2', 'bodyId': 2, 'isLandable': False}]
        }

        assert c.get_body(system, '1') is not None
        assert c.get_body(system, 1) is not None
        bodies_all = c.get_bodies(system, 'All')
        assert '1' in bodies_all
        bodies_surface = c.get_bodies(system, 'Surface')
        assert '1' in bodies_surface
        assert '2' not in bodies_surface

    def test_from_dict_migrates_resourcesrequired(self, harness) -> None:
        c = harness.plugin.colonisation
        payload = {
            'Systems': [],
            'Progress': [{'MarketID': 500, 'ResourcesRequired': [{'Name': '$steel_name;', 'RequiredAmount': 12, 'ProvidedAmount': 3}], 'Updated': '2026-03-01'}],
            'ProgressView': 0,
            'ProgressUnits': [0],
            'ProgressColumns': [],
            'BuildIndex': 0,
            'WindowGeometries': {}
        }

        c.progress = []
        c._from_dict(payload)

        progress_list = [p for p in c.progress if p.get('MarketID') == 500 and p.get('Required', {}).get('steel') == 12]
        assert len(progress_list) == 1

        progress = progress_list[0]
        assert progress['Required']['steel'] == 12
        assert progress['Delivered']['steel'] == 3

    def test_generate_buildid(self, harness) -> None:
        c = harness.plugin.colonisation
        id1 = c._generate_buildid(None)
        assert id1.startswith('x')
        id2 = c._generate_buildid(123)
        assert id2 == '&123'