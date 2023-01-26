import logging
from os import path

from config import appname


class Debug:
    logger = None

    def __init__(self, bgstally):
        # A Logger is used per 'found' plugin to make it easy to include the plugin's
        # folder name in the logging output format.
        # NB: plugin_name here *must* be the plugin's folder name as per the preceding
        #     code, else the logger won't be properly set up.
        Debug.logger = logging.getLogger(f'{appname}.{path.basename(bgstally.plugin_dir)}')

        # If the Logger has handlers then it was already set up by the core code, else
        # it needs setting up here.
        if not Debug.logger.hasHandlers():
            level = logging.INFO  # So logger.info(...) is equivalent to print()

            Debug.logger.setLevel(level)
            logger_channel = logging.StreamHandler()
            logger_formatter = logging.Formatter(f'%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d:%(funcName)s: %(message)s')
            logger_formatter.default_time_format = '%Y-%m-%d %H:%M:%S'
            logger_formatter.default_msec_format = '%s.%03d'
            logger_channel.setFormatter(logger_formatter)
            Debug.logger.addHandler(logger_channel)
