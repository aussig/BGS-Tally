import textwrap

from bgstally.constants import CheckStates
from bgstally.debug import Debug

try:
    from EDMCOverlay import edmcoverlay
except ImportError:
    edmcoverlay = None

HEIGHT_CHARACTER_NORMAL = 14
HEIGHT_CHARACTER_LARGE = 20
WIDTH_CHARACTER_NORMAL = 4
WIDTH_CHARACTER_LARGE = 6
MAX_LINES_PER_PANEL = 30


class Overlay:
    """
    Handles the game overlay. Provides purpose-agnostic functions to display information and data in frames on screen.
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.edmcoverlay = None
        self.problem_displaying:bool = False
        self._check_overlay()


    def display_message(self, frame_name: str, message: str, fit_to_text: bool = False, ttl_override: int = None, text_colour_override: str = None, title_colour_override: str = None, has_title: bool = False):
        """
        Display a message in the overlay
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return

        try:
            fi:dict = self._get_frame_info(frame_name)

            # Split text on line breaks, then limit length of each line
            lines:list = message.splitlines()
            segments:list = []
            for line in lines:
                segments += textwrap.wrap(line, width = 70, subsequent_indent = '  ')

            message_width:int = len(max(segments, key = len)) * WIDTH_CHARACTER_NORMAL if fi['text_size'] == "normal" else len(max(segments, key = len)) * WIDTH_CHARACTER_LARGE
            message_height:int = len(segments) * HEIGHT_CHARACTER_NORMAL if fi['text_size'] == "normal" else len(max(segments, key = len)) * HEIGHT_CHARACTER_LARGE
            ttl:int = ttl_override if ttl_override else fi['ttl']
            title_colour:str = title_colour_override if title_colour_override else fi['title_colour']
            text_colour:str = text_colour_override if text_colour_override else fi['text_colour']

            # Border
            if fi['border_colour'] and fi['fill_colour']:
                self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", fi['border_colour'], fi['fill_colour'], fi['x'], fi['y'], message_width + 30 if fit_to_text else fi['w'], message_height + 10 if fit_to_text else fi['h'], ttl=ttl)

            yoffset:int = 0
            index:int = 0

            # Title
            if has_title:
                self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", segments[index], title_colour, fi['x'] + 10, fi['y'] + 5 + yoffset, ttl=ttl, size="large")
                yoffset += HEIGHT_CHARACTER_LARGE
                index += 1

            # Text
            while index <= MAX_LINES_PER_PANEL:
                if index < len(segments):
                    if index < MAX_LINES_PER_PANEL:
                        # Line has content
                        self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", segments[index], text_colour, fi['x'] + 10, fi['y'] + 5 + yoffset, ttl=ttl, size=fi['text_size'])
                    else:
                        # Last line
                        self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", "[...]", text_colour, fi['x'] + 10, fi['y'] + 5 + yoffset, ttl=ttl, size=fi['text_size'])
                else:
                    # Unused line, clear
                    self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", "", text_colour, fi['x'] + 10, fi['y'] + 5 + yoffset, ttl=ttl, size=fi['text_size'])

                yoffset += HEIGHT_CHARACTER_NORMAL if fi['text_size'] == "normal" else HEIGHT_CHARACTER_LARGE
                index += 1

            self.problem_displaying = False

        except Exception as e:
            if not self.problem_displaying:
                # Only log a warning about failure once
                self.problem_displaying = True
                Debug.logger.info(f"Could not display overlay message")


    def display_indicator(self, frame_name: str, ttl_override: int = None, fill_colour_override: str = None, border_colour_override: str = None):
        """
        Display a rectangular indicator
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return

        try:
            fi = self._get_frame_info(frame_name)
            ttl = ttl_override if ttl_override else fi['ttl']
            fill_colour = fill_colour_override if fill_colour_override else fi['fill_colour']
            border_colour = border_colour_override if border_colour_override else fi['border_colour']
            self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", border_colour, fill_colour, fi['x'], fi['y'], fi['w'], fi['h'], ttl=ttl)

        except Exception as e:
            if not self.problem_displaying:
                # Only log a warning about failure once
                self.problem_displaying = True
                Debug.logger.info(f"Could not display overlay message")


    def display_progress_bar(self, frame_name: str, message: str, progress: float = 0, ttl_override: int = None):
        """
        Display a progress bar with a message
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return

        try:
            fi:dict = self._get_frame_info(frame_name)
            ttl:int = ttl_override if ttl_override else fi['ttl']
            bar_width:int = int(fi['w'] * progress)
            bar_height:int = 10

            #vect:list = [{'x':int(cx+(coords['x']*hw)), 'y':int(cy-(coords['y']*hh))]

            self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}", message, fi['text_colour'], fi['x'] + 10, fi['y'] + 5, ttl=ttl, size=fi['text_size'])
            self.edmcoverlay.send_shape(f"bgstally-bar-{frame_name}", "rect", "#ffffff", fi['fill_colour'], fi['x'] + 10, fi['y'] + 20, bar_width, bar_height, ttl=ttl)
            self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", "#ffffff", fi['border_colour'], fi['x'] + 10 + bar_width, fi['y'] + 20, fi['w'] - bar_width, bar_height, ttl=ttl)

            self.problem_displaying = False

        except Exception as e:
            if not self.problem_displaying:
                # Only log a warning about failure once
                self.problem_displaying = True
                Debug.logger.info(f"Could not display overlay message")


    def _check_overlay(self):
        """
        Ensure overlay is running and available
        """
        if edmcoverlay:
            try:
                self.edmcoverlay = edmcoverlay.Overlay()
                self.display_message("info", "BGSTally Ready", True, 30)
            except Exception as e:
                Debug.logger.warning(f"EDMCOverlay is not running")
            else:
                Debug.logger.info(f"EDMCOverlay is running")
        else:
            # Couldn't load edmcoverlay python lib, the plugin probably isn't installed
            Debug.logger.warning(f"EDMCOverlay plugin is not installed")


    def _get_frame_info(self, frame: str) -> dict:
        """
        Get the properties of the type of message frame we are displaying
        """
        if frame == "info":
            return {'border_colour': "green", 'fill_colour': "green", 'text_colour': "#ffffff", 'title_colour': "#ffffff", 'x': 900, 'y': 5, 'w': 100, 'h': 25, 'ttl': 30, 'text_size': "normal"}
        elif frame == "indicator":
            return {'border_colour': "#ffffff", 'fill_colour': "#00cc00", 'text_colour': "red", 'title_colour': "red", 'x': 970, 'y': 10, 'w': 10, 'h': 15, 'ttl': 1, 'text_size': "normal"}
        elif frame == "tick":
            return {'border_colour': None, 'fill_colour': None, 'text_colour': "#ffffff", 'title_colour': "#ffffff", 'x': 1000, 'y': 0, 'w': 100, 'h': 25, 'ttl': 3, 'text_size': "large"}
        elif frame == "tickwarn":
            return {'border_colour': None, 'fill_colour': None, 'text_colour': "red", 'title_colour': "red", 'x': 1000, 'y': 20, 'w': 100, 'h': 25, 'ttl': 1, 'text_size': "normal"}
        elif frame == "tw":
            return {'border_colour': "#1a4f09", 'fill_colour': "#63029c", 'text_colour': "#ffffff", 'title_colour': "#ffffff", 'x': 1000, 'y': 60, 'w': 100, 'h': 25, 'ttl': 3, 'text_size': "normal"}
        elif frame == "system_info":
            return {'border_colour': None, 'fill_colour': None, 'text_colour': "#ffffff", 'title_colour': "green", 'x': 1000, 'y': 95, 'w': 100, 'h': 100, 'ttl': 30, 'text_size': "normal"}
