import textwrap

from bgstally.constants import CheckStates
from bgstally.debug import Debug
from bgstally.utils import _

try:
    from EDMCOverlay import edmcoverlay
except ImportError:
    edmcoverlay = None

HEIGHT_CHARACTER_NORMAL = 14
HEIGHT_CHARACTER_LARGE = 20
WIDTH_CHARACTER_NORMAL = 4
WIDTH_CHARACTER_LARGE = 7
MAX_LINES_PER_PANEL = 30

WIDTH_OVERLAY = 1280  # Virtual screen width of overlay
HEIGHT_OVERLAY = 960  # Virtual screen height of overlay


class Overlay:
    """
    Handles the game overlay. Provides purpose-agnostic functions to display information and data in frames on screen.
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally
        self.edmcoverlay: Overlay = None
        self.problem_displaying: bool = False
        self._check_overlay()


    def display_message(self, frame_name: str, message: str, fit_to_text: bool = False, ttl_override: int = None, text_colour_override: str = None, title_colour_override: str = None, text_includes_title: bool = False, title: str = None):
        """
        Display a message in the overlay
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return
        if message == "": return

        try:
            fi: dict | None = self.bgstally.config.overlay_frame(frame_name)
            if fi is None: return

            # Split text on line breaks, then limit length of each line
            lines: list = message.splitlines()
            segments: list = []
            for line in lines:
                segments += textwrap.wrap(line, width = 80, subsequent_indent = '  ')

            message_width: int = len(max(segments, key = len)) * WIDTH_CHARACTER_NORMAL if fi['text_size'] == "normal" else len(max(segments, key = len)) * WIDTH_CHARACTER_LARGE
            message_height: int = len(segments) * HEIGHT_CHARACTER_NORMAL if fi['text_size'] == "normal" else len(segments) * HEIGHT_CHARACTER_LARGE
            ttl: int = ttl_override if ttl_override else int(fi['ttl'])
            title_colour: str = title_colour_override if title_colour_override else fi['title_colour']
            text_colour: str = text_colour_override if text_colour_override else fi['text_colour']

            if fi.get('x_center', False):
                x: int = int((WIDTH_OVERLAY - message_width) / 2) + int(fi['x'])   # Horizontally centred, offset by 'x'
            else:
                x: int = int(fi['x'])

            if fi.get('y_center', False):
                y: int = int((HEIGHT_OVERLAY - message_height) / 2) + int(fi['y']) # Vertically centred, offset by 'y'
            else:
                y: int = int(fi['y'])

            # Border
            if fi['border_colour'] and fi['fill_colour']:
                self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", fi['border_colour'], fi['fill_colour'], x, y, message_width + 30 if fit_to_text else fi['w'], message_height + 10 if fit_to_text else fi['h'], ttl=ttl)

            yoffset: int = 0
            index: int = 0

            # Title
            if text_includes_title:
                self.edmcoverlay.send_message(f"bgstally-msg-title-{frame_name}-{index}", segments[index], title_colour, x + 10, y + 5 + yoffset, ttl=ttl, size="large")
                yoffset += HEIGHT_CHARACTER_LARGE
                index += 1
            elif title is not None:
                self.edmcoverlay.send_message(f"bgstally-msg-title-{frame_name}-{index}", title, title_colour, x + 10, y + 5 + yoffset, ttl=ttl, size="large")
                yoffset += HEIGHT_CHARACTER_LARGE

            # Text
            while index <= MAX_LINES_PER_PANEL:
                if index < len(segments):
                    if index < MAX_LINES_PER_PANEL:
                        # Line has content
                        self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", segments[index], text_colour, x + 10, y + 5 + yoffset, ttl=ttl, size=fi['text_size'])
                    else:
                        # Last line
                        self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", "[...]", text_colour, x + 10, y + 5 + yoffset, ttl=ttl, size=fi['text_size'])
                else:
                    # Unused line, clear
                    self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}-{index}", "", text_colour, x + 10, y + 5 + yoffset, ttl=ttl, size=fi['text_size'])

                yoffset += HEIGHT_CHARACTER_NORMAL if fi['text_size'] == "normal" else HEIGHT_CHARACTER_LARGE
                index += 1

            self.problem_displaying = False

        except Exception as e:
            if not self.problem_displaying:
                # Only log a warning about failure once
                self.problem_displaying = True
                Debug.logger.warning(f"Could not display overlay message", exc_info=e)


    def display_indicator(self, frame_name: str, ttl_override: int = None, fill_colour_override: str = None, border_colour_override: str = None):
        """
        Display a rectangular indicator
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return

        try:
            fi: dict | None = self.bgstally.config.overlay_frame(frame_name)
            if fi is None: return

            ttl: int = ttl_override if ttl_override else int(fi['ttl'])
            fill_colour: str = fill_colour_override if fill_colour_override else fi['fill_colour']
            border_colour: str = border_colour_override if border_colour_override else fi['border_colour']
            self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", border_colour, fill_colour, int(fi['x']), int(fi['y']), int(fi['w']), int(fi['h']), ttl=ttl)

            self.problem_displaying = False

        except Exception as e:
            if not self.problem_displaying:
                # Only log a warning about failure once
                self.problem_displaying = True
                Debug.logger.warning(f"Could not display overlay message", exc_info=e)


    def display_progress_bar(self, frame_name: str, message: str, progress: float = 0, ttl_override: int = None):
        """
        Display a progress bar with a message
        """
        if self.edmcoverlay == None: return
        if not self.bgstally.state.enable_overlay: return

        try:
            fi: dict | None = self.bgstally.config.overlay_frame(frame_name)
            if fi is None: return

            ttl: int = ttl_override if ttl_override else int(fi['ttl'])
            bar_width: int = int(int(fi['w']) * progress)
            bar_height: int = 10

            #vect:list = [{'x':int(cx+(coords['x']*hw)), 'y':int(cy-(coords['y']*hh))]

            self.edmcoverlay.send_message(f"bgstally-msg-{frame_name}", message, fi['text_colour'], int(fi['x']) + 10, int(fi['y']) + 5, ttl=ttl, size=fi['text_size'])
            self.edmcoverlay.send_shape(f"bgstally-bar-{frame_name}", "rect", "#ffffff", fi['fill_colour'], int(fi['x']) + 10, int(fi['y']) + 20, bar_width, bar_height, ttl=ttl)
            self.edmcoverlay.send_shape(f"bgstally-frame-{frame_name}", "rect", "#ffffff", fi['border_colour'], int(fi['x']) + 10 + bar_width, int(fi['y']) + 20, int(fi['w']) - bar_width, bar_height, ttl=ttl)

            self.problem_displaying = False

        except Exception as e:
            if not self.problem_displaying:
                # Only log a warning about failure once
                self.problem_displaying = True
                Debug.logger.warning(f"Could not display overlay message", exc_info=e)


    def _check_overlay(self):
        """
        Ensure overlay is running and available
        """
        if edmcoverlay:
            try:
                self.edmcoverlay = edmcoverlay.Overlay()
                self.display_message("info", _("{plugin_name} Ready").format(plugin_name=self.bgstally.plugin_name), True, 30) # LANG: Overlay message
            except Exception as e:
                Debug.logger.warning(f"EDMCOverlay is not running")
            else:
                Debug.logger.info(f"EDMCOverlay is running")
        else:
            # Couldn't load edmcoverlay python lib, the plugin probably isn't installed
            Debug.logger.warning(f"EDMCOverlay plugin is not installed")
