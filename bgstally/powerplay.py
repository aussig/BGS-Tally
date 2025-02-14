import json
import os
from os import path, remove
from os.path import join
from datetime import datetime
from typing import Dict, List
from bgstally.constants import DATETIME_FORMAT_JOURNAL, FOLDER_OTHER_DATA
from bgstally.debug import Debug
from config import config
import jsonlines

FILENAME = "merits.json"
JOURNALPATH = '/home/pixie/.steam/steam/steamapps/compatdata/359320/pfx/drive_c/users/steamuser/Saved Games/Frontier Developments/Elite Dangerous'
EPOCHLOG = "Journal.1970-01-01T000000.01.log"
EPOCHTS = "1970-01-01T00:00:00Z"

class LogLine:
    def __init__(self, logline):
        if isinstance(logline, dict):
            for key, value in logline.items():
                setattr(self, key, value)

class LogEntry:
    def __init__(self, logfile):
        self.LogLines = []
        with jsonlines.open(f"{logfile}") as logdata:
            for logline in logdata:
                self.AddLine(logline)
    def AddLine(self, logline):
        self.LogLines.append(LogLine(logline))

class PowerPlay: 
    def __init__(self):
        self.LogLines = []
        pass
    def AddLine(self, logline):
        self.LogLines.append(logline)

class LogBook:
    def __init__(self):
        self.LogEntries = []
        self.PowerPlay = PowerPlay()
    def AddEntry(self, logfile):
       self.LogEntries.append(LogEntry(logfile))

    def GetPowerPlay(self):
        for Entry in self.LogEntries:
            for Line in Entry.LogLines:
                for key, value in vars(Line).items():
                    if key == "event":
                        if value == "Powerplay":
                            self.PowerPlay.AddLine(Line)

    def ProcessPowerPlay(self, timestamp, merits, rank, tick_dt):
        print("ProcessPowerPlay")
        self.merits = merits
        self.meritsInit = self.merits
        self.timestamp = timestamp
        self.timestampInit = self.timestamp
        self.power = ""
        self.powerInit = self.power
        self.rank = rank
        self.rankInit = self.rank
        for Line in self.PowerPlay.LogLines:
            timestamp = Line.timestamp
            timestamp_dt = datetime.fromisoformat(timestamp.rstrip('Z'))
            power = Line.Power
            merits = Line.Merits
            rank = Line.Rank
            if int(merits) > int(self.merits):
                if timestamp_dt < tick_dt:
                    self.timestampInit = timestamp
                    self.meritsInit = merits
                    self.rankInit = rank
                if timestamp_dt > tick_dt:
                    self.timestamp = timestamp 
                    self.merits = merits
                    self.rank = rank
        return self.timestampInit, self.meritsInit, self.rankInit, self.timestamp, self.merits, self.rank
                
    def PrintEntries(self):
        for Entry in self.LogEntries:
            for Line in Entry.LogLines:
                for key, value in vars(Line).items():
                    print(f"{key}: {value}")

class Merits:
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.current_activity = self.bgstally.activity_manager.get_current_activity()
        self.current_tick_dt = self.current_activity.tick_time
        #self.current_tick_dt = datetime.fromisoformat(self.current_tick.rstrip('Z'))
        json_string = '[{"timestamp": "1970-01-01T00:00:00Z", "Power": "", "Rank": 0, "Merits": 0, "Journal": "Journal.1970-01-01T000000.01.log"}]'
        self.meritlog = json.loads(json_string)
        self.load()
        self.timestamp = self.meritlog[0]['timestamp']
        self.power = self.meritlog[0]['Power']
        self.rank = self.meritlog[0]['Rank']
        self.merits = self.meritlog[0]['Merits']
        self.lastjournal = self.meritlog[0]['Journal']
        self.newestjournal = self.lastjournal

        parts = self.lastjournal.split(".")
        if len(parts) >= 3 and parts[0] == "Journal": 
            date_part = parts[1] 
            time_part = date_part.split("T")[1]
            last_filestamp = f"{date_part[:10]}T{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}Z"
            self.lastjournal_dt = datetime.strptime(last_filestamp, "%Y-%m-%dT%H:%M:%SZ")

        self.merits_gained = 0
        activity = bgstally.activity_manager.get_current_activity()
        self.update_power(self.power)
        activity.update_merits_gained(self.merits_gained)

        journal_files = [file for file in os.listdir(JOURNALPATH) if file.endswith(".log")]
        # List to store newer files
        newer_files = []
        for journal_file in journal_files:
            #print("File: ", journal_file)
            file_name = os.path.join(JOURNALPATH, journal_file)
            # Split the filename to extract the date and time
            parts = journal_file.split(".")

            #print("Parts: ", parts)
            if len(parts) >= 3 and parts[0] == "Journal":
                date_part = parts[1] 
                time_part = date_part.split("T")[1]

                # Construct the full timestamp string
                file_timestamp = f"{date_part[:10]}T{time_part[:2]}:{time_part[2:4]}:{time_part[4:]}Z"

                # Convert to datetime object
                file_dt = datetime.strptime(file_timestamp, "%Y-%m-%dT%H:%M:%SZ")

                # Compare with the target timestamp
                if file_dt > self.lastjournal_dt:
                    newer_files.append((file_name, file_dt))

        #print("Newer Files:", newer_files)
        if newer_files:
            newest_file = max(newer_files, key=lambda x: x[1])
            self.newestjournal = os.path.basename(newest_file[0])
            logbook = LogBook()
            for journal_file, journal_dt in newer_files:
                logbook.AddEntry(journal_file)
            logbook.GetPowerPlay()
            timestampInit, meritsInit, rankInit, timestamp, merits, rank = logbook.ProcessPowerPlay(self.timestamp, self.merits, self.rank, self.current_tick_dt)

            self.timestamp = timestamp
            self.merits = meritsInit
            if int(merits) > int(meritsInit):
                self.merits_gained = int(merits) - int(meritsInit)
                activity.update_merits_gained(self.merits_gained)
            self.rank = rank
            json_string =  '[{"timestamp": "'+f'{timestampInit}'+'", "Power": "'+f'{self.power}'+'", "Rank": "'+f'{rankInit}'+'", "Merits": "'+f'{meritsInit}'+'", "Journal": "'+f'{self.newestjournal}'+'"}]'
            self.meritlog = json.loads(json_string)

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
        self.update_merits_gained(journal_entry)
            
    def update_merits_gained(self, journal_entry: Dict):
        #I should probably do a check to see if the power has changed
        self.merits_gained = int(journal_entry['Merits']) - int(self.merits)
        json_string =  '[{"timestamp": "'+f'{self.timestamp}'+'", "Power": "'+f'{self.power}'+'", "Rank": "'+f'{self.rank}'+'", "Merits": "'+f'{self.merits}'+'", "Journal": "'+f'{self.newestjournal}'+'"}]'
        self.meritlog = json.loads(json_string)
        activity = self.bgstally.activity_manager.get_current_activity()
        activity.update_merits_gained(self.merits_gained)
        return
    
    def update_power(self, power):
        activity = self.bgstally.activity_manager.get_current_activity()
        activity.update_power(power)

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