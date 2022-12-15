from datetime import datetime
from typing import Dict, List

import requests

from bgstally.constants import DiscordChannel
from bgstally.debug import Debug

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S (game)"
URL_CLOCK_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Fxemoji_u1F556.svg/240px-Fxemoji_u1F556.svg.png"

class Discord:
    """
    Handle Discord integration
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally


    def post_plaintext(self, discord_text: str, previous_messageid: str, channel: DiscordChannel):
        """
        Post plain text to Discord
        """
        webhook_url = self._get_webhook(channel)
        if not self._is_webhook_valid(webhook_url): return

        utc_time_now = datetime.utcnow().strftime(DATETIME_FORMAT)
        new_messageid = previous_messageid

        if previous_messageid == "" or previous_messageid == None:
            # No previous post
            if discord_text != "":
                discord_text += f"```md\n# Posted at: {utc_time_now}```" # Blue text instead of gray
                url = webhook_url
                response = requests.post(url=url, params={'wait': 'true'}, json={'content': discord_text, 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': []})
                if response.ok:
                    # Store the Message ID
                    response_json = response.json()
                    new_messageid = response_json['id']
                else:
                    Debug.logger.error(f"Unable to create new discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")

        else:
            # Previous post, amend or delete it
            if discord_text != '':
                discord_text += f"```diff\n+ Updated at: {utc_time_now}```"
                url = f"{webhook_url}/messages/{previous_messageid}"
                response = requests.patch(url=url, json={'content': discord_text, 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': []})
                if not response.ok:
                    new_messageid = ""
                    Debug.logger.error(f"Unable to update previous discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")

                    # Try to post new message instead
                    url = webhook_url
                    response = requests.post(url=url, params={'wait': 'true'}, json={'content': discord_text, 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': []})
                    if response.ok:
                        # Store the Message ID
                        response_json = response.json()
                        new_messageid = response_json['id']
                    else:
                        Debug.logger.error(f"Unable to create new discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")
            else:
                url = f"{webhook_url}/messages/{previous_messageid}"
                response = requests.delete(url=url)
                if response.ok:
                    # Clear the Message ID
                    new_messageid = ""
                else:
                    Debug.logger.error(f"Unable to delete previous discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")

        return new_messageid


    def post_embed(self, title: str, description: str, fields: List, previous_messageid: str, channel: DiscordChannel):
        """
        Post an embed to Discord
        """
        webhook_url = self._get_webhook(channel)
        if not self._is_webhook_valid(webhook_url): return

        new_messageid = previous_messageid

        if previous_messageid == "" or previous_messageid == None:
            # No previous post
            embed = self._get_embed(title, description, fields, False)
            url = webhook_url
            response = requests.post(url=url, params={'wait': 'true'}, json={'content': "", 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': [embed]})
            if response.ok:
                # Store the Message ID
                response_json = response.json()
                new_messageid = response_json['id']
            else:
                Debug.logger.error(f"Unable to create new discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")

        else:
            # Previous post, amend or delete it
            if fields is not None:
                embed = self._get_embed(title, description, fields, True)
                url = f"{webhook_url}/messages/{previous_messageid}"
                response = requests.patch(url=url, json={'content': "", 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': [embed]})
                if not response.ok:
                    new_messageid = ""
                    Debug.logger.error(f"Unable to update previous discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")

                    # Try to post new message instead
                    url = webhook_url
                    response = requests.post(url=url, params={'wait': 'true'}, json={'content': "", 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': [embed]})
                    if response.ok:
                        # Store the Message ID
                        response_json = response.json()
                        new_messageid = response_json['id']
                    else:
                        Debug.logger.error(f"Unable to create new discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")
            else:
                url = f"{webhook_url}/messages/{previous_messageid}"
                response = requests.delete(url=url)
                if response.ok:
                    # Clear the Message ID
                    new_messageid = ""
                else:
                    Debug.logger.error(f"Unable to delete previous discord post. Reason: '{response.reason}' Content: '{response.content}' URL: '{url}'")

        return new_messageid


    def _get_embed(self, title: str, description: str, fields: List, update: bool):
        """
        Create a Discord embed JSON structure. If supplied, `fields` should be a List of Dicts, with each Dict containing 'name' (the field title) and
        'value' (the field contents)
        """
        footer_timestamp = f"Updated at {datetime.utcnow().strftime(DATETIME_FORMAT)}" if update else f"Posted at {datetime.utcnow().strftime(DATETIME_FORMAT)}"
        footer_version = f"{self.bgstally.plugin_name} v{str(self.bgstally.version)}"
        footer_pad = 108 - len(footer_version)

        embed:Dict = {
            "color": 10682531,
            "footer": {
                "text": f"{footer_timestamp: <{footer_pad}}{footer_version}",
                "icon_url": URL_CLOCK_IMAGE
            }}

        if title: embed['title'] = title
        if description: embed['description'] = description
        if fields: embed['fields'] = fields

        return embed


    def is_webhook_valid(self, channel: DiscordChannel):
        """
        Check a channel's webhook is valid
        """
        return self._is_webhook_valid(self._get_webhook(channel))


    def _get_webhook(self, channel: DiscordChannel):
        """
        Get the webhook url for the given channel
        """
        match channel:
            case DiscordChannel.BGS:
                return self.bgstally.state.DiscordBGSWebhook.get().strip()
            case DiscordChannel.FLEETCARRIER:
                return self.bgstally.state.DiscordFCJumpWebhook.get().strip()
            case DiscordChannel.THARGOIDWAR:
                return self.bgstally.state.DiscordTWWebhook.get().strip()


    def _is_webhook_valid(self, webhook:str):
        """
        Do a basic check on a Discord webhook
        """
        return webhook.startswith('https://discordapp.com/api/webhooks/') \
                or webhook.startswith('https://discord.com/api/webhooks/') \
                or webhook.startswith('https://ptb.discord.com/api/webhooks/') \
                or webhook.startswith('https://canary.discord.com/api/webhooks/')
