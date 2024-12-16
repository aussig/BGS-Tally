import json
from os import path, remove
from os.path import join
from typing import Dict, List
from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA
from bgstally.debug import Debug
from config import config

FILENAME = "merits.json"

class Merits:
    def __init__(self, bgstally):
        self.bgstally = bgstally
        json_string = '{"Power": "", "Rank": 0, "Merits": 0}'
        self.meritlog = json.loads(json_string)
        self.load()
        self.power = self.meritlog[0]['Power']
        self.rank = self.meritlog[0]['Rank']
        self.merits = self.meritlog[0]['Merits']
        self.merits_gained = 0
        activity = bgstally.activity_manager.get_current_activity()
        activity.update_merits_gained(self.power, self.merits_gained)

    def load(self):
        """
        Load state from file
        """
        # New location
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self.meritlog = json.load(json_file)
                    return
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")
            
    def update(self, journal_entry: Dict):
        #I should probably do a check to see if the power has changed here just in case
        self.merits_gained = int(journal_entry['Merits']) - int(self.merits)
        json_string =  '{"Power": "'+f'{journal_entry["Power"]}'+'", "Rank": "'+f'{journal_entry["Rank"]}'+'", "Merits": "'+f'{journal_entry["Merits"]}'+'"}'
        self.meritlog = json.load(json_string)
        activity = bgstally.activity_manager.get_current_activity()
        activity.update_merits_gained(journal_entry['Power'], self.merits_gained)
        return

    def save(self):
        """
        Save state to file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self.meritlog, outfile)
        return

    def get_meritlog(self):
        """
        Get the current meritlog
        """
        return self.meritlog
    
    def get_meritsgained(self):
        """
        Get the current meritsgained
        """
        return self.meritsgained