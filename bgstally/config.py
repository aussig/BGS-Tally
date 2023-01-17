import configparser as cp
import os.path

FOLDERNAME = "config"
FILENAME = "config.ini"


class Config(object):
    """
    Read the plugin config
    """
    def __init__(self, bgstally):
        self.config = cp.ConfigParser()
        self.config.read(os.path.join(bgstally.plugin_dir, FOLDERNAME, FILENAME))


    def apikey_inara(self):
        return self.config.get('apikeys', 'inara')


    def api(self, name:str) -> dict:
        """
        Fetch all information about a given API
        """
        return self.config[f'apis.{name}']
