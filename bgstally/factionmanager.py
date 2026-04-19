
import json
from os import path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bgstally.bgstally import BGSTally

from bgstally.constants import FOLDER_OTHER_DATA
from bgstally.debug import Debug

FILENAME = "factions.json"


class FactionManager:
    """Handles favourite factions
    """

    def __init__(self, bgstally: 'BGSTally'):
        """Initialise the class

        Args:
            bgstally (bgstally): The bgstally plugin object
        """
        self.bgstally: BGSTally = bgstally
        self.factions: list[str] = []
        self.load()


    def load(self) -> None:
        """Load state from file
        """
        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        if path.exists(file):
            try:
                with open(file) as json_file:
                    self.factions = json.load(json_file)
                    return
            except Exception as e:
                Debug.logger.info(f"Unable to load {file}")

    def save(self):
        """Save state to file
        """

        file = path.join(self.bgstally.plugin_dir, FOLDER_OTHER_DATA, FILENAME)
        with open(file, 'w') as outfile:
            json.dump(self.factions, outfile)


    def is_favourite(self, faction_name: str) -> bool:
        """Check if a faction is marked as favourite

        Args:
            faction_name (str): The faction name
        """
        return faction_name in self.factions


    def set_favourite(self, faction_name: str, favourite: bool = True) -> None:
        """Mark or unmark a faction as favourite

        Args:
            faction_name (str): The faction name
            favourite (bool, optional): True to mark as favourite, False to unmark. Defaults to True.
        """
        if favourite:
            if faction_name not in self.factions:
                self.factions.append(faction_name)
        else:
            if faction_name in self.factions:
                self.factions.remove(faction_name)
        self.save()
