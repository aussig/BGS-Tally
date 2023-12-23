from datetime import datetime, timedelta

import plug
import requests
import hashlib
from config import config
from secrets import token_hex

from bgstally.debug import Debug

DATETIME_FORMAT_DISPLAY = "%Y-%m-%d %H:%M:%S"
TICKID_UNKNOWN = "unknown_tickid"
URL_TICK_DETECTOR = "https://tick.edcd.io/api/tick"

class Tick:
    """
    Information about a tick
    """

    def __init__(self, bgstally, load: bool = False):
        self.bgstally = bgstally
        self.tick_id:str = TICKID_UNKNOWN
        self.tick_time:datetime = (datetime.utcnow() - timedelta(days = 30)) # Default to a tick a month old
        if load: self.load()


    def fetch_tick(self):
        """
        Tick check and counter reset
        """
        try:
            response = requests.get(URL_TICK_DETECTOR, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            Debug.logger.error(f"Unable to fetch latest tick from elitebgs.app: {str(e)}")
            plug.show_error(f"BGS-Tally WARNING: Unable to fetch latest tick")
            return None
        else:
            tickTime = response.text.replace("\"", "")
            tick_time:datetime = datetime.fromisoformat(tickTime).replace(tzinfo=None)

            if tick_time > self.tick_time:
                # There is a newer tick
                self.tick_id = hashlib.md5(tickTime.encode()).hexdigest()
                self.tick_time = tick_time
                return True

        return False


    def force_tick(self):
        """
        Force a new tick, user-initiated
        """
        # Set the tick time to the current datetime and generate a new 24-digit tick id with six leading zeroes to signify a forced tick
        self.tick_id = f"000000{token_hex(9)}"
        self.tick_time = datetime.now()


    def load(self):
        """
        Load tick status from config
        """
        self.tick_id = config.get_str("XLastTick")
        self.tick_time = datetime.fromisoformat(config.get_str("XTickTime", default=self.tick_time.isoformat())).replace(tzinfo=None)


    def save(self):
        """
        Save tick status to config
        """
        config.set('XLastTick', self.tick_id)
        config.set('XTickTime', self.tick_time.isoformat())


    def get_formatted(self, format:str = DATETIME_FORMAT_DISPLAY):
        """
        Return a formatted tick date/time
        """
        return self.tick_time.strftime(format)


    def get_next_formatted(self, format:str = DATETIME_FORMAT_DISPLAY):
        """
        Return next predicted tick formated date/time
        """
        return self.next_predicted().strftime(format)


    def next_predicted(self):
        """
        Return the next predicted tick time (currently just add 24h to the current tick time)
        """
        return self.tick_time + timedelta(hours = 24)
