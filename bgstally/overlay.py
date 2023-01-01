from bgstally.debug import Debug
from bgstally.constants import CheckStates

try:
    from EDMCOverlay import edmcoverlay
except ImportError:
    edmcoverlay = None

WIDTH_CHARACTER_NORMAL = 4
WIDTH_CHARACTER_LARGE = 6

class Overlay:
    """
    Handles the game overlay. Provides purpose-agnostic functions to display information and data in frames on screen.
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.edmcoverlay = None
        self._check_overlay()


    def display_message(self, frame_name: str, message: str, fit_to_width: bool = False, ttl_override: int = None, text_colour_override: str = None):
        """
        Display a message in the overlay
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return

        try:
            fi = self._get_frame_info(frame_name)
            message_width = len(message) * WIDTH_CHARACTER_NORMAL if fi["text_size"] == "normal" else len(message) * WIDTH_CHARACTER_LARGE
            ttl = ttl_override if ttl_override else fi["ttl"]
            text_colour = text_colour_override if text_colour_override else fi["text_colour"]

            if fi["border_colour"] and fi["fill_colour"]:
                self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", fi["border_colour"], fi["fill_colour"], fi["x"], fi["y"], message_width + 30 if fit_to_width else fi["w"], fi["h"], ttl=ttl)
            self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}", message, text_colour, fi["x"] + 10, fi["y"] + 5, ttl=ttl, size=fi["text_size"])
        except Exception as e:
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


    def _get_frame_info(self, frame: str):
        """
        Get the properties of the type of message frame we are displaying
        """
        if frame == "info":
            return {"border_colour": "green", "fill_colour": "green", "text_colour": "#ffffff", "x": 900, "y": 5, "w": 100, "h": 25, "ttl": 6, "text_size": "normal"}
        elif frame == "tick":
            return {"border_colour": None, "fill_colour": None, "text_colour": "#ffffff", "x": 1000, "y": 0, "w": 100, "h": 25, "ttl": 3, "text_size": "large"}
        elif frame == "tickwarn":
            return {"border_colour": None, "fill_colour": None, "text_colour": "red", "x": 1000, "y": 20, "w": 100, "h": 25, "ttl": 1, "text_size": "normal"}
