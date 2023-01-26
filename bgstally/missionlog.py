import json
from os import path, remove
from datetime import datetime, timedelta

from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_DATA
from bgstally.debug import Debug

FILENAME = "missionlog.json"
FILENAME_LEGACY = "MissionLog.txt"
TIME_MISSION_EXPIRY_D = 7


class MissionLog:
    """
    Handle a log of all in-progress missions
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.missionlog = []
        self.load()
        self._expire_old_missions()


    def load(self):
        """
        Load state from file
        """
        # New location
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        if path.exists(file):
            with open(file) as json_file:
                self.missionlog = json.load(json_file)
                return

        # Legacy location
        file = path.join(self.bgstally.plugin_dir, FILENAME_LEGACY)
        if path.exists(file):
            with open(file) as json_file:
                self.missionlog = json.load(json_file)
            remove(file)


    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self.missionlog, outfile)


    def get_missionlog(self):
        """
        Get the current missionlog
        """
        return self.missionlog


    def get_mission(self, missionid: int):
        """
        Fetch a given mission from the missionlog, or None if not found
        """
        for mission in self.missionlog:
            if mission['MissionID'] == missionid: return mission
        return None


    def add_mission(self, name: str, faction: str, missionid: str, expiry: str, system_name: str, station_name: str, commodity_count: int, passenger_count: int, kill_count: int):
        """
        Add a mission to the missionlog
        """
        self.missionlog.append({'Name': name, 'Faction': faction, 'MissionID': missionid, 'Expiry': expiry, 'System': system_name, 'Station': station_name,
                                'CommodityCount': commodity_count, 'PassengerCount': passenger_count, 'KillCount': kill_count})


    def delete_mission_by_id(self, missionid: str):
        """
        Delete the mission with the given id from the missionlog
        """
        for i in range(len(self.missionlog)):
            if self.missionlog[i]['MissionID'] == missionid:
                self.missionlog.pop(i)
                break


    def delete_mission_by_index(self, missionindex: int):
        """
        Delete the mission at the given index from the missionlog
        """
        self.missionlog.pop(missionindex)


    def get_active_systems(self):
        """
        Return a list of systems that have currently active missions
        """
        systems = [x['System'] for x in self.missionlog]
        # De-dupe before returning
        return list(dict.fromkeys(systems))


    def _expire_old_missions(self):
        """
        Clear out all missions older than 7 days from the mission log
        """
        for mission in reversed(self.missionlog):
            # Old missions pre v1.11.0 and missions with missing expiry dates don't have Expiry stored. Set to 7 days ahead for safety
            if not 'Expiry' in mission or mission['Expiry'] == "": mission['Expiry'] = (datetime.utcnow() + timedelta(days = TIME_MISSION_EXPIRY_D)).strftime(DATETIME_FORMAT_JOURNAL)

            timedifference = datetime.utcnow() - datetime.strptime(mission['Expiry'], DATETIME_FORMAT_JOURNAL)
            if timedifference > timedelta(days = TIME_MISSION_EXPIRY_D):
                # Keep missions for a while after they have expired, so we can log failed missions correctly
                self.missionlog.remove(mission)
