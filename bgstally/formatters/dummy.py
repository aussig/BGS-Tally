from bgstally.activity import Activity
from bgstally.constants import DiscordActivity, FormatMode
from bgstally.debug import Debug
from bgstally.formatters.base import FieldActivityFormatterInterface
from bgstally.state import State
from bgstally.utils import _


class DummyActivityFormatter(FieldActivityFormatterInterface):
    """Activity formatter that outputs Lorum Ipsum
    """

    def __init__(self, state: State):
        """Instantiate class

        Args:
            state (State): The State object containing persistent values and settings
        """
        super(DummyActivityFormatter, self).__init__(state)


    def get_name(self) -> str:
        """Get the name of this formatter

        Returns:
            str: The name of this formatter for choosing in the UI
        """
        return _("Lorum Ipsum")


    def get_text(self, activity: Activity, activity_mode: DiscordActivity, discord: bool = False, system_names: list = None, lang: str = None) -> str:
        """Generate formatted text for a given instance of Activity. Must be implemented by subclasses.
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
        return "[Lorum Ipsum 1]\n \
                Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam a odio urna. Integer nec augue luctus, \
                fermentum massa mattis, euismod nibh. Cras volutpat nec risus non porta. Aliquam varius laoreet tempor.\n\n \
                [Lorum Ipsum 2]\n \
                Suspendisse sit amet ultricies nulla. Phasellus sed metus molestie, tincidunt felis in, sagittis est. \
                Aliquam orci augue, congue in sollicitudin at, viverra eu tortor. Phasellus faucibus condimentum risus\n\n \
                [Lorum Ipsum 3]\n \
                venenatis laoreet. Aliquam erat volutpat. Integer sagittis facilisis ipsum a tristique. Vivamus at tortor \
                erat. Vivamus nec interdum tortor. Praesent vitae odio sed tortor pulvinar varius."


    def get_fields(self, activity: Activity, activity_mode: DiscordActivity, system_names: list = None, lang: str = None) -> list[dict]:
        """Generate a list of discord embed fields, conforming to the embed field spec defined here:
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
        return [{'name': "Lorum Ipsum 1", 'value': "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam a odio urna. Integer nec augue luctus, \
                fermentum massa mattis, euismod nibh. Cras volutpat nec risus non porta. Aliquam varius laoreet tempor."},
                {'name': "Lorum Ipsum 2", 'value': "Suspendisse sit amet ultricies nulla. Phasellus sed metus molestie, tincidunt felis in, sagittis est. \
                Aliquam orci augue, congue in sollicitudin at, viverra eu tortor. Phasellus faucibus condimentum risus"},
                {'name': "Lorum Ipsum 3", 'value': "venenatis laoreet. Aliquam erat volutpat. Integer sagittis facilisis ipsum a tristique. Vivamus at tortor \
                erat. Vivamus nec interdum tortor. Praesent vitae odio sed tortor pulvinar varius."}
                ]
