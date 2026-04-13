"""
Test suite for colonisation module of BGS-Tally.
"""

import pytest # type: ignore
import shutil
import json
from pathlib import Path
from typing import Generator
from time import sleep
from unittest.mock import patch, MagicMock

from datetime import datetime, UTC
from bgstally.windows import progress
from harness import TestHarness
from bgstally.constants import BuildState

SHORT_DELAY = 0.01

@pytest.fixture
def harness(request) -> Generator:
    """ Provide a fresh test harness for each test. """
    live = request.node.get_closest_marker('live_requests') is not None
    test_harness = TestHarness(live_requests=live)

    # Use the "normal" locations for assets and data
    import bgstally.constants
    bgstally.constants.FOLDER_ASSETS = "../assets"
    bgstally.constants.FOLDER_DATA = "../data"

    # Put in a response for the update manager so it doesn't error
    if not live:
        from tests.edmc.requests import queue_response, MockResponse
        queue_response('get', MockResponse(200,
                                           url='https://api.github.com/repos/aussig/BGS-Tally/releases/latest',
                                           json_data={'tag_name': 'v1.0.0','draft': True,'prerelease': True,
                                                       'assets': [{'browser_download_url': 'https://example.com/download'}]}),
                                            url='https://api.github.com/repos/aussig/BGS-Tally/releases/latest')
        queue_response('get', MockResponse(200,
                                           url='http://tick.infomancer.uk/galtick.json',
                                           json_data={"lastGalaxyTick": datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')}),
                                           url='http://tick.infomancer.uk/galtick.json',
                                           sticky=True)

    # Initialize colonisation state - use parametrized filename if provided
    Path(Path(__file__).parent / "otherdata" / "colonisation.json").unlink(missing_ok=True)
    colonisation_init_file = getattr(request, 'param', 'colonisation_init.json')
    if colonisation_init_file != 'None':
        shutil.copy(Path(__file__).parent / "config" / colonisation_init_file,
                    Path(__file__).parent / "otherdata" / "colonisation.json")

    from load import plugin_start3, plugin_app, journal_entry
    import bgstally.globals
    test_harness.plugin = bgstally.globals.this

    plugin_start3(str(test_harness.plugin_dir))
    plugin_app(test_harness.parent)

    test_harness.register_journal_handler(journal_entry, 'Testy', 'Sol', False)

    yield test_harness
    test_harness.assert_no_unhandled_exceptions()

class TestColonisationInitialization:
    @pytest.mark.parametrize('harness', ['None', 'colonisation_empty.json', 'colonisation-5.4.0.json'], indirect=True)
    def test_save_files(self, harness) -> None:
        """ Test that the plugin initializes correctly with no existing data and doesn't save an empty overview. """
        assert isinstance(harness.plugin.colonisation.systems, list)
        assert len(harness.plugin.ui.window_progress.columns) == 4

    def test_load_base_types_and_costs(self, harness) -> None:
        c = harness.plugin.colonisation
        c._load_base_types()
        assert isinstance(c.base_types, dict)
        assert 'Asteroid Base' in c.base_types

        assert isinstance(c.base_costs, dict)
        assert 'Hub' in c.base_costs

class TestColonisationMethods:
    """Synthetic tests of individual colonisation functions."""

    def test_body_name(self, harness) -> None:
        c = harness.plugin.colonisation
        name = c.body_name('Bleae Thua ED-D c12-5', 'Bleae Thua ED-D c12-5 8 b')
        assert name == '8 b'

    def test_get_base_type(self, harness) -> None:
        c = harness.plugin.colonisation

        asteroid = c.get_base_type('Asteroid Base')
        assert asteroid.get('Category') == 'Starport'

        layout = c.get_base_type('Dec Truss')
        assert layout.get('Type') == "Dodecahedron Starport"

        layout = c.get_base_type('NoneExistent')
        assert layout == {}

    def test_get_base_types(self, harness) -> None:
        c = harness.plugin.colonisation

        for t, count in {'Any': 55, 'Initial': 11, 'Starport': 5, 'Ports': 6, 'Settlement': 18, 'Nonexistent': 0}.items():
            types = c.get_base_types(t)
            assert isinstance(types, list)
            assert len(types) == count

    def test_get_base_layouts(self, harness) -> None:
        c = harness.plugin.colonisation

        for l, count in {'Any': 110, 'Installation': 31, 'Satellite': 3, 'Nonexistent': 0}.items():
            layouts = c.get_base_layouts(l)
            assert isinstance(layouts, list)
            assert len(layouts) == count

    def test_get_all_systems(self, harness) -> None:
        c = harness.plugin.colonisation
        systems = c.get_all_systems()
        assert isinstance(systems, list)
        assert len(systems) == 1
        assert systems[0].get('Name') == c.systems[0].get('Name')

    def test_get_system(self, harness) -> None:
        c = harness.plugin.colonisation
        sys = c.systems[0]
        for k, v in sys.items():
            assert c.get_system(k, v) == sys
        assert c.get_system('NonexistentKey', 'NonexistentValue') is None

    def test_get_system_tracking(self, harness) -> None:
        c = harness.plugin.colonisation
        # Make sure we only have two builds so we can do the three states
        c.systems[0]['Builds'] = c.systems[0]['Builds'][0:2]
        sys = c.systems[0]
        for i, state in enumerate(['None', 'Partial', 'All']):
            if i > 0: sys['Builds'][i-1]['Track'] = True
            res = c.get_system_tracking(sys)
            assert res == state

    def test_find_system(self, harness) -> None:
        c = harness.plugin.colonisation
        sys = c.systems[0]
        for k in ['SystemAddress', 'StarSystem', 'Name']:
            assert c.find_system({k: sys[k]}) == sys
            assert c.find_system({k: 'NonexistentValue'}) is None

    def test_find_or_create_system(self, harness) -> None:
        """ Test system find or addition """
        c = harness.plugin.colonisation
        syscount:int = len(c.systems)

        # Existing system
        data:dict = {'Name': c.systems[0]['Name']}
        found:dict = c.find_or_create_system(data)
        assert len(c.systems) == syscount
        assert found['Name'] == data['Name']

        # New system
        data:dict = {'Name': 'Test System', 'StarSystem': 'Test StarSystem'}
        found:dict = c.find_or_create_system(data)

        assert len(c.systems) == syscount + 1
        assert found['Name'] == data['Name']
        assert found['StarSystem'] == data['StarSystem']
        assert found['Builds'] == []

    def test_add_system(self, harness) -> None:
        """ Test system creation """
        c = harness.plugin.colonisation
        syscount:int = len(c.systems)
        data:dict = {'Name': 'Test System', 'StarSystem': 'Test StarSystem'}
        c.add_system(data, False, False)

        assert len(c.systems) == syscount + 1
        assert c.systems[syscount]['Name'] == 'Test System'
        assert c.systems[syscount]['StarSystem'] == 'Test StarSystem'
        assert c.systems[syscount]['Builds'] == []

    def test_modify_system(self, harness) -> None:
        """ Test system modification """
        c = harness.plugin.colonisation
        data:dict = {'Name': 'Test System'}

        c.modify_system(0, {'Name': 'Renamed'})
        assert c.systems[0]['Name'] == 'Renamed'

        c.modify_system(0, {'StarSystem': 'Nowhere'})

        assert c.systems[0]['StarSystem'] == 'Nowhere'
        assert c.systems[0]['SystemAddress'] == None

    def test_remove_system(self, harness) -> None:
        """ Test system removal """
        c = harness.plugin.colonisation
        syscount:int = len(c.systems)
        data:dict = {'Name': 'Test System'}

        c.add_system(data, False, False)
        assert len(c.systems) == syscount + 1
        c.remove_system(syscount)
        assert len(c.systems) == syscount

    def test_get_body(self, harness) -> None:
        c = harness.plugin.colonisation
        sys = c.systems[0]
        body = sys['Bodies'][0]
        assert c.get_body(sys, body['bodyId']) == body
        assert c.get_body(sys, 'NonexistentID') is None

    def test_get_bodies(self, harness) -> None:
        c = harness.plugin.colonisation
        sys = c.systems[0]

        for type, count in {'All': len(sys['Bodies']), 'Surface': 0, 'Orbital': len(sys['Bodies'])}.items():
            bodies = c.get_bodies(sys, type)
            assert isinstance(bodies, list)
            assert len(bodies) == count

    def test_find_build(self, harness) -> None:
        """ This function does a lot of important matching so there are many scenarios to test """
        c = harness.plugin.colonisation
        system = c.systems[0]
        build = system['Builds'][0]

        # By ID
        found_build:dict = c.find_build(system, {'BuildID': build['BuildID']})
        assert found_build is not None
        assert found_build['BuildID'] == build['BuildID']

        # By Name
        found_build:dict = c.find_build(system, {'Name': build['Name']})
        assert found_build is not None
        assert found_build['BuildID'] == build['BuildID']

        # By Colonisation Ship (always matches the first build in the system)
        found_build:dict = c.find_build(system, {'Name': 'System Colonisation Ship: Dummy'})
        assert found_build is not None
        assert found_build['BuildID'] == build['BuildID']

        # By Name that matches a construction site
        found_build:dict = c.find_build(system, {'Name': f'Surface Construction Site: {system["Builds"][-1]["Name"]}'})
        assert found_build is not None
        assert found_build['BuildID'] == system['Builds'][-1]['BuildID']

        data:dict = {"Track": "No", "State": "Planned", "Base Type": "Industrial Outpost", "Name": "Plan Name",
                             "Body": "B 7", "Layout": "Vulcan", "BodyNum": 30, "Location": "Orbital", "Readonly": False}
        c.add_build(system, data, True)

        # A planned build that is now in progress with a name that doesn't match but we have a plan of the right type
        # that we haven't visited yet.
        found_build:dict = c.find_build(system, {'Name': 'Orbital Construction Site: Build Name', 'State': 'Progress', 'Body': 'B 7'})
        assert found_build is not None
        assert found_build['Name'] == "Plan Name"

        # A build that doesn't match because the location is wrong.
        system['Builds'][-1] = data
        found_build:dict = c.find_build(system, {'Name': 'Planetary Construction Site: Build Name', 'State': 'Progress', 'Body': 'B 6'})
        assert found_build is None

        # A build that doesn't match because the body is wrong.
        system['Builds'][-1] = data
        found_build:dict = c.find_build(system, {'Name': 'Orbital Construction Site: Build Name', 'State': 'Progress', 'Body': 'B 6'})
        assert found_build is None

        # A build that doesn't match because the existing build has already been visited.
        system['Builds'][-1] = data
        system['Builds'][-1]['MarketID'] = '1233445667'
        found_build:dict = c.find_build(system, {'Name': 'Orbital Construction Site: Build Name', 'State': 'Progress', 'Body': 'B 7'})
        assert found_build is None

    def test_add_build(self, harness) -> None:
        """ Test build creation """
        c = harness.plugin.colonisation

        system:dict = c.systems[0]
        new_build:dict = {"Track": "No", "State": "Planned", "Base Type": "Industrial Outpost", "Name": "Goddard Sanctuary",
                          "Body": "B 7", "MarketID": 4224499459, "StationEconomy": "Extraction", "Layout": "Vulcan",
                          "BuildID": "&4224499459", "BodyNum": 30, "Location": "Orbital", "Readonly": True}

        build:dict = c.add_build(system, new_build, False)
        assert build is not None
        assert build['Name'] == new_build['Name']
        assert build['Base Type'] == new_build['Base Type']
        assert build['State'] == new_build['State']
        assert build['MarketID'] == new_build['MarketID']

    def test_modify_build(self, harness) -> None:
        """ Test build modification """
        c = harness.plugin.colonisation

        system:dict = c.systems[0]
        build:dict = system['Builds'][0]
        assert build['Name'] != 'Renamed Build'
        c.modify_build(system, build['BuildID'], {'Name': 'Renamed Build', 'Base Type': 'Scientific Outpost'}, False)
        assert build['Name'] == 'Renamed Build'
        assert build['Base Type'] == 'Scientific Outpost'

        c.modify_build(system, "&1111111111", {'Name': 'Error Name'}, False)
        for b in system['Builds']:
            assert b['Name'] != 'Error Name'

    def test_move_build(self, harness) -> None:
        """ Test build order change """
        c = harness.plugin.colonisation

        system:dict = c.systems[0]
        new_build:dict = {"Track": "No", "State": "Planned", "Base Type": "Industrial Outpost", "Name": "Goddard Sanctuary",
                          "Body": "B 7", "MarketID": 4224499459, "StationEconomy": "Extraction", "Layout": "Vulcan",
                          "BuildID": "&4224499459", "BodyNum": 30, "Location": "Orbital", "Readonly": True}

        build:dict = c.add_build(system, new_build, False)
        bone = system['Builds'][0]
        btwo = system['Builds'][1]

        c.move_build(system, 0, 1)

        assert system['Builds'][0]['BuildID'] == btwo['BuildID']
        assert system['Builds'][1]['BuildID'] == bone['BuildID']

    def test_remove_build(self, harness) -> None:
        """ Test build removal """
        c = harness.plugin.colonisation

        system:dict = c.systems[0]

        buildc:int = len(system['Builds'])
        new_build:dict = {"Track": "No", "State": "Planned", "Base Type": "Industrial Outpost", "Name": "Goddard Sanctuary",
                          "Body": "B 7", "MarketID": 4224499459, "StationEconomy": "Extraction", "Layout": "Vulcan",
                          "BuildID": "&4224499459", "BodyNum": 30, "Location": "Orbital", "Readonly": True}

        build:dict = c.add_build(system, new_build, False)
        assert len(system['Builds']) == buildc + 1
        c.remove_build(system, build['MarketID'], False)
        assert len(system['Builds']) == buildc

    def test_set_base_type(self, harness) -> None:
        c = harness.plugin.colonisation

        sys = c.systems[0]
        buildid = sys['Builds'][0]['BuildID']
        type = sys['Builds'][0]['Base Type']
        c.set_base_type(sys, buildid, 'Scientific Outpost')

        assert sys['Builds'][0]['Base Type'] == 'Scientific Outpost'

    def test_get_cost(self, harness) -> None:
        """ Get base costs for various base types"""
        c = harness.plugin.colonisation

        for v, amt in {'Dodecahedron Starport': [63342, 74062],
                       'Pirate Outpost': [5588, 6660],
                       'Civilian Planetary Outpost': [10164, 10164],
                       'Agriculture Tier 1 Sml': [768, 768],
                       'Extraction Tier 2 Lrg': [3084, 3084],
                       'Space Bar': [2483, 2483]}.items():
            for i, a in enumerate(amt):
                cost = c._get_cost(v, bool(i))
                assert isinstance(cost, dict)
                assert 'steel' in cost
                assert cost['steel'] == a

        cost = c._get_cost('Dummy', False)
        assert cost == {}

    def test_get_progress(self, harness) -> None:
        """ test the get_required and get_delivered functions that call _get_progress"""
        c = harness.plugin.colonisation
        build:dict = c.systems[0]['Builds'][1]
        progress:list = c.get_required([build])
        assert isinstance(progress, list)
        assert progress[0]['aluminium'] == 1377

        progress:list = c.get_delivered([build])
        assert isinstance(progress, list)
        assert progress[0]['foodcartridges'] == 8

    def test_find_or_create_progress(self, harness) -> None:
        """ Test progress find or create """
        c = harness.plugin.colonisation
        build:dict = c.systems[0]['Builds'][1]
        progress:list = c.find_or_create_progress(build['MarketID'])
        assert isinstance(progress, dict)
        assert progress['ConstructionProgress'] == 0.001194

        progress:list = c.find_or_create_progress(12345)
        assert isinstance(progress, dict)
        assert progress['MarketID'] == 12345
        assert progress['Required'] == {}

    def test_find_progress(self, harness) -> None:
        """ test the get_required and get_delivered functions that call _get_progress"""
        c = harness.plugin.colonisation
        build:dict = c.systems[0]['Builds'][1]

        progress:list = c.find_progress(build['MarketID'])
        assert isinstance(progress, dict)
        assert progress['ConstructionProgress'] == 0.001194

        progress:list = c.find_progress(build['ProjectID'])
        assert isinstance(progress, dict)
        assert progress['ConstructionProgress'] == 0.001194

    def test_update_progress(self, harness) -> None:
        """test updating progress with a colonisation contribution"""
        c = harness.plugin.colonisation
        mid:int = c.progress[0]['MarketID']
        data:dict = { "event":"ColonisationConstructionDepot", "ConstructionProgress":0.059446, "ConstructionComplete":False, "ConstructionFailed":False, "ResourcesRequired":[ { "Name":"$aluminium_name;", "Name_Localised":"Aluminium", "RequiredAmount":500, "ProvidedAmount":0, "Payment":3239 }, { "Name":"$ceramiccomposites_name;", "Name_Localised":"Ceramic Composites", "RequiredAmount":521, "ProvidedAmount":0, "Payment":724 }, { "Name":"$cmmcomposite_name;", "Name_Localised":"CMM Composite", "RequiredAmount":4508, "ProvidedAmount":0, "Payment":6788 }, { "Name":"$computercomponents_name;", "Name_Localised":"Computer Components", "RequiredAmount":62, "ProvidedAmount":0, "Payment":1112 }, { "Name":"$copper_name;", "Name_Localised":"Copper", "RequiredAmount":242, "ProvidedAmount":0, "Payment":1050 }, { "Name":"$foodcartridges_name;", "Name_Localised":"Food Cartridges", "RequiredAmount":94, "ProvidedAmount":0, "Payment":673 }, { "Name":"$fruitandvegetables_name;", "Name_Localised":"Fruit and Vegetables", "RequiredAmount":50, "ProvidedAmount":0, "Payment":865 }, { "Name":"$insulatingmembrane_name;", "Name_Localised":"Insulating Membrane", "RequiredAmount":347, "ProvidedAmount":0, "Payment":11788 }, { "Name":"$liquidoxygen_name;", "Name_Localised":"Liquid oxygen", "RequiredAmount":1792, "ProvidedAmount":1298, "Payment":2260 }, { "Name":"$medicaldiagnosticequipment_name;", "Name_Localised":"Medical Diagnostic Equipment", "RequiredAmount":13, "ProvidedAmount":0, "Payment":3609 }, { "Name":"$nonlethalweapons_name;", "Name_Localised":"Non-Lethal Weapons", "RequiredAmount":13, "ProvidedAmount":0, "Payment":2503 }, { "Name":"$polymers_name;", "Name_Localised":"Polymers", "RequiredAmount":521, "ProvidedAmount":0, "Payment":682 }, { "Name":"$powergenerators_name;", "Name_Localised":"Power Generators", "RequiredAmount":19, "ProvidedAmount":0, "Payment":3072 }, { "Name":"$semiconductors_name;", "Name_Localised":"Semiconductors", "RequiredAmount":68, "ProvidedAmount":0, "Payment":1526 }, { "Name":"$steel_name;", "Name_Localised":"Steel", "RequiredAmount":6660, "ProvidedAmount":0, "Payment":5057 }, { "Name":"$superconductors_name;", "Name_Localised":"Superconductors", "RequiredAmount":112, "ProvidedAmount":0, "Payment":7657 }, { "Name":"$titanium_name;", "Name_Localised":"Titanium", "RequiredAmount":5534, "ProvidedAmount":0, "Payment":5360 }, { "Name":"$water_name;", "Name_Localised":"Water", "RequiredAmount":741, "ProvidedAmount":0, "Payment":662 }, { "Name":"$waterpurifiers_name;", "Name_Localised":"Water Purifiers", "RequiredAmount":38, "ProvidedAmount":0, "Payment":849 } ] }
        c.update_progress(mid, data, True)

        assert c.progress[0]['ConstructionProgress'] == 0.059446

    def test_update_cargo(self, harness) -> None:
        """ Test _update_cargo """
        c = harness.plugin.colonisation
        assert len(c.cargo) == 0

        shutil.copy(Path(__file__).parent / "journal_config" / 'cargo_init.json',
                    Path(__file__).parent / "journal_folder" / "Cargo.json")

        harness.fire_event({"event": "Cargo", "Vessel": "Ship"})
        assert len(c.cargo) == 3

    def test_generate_buildid(self, harness) -> None:
        """ Generate an ID for a build """
        c = harness.plugin.colonisation
        id1 = c._generate_buildid(None)
        assert id1.startswith('x')
        id2 = c._generate_buildid(123)
        assert id2 == '&123'

    def test_from_dict_migrates_resourcesrequired(self, harness) -> None:
        """This can likely go away soon and the code can be removed """
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


class TestColonisationFullBuild:
    def test_claim(self, harness) -> None:
        """ Test claiming a system and deploying a beacon creates a new system entry and updates state. """
        harness.load_events("colonisation_build.json")
        c = harness.plugin.colonisation
        harness.play_sequence("claim", SHORT_DELAY)

    def test_visit(self, harness) -> None:
        """ Test visiting the colonisation ship. """
        harness.load_events("colonisation_build.json")
        c = harness.plugin.colonisation

        harness.play_sequence("claim", SHORT_DELAY)
        harness.play_sequence("visit_ship", SHORT_DELAY)

        assert len(c.systems[1]['Builds']) == 1
        assert c.systems[1]['Builds'][0]['BuildID'] == "&3963439106"
        assert len(c.progress) == 2

    def test_contribution(self, harness) -> None:
        """ Test visiting the colonisation ship. """
        harness.load_events("colonisation_build.json")
        c = harness.plugin.colonisation

        harness.play_sequence("claim", SHORT_DELAY)
        harness.play_sequence("visit_ship", SHORT_DELAY)
        harness.play_sequence("contribution", SHORT_DELAY)

        assert c.progress[-1]['ConstructionProgress'] == 0.059446
        assert c.progress[-1]['Delivered']['liquidoxygen'] == 1298

    def test_complete(self, harness) -> None:
        """ Test completing construction. """
        harness.load_events("colonisation_build.json")
        c = harness.plugin.colonisation

        harness.play_sequence("claim", SHORT_DELAY)
        harness.play_sequence("visit_ship", SHORT_DELAY)
        harness.play_sequence("contribution", SHORT_DELAY)
        harness.play_sequence("complete", SHORT_DELAY)

        assert c.progress[-1]['Required']['steel'] == 6660
        assert c.progress[-1]['Delivered']['steel'] == 6660
        assert c.progress[-1]['ConstructionProgress'] == 1.0
        assert c.progress[-1]['ConstructionComplete'] is True

    def test_visit_outpost(self, harness) -> None:
        """ Test visiting the completed outpost. """
        harness.load_events("colonisation_build.json")
        c = harness.plugin.colonisation

        harness.play_sequence("claim", SHORT_DELAY)
        harness.play_sequence("visit_ship", SHORT_DELAY)
        harness.play_sequence("contribution", SHORT_DELAY)
        harness.play_sequence("complete", SHORT_DELAY)
        harness.play_sequence("visit_outpost", SHORT_DELAY)

        assert c.systems[1]['Builds'][0]['BuildID'] == "&3963439106"
        assert c.systems[1]['Builds'][0]['MarketID'] == 4351826691
        assert c.systems[1]['Builds'][0]['State'] == BuildState.COMPLETE
        assert c.systems[1]['Builds'][0]['Name'] == 'Citroen Arsenal'



# Unused tests that do some interesting things
    # def test_journal_entry_colonisation_contribution(self, harness) -> None:
    #     c = harness.plugin.colonisation

    #     with patch('bgstally.colonisation.RavenColonial') as mock_rc:
    #         instance = mock_rc.return_value
    #         c.current_system = 'Sol'
    #         c.system_id = 777
    #         c.market_id = 500
    #         c.journal_entry('Testy', False, 'Sol', '', {'event': 'ColonisationContribution', 'StarSystem': 'Sol', 'SystemAddress': 777, 'Contributions': [{'Name': '$steel_name;', 'ProvidedAmount': 10}]}, {})

    #         instance.record_contribution.assert_called_once()

    # def test_journal_entry_docked_creates_build(self, harness) -> None:
    #     c = harness.plugin.colonisation

    #     c.systems = []
    #     c.progress = []

    #     with patch('bgstally.colonisation.BODY_SERVICE.import_bodies', return_value=None), \
    #          patch('bgstally.colonisation.SYSTEM_SERVICE.import_system', return_value=None), \
    #          patch('bgstally.colonisation.STATION_SERVICE.import_stations', return_value=None):

    #         c.current_system = 'Sol'
    #         c.system_id = 777
    #         c.market_id = 600
    #         c.station = 'System Colonisation Ship'

    #         c.journal_entry('Testy', False, 'Sol', '', {'event': 'Docked', 'StarSystem': 'Sol', 'SystemAddress': 777, 'MarketID': 600, 'StationType': 'Starport'}, {})

    #         system = c.find_system({'StarSystem': 'Sol', 'SystemAddress': 777})
    #         assert system is not None
    #         assert len(system.get('Builds', [])) > 0

    #         build = c.find_build(system, {'MarketID': 600})
    #         if build is None:
    #             # fallback: there is at least one build; pick the first one
    #             build = system.get('Builds', [None])[0]

    #         assert build is not None
    #         assert build['State'] == BuildState.PROGRESS

    # def test_journal_entry_supercruise_exit_tracks_project(self, harness) -> None:
    #     c = harness.plugin.colonisation
    #     c.systems = [{
    #         'Name': 'SolPlan', 'StarSystem': 'Sol', 'SystemAddress': 777, 'RCSync': True, 'Hidden': False,
    #         'Builds': [{'Name': 'Asteroid Base', 'MarketID': 500, 'BuildID': 'x-1', 'ProjectID': 100, 'Track': True, 'State': BuildState.PROGRESS}]
    #     }]

    #     c.progress = [{'MarketID': 500, 'ProjectID': 100, 'Required': {}, 'Delivered': {}, 'ConstructionComplete': False}]

    #     c.current_system = 'Sol'
    #     c.system_id = 777
    #     c.station = 'Some Station'

    #     with patch('bgstally.colonisation.RavenColonial') as mock_rc:
    #         instance = mock_rc.return_value
    #         c.journal_entry('Testy', False, 'Sol', '', {'event': 'SupercruiseExit', 'StarSystem': 'Sol', 'SystemAddress': 777}, {})
    #         instance.load_project.assert_called_once_with(c.progress[0])
