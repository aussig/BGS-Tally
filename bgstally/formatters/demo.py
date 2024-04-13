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


    def get_text(self, activity: Activity, activity_mode: DiscordActivity, discord: bool = False, system_names: list = None, lang: str = None) -> str:
        """Generate formatted text for a demonstration Activity with demo data only.
        This method is also used to display the preview text on-screen in activity windows.

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            discord (bool, optional): True if the destination is Discord (so can include Discord-specific formatting such
            as ```ansi blocks and UTF8 emoji characters), False if not. Defaults to False.
            system_names (list, optional): A list of system names to restrict the output for. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            str: The output text
        """
        # Override the passed in Activity object with one containing demo data only
        demo_activity: Activity = Activity(self.bgstally, None, True)

        return super().get_text(demo_activity, activity_mode, discord, system_names, lang)


    def get_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list[dict]:
        """Generate a list of discord embed fields for a demonstration Activity with demo data only, conforming to the embed field spec defined here:
        https://birdie0.github.io/discord-webhooks-guide/structure/embed/fields.html - i.e. each field should be a dict
        containing 'name' and 'value' str keys, and optionally an 'inline' bool key

        Args:
            activity (Activity): The Activity object containing the activity to post
            activity_mode (DiscordActivity): Determines the type(s) of activity to post
            system_names (list, optional): A list of system names to restrict the output for. Defaults to None.
            lang (str, optional): The language code for this post. Defaults to None.

        Returns:
            list[dict]: A list of dicts, each containing an embed field containing 'name' and 'value' str keys, and optionally an 'inline' bool key
        """
        # Override the passed in Activity object with one containing demo data only
        demo_activity: Activity = Activity(self.bgstally, None, True)

        return super().get_feilds(demo_activity, activity_mode, system_names, lang)
