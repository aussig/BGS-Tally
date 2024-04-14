from bgstally.activity import Activity
from bgstally.constants import DiscordActivity, FormatMode
from bgstally.debug import Debug
from bgstally.formatters.default import DefaultActivityFormatter
from bgstally.utils import _


class DemoActivityFormatter(DefaultActivityFormatter):
    """Activity formatter that outputs Lorum Ipsum
    """

    def __init__(self, bgstally):
        """Instantiate class

        Args:
            bgstally (BGSTally): The BGSTally object
        """
        super().__init__(bgstally)


    def get_name(self) -> str:
        """Get the name of this formatter

        Returns:
            str: The name of this formatter for choosing in the UI
        """
        return _("Demo Data Only")


    def is_visible(self) -> bool:
        """Should this formatter be visible to the user as a choice. Only return True for this
        formatter if we are running in dev mode.

        Returns:
            bool: True if visible, false if not
        """
        return self.bgstally.dev_mode


    def get_text(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> str:
        """Generate formatted text for a given instance of Activity. Must be implemented by subclasses.
        This method is used for getting the text for the 'copy and paste' function, and for direct posting
        to Discord for those Formatters that use text style posts (vs Discord embed style posts)

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            discord (bool, optional): True if the destination is Discord (so can include Discord-specific formatting such
            as ```ansi blocks and UTF8 emoji characters), False if not. Defaults to False.
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            str: The output text
        """
        # Override the passed in Activity object with one containing demo data only
        demo_activity: Activity = Activity(self.bgstally, None, True)

        return super().get_text(demo_activity, activity_mode, system_names, lang)


    def get_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list[dict]:
        """Generate a list of discord embed fields for a demonstration Activity with demo data only, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. If None, all systems are included. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            list[dict]: A list of dicts, each containing an embed field containing 'name' and 'value' str keys, and optionally an 'inline' bool key
        """
        # Override the passed in Activity object with one containing demo data only
        demo_activity: Activity = Activity(self.bgstally, None, True)

        return super().get_fields(demo_activity, activity_mode, system_names, lang)
