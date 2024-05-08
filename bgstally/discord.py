from copy import deepcopy
from datetime import datetime

from requests import Response

from bgstally.constants import DiscordChannel, RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest
from bgstally.utils import _, __, get_by_path
from thirdparty.colors import *

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Discord post limits: https://discord.com/developers/docs/resources/channel#create-message-jsonform-params
DISCORD_LIMIT_CONTENT = 2000

# Discord embed limits: https://discord.com/developers/docs/resources/channel#embed-object-embed-limits
DISCORD_LIMIT_EMBED_TITLE = 256
DISCORD_LIMIT_EMBED_DESCRIPTION = 4096
DISCORD_LIMIT_FIELDS = 25
DISCORD_LIMIT_EMBED_FIELD_NAME = 256
DISCORD_LIMIT_EMBED_FIELD_VALUE = 1024


URL_CLOCK_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Fxemoji_u1F556.svg/240px-Fxemoji_u1F556.svg.png"
URL_LOGO = "https://raw.githubusercontent.com/wiki/aussig/BGS-Tally/images/logo-square-white.png"


class Discord:
    """
    Handle Discord integration
    """
    def __init__(self, bgstally):
        self.bgstally = bgstally


    def post_plaintext(self, discord_text:str, webhooks_data:dict|None, channel:DiscordChannel, callback:callable):
        """
        Post plain text to Discord
        """
        # Start with latest webhooks from manager. Will contain True / False for each channel. Copy dict so we don't affect the webhook manager data.
        webhooks:dict = deepcopy(self.bgstally.webhook_manager.get_webhooks_as_dict(channel))

        # Aply Discord limits
        discord_text = self._truncate(discord_text, DISCORD_LIMIT_CONTENT)

        for webhook in webhooks.values():
            webhook_url:str = webhook.get('url')
            if not self._is_webhook_valid(webhook_url): continue

            # Get the previous state for this webhook's uuid from the passed in data, if it exists. Default to the state from the webhook manager
            specific_webhook_data:dict = {} if webhooks_data is None else webhooks_data.get(webhook.get('uuid', ""), webhook)

            utc_time_now:str = datetime.utcnow().strftime(DATETIME_FORMAT) + " " + __("game", lang=self.bgstally.state.discord_lang) # LANG: Discord date/time suffix for game time
            data:dict = {'channel': channel, 'callback': callback, 'webhookdata': specific_webhook_data} # Data that's carried through the request queue and back to the callback

            # Fetch the previous post ID, if present, from the webhook data for the channel we're posting in. May be the default True / False value
            previous_messageid:str = specific_webhook_data.get(channel, None)

            if previous_messageid == "" or previous_messageid == None or previous_messageid == True or previous_messageid == False:
                # No previous post
                if discord_text == "": return

                discord_text += ("```ansi\n" + blue(__("Posted at: {date_time} | {plugin_name} v{version}", lang=self.bgstally.state.discord_lang)) + "```").format(date_time=utc_time_now, plugin_name=self.bgstally.plugin_name, version=str(self.bgstally.version)) # LANG: Discord message footer, legacy text mode
                url:str = webhook_url
                payload:dict = {'content': discord_text, 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': []}

                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, callback=self._request_complete, data=data)
            else:
                # Previous post
                if discord_text != "":
                    discord_text += ("```ansi\n" + green(__("Updated at: {date_time} | {plugin_name} v{version}", lang=self.bgstally.state.discord_lang)) + "```").format(date_time=utc_time_now, plugin_name=self.bgstally.plugin_name, version=str(self.bgstally.version)) # LANG: Discord message footer, legacy text mode
                    url:str = f"{webhook_url}/messages/{previous_messageid}"
                    payload:dict = {'content': discord_text, 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': []}

                    self.bgstally.request_manager.queue_request(url, RequestMethod.PATCH, payload=payload, callback=self._request_complete, data=data)
                else:
                    url:str = f"{webhook_url}/messages/{previous_messageid}"

                    self.bgstally.request_manager.queue_request(url, RequestMethod.DELETE, callback=self._request_complete, data=data)


    def post_embed(self, title:str, description:str, fields:list, webhooks_data:dict|None, channel:DiscordChannel, callback:callable):
        """
        Post an embed to Discord
        """
        # Start with latest webhooks from manager. Will contain True / False for each channel. Copy dict so we don't affect the webhook manager data.
        webhooks:dict = deepcopy(self.bgstally.webhook_manager.get_webhooks_as_dict(channel))

        # Apply Discord limits
        title = self._truncate(title, DISCORD_LIMIT_EMBED_TITLE)
        title = self._truncate(description, DISCORD_LIMIT_EMBED_DESCRIPTION)
        fields = fields[0 : DISCORD_LIMIT_FIELDS]
        for field in fields:
            field['name'] = self._truncate(field.get('name', ""), DISCORD_LIMIT_EMBED_FIELD_NAME)
            field['value'] = self._truncate(field.get('value', ""), DISCORD_LIMIT_EMBED_FIELD_VALUE)

        for webhook in webhooks.values():
            webhook_url:str = webhook.get('url')
            if not self._is_webhook_valid(webhook_url): continue

            # Get the previous state for this webhook's uuid from the passed in data, if it exists. Default to the state from the webhook manager
            specific_webhook_data:dict = {} if webhooks_data is None else webhooks_data.get(webhook.get('uuid', ""), webhook)

            data:dict = {'channel': channel, 'callback': callback, 'webhookdata': specific_webhook_data} # Data that's carried through the request queue and back to the callback

            # Fetch the previous post ID, if present, from the webhook data for the channel we're posting in. May be the default True / False value
            previous_messageid:str = specific_webhook_data.get(channel, None)

            if previous_messageid == "" or previous_messageid == None or previous_messageid == True or previous_messageid == False:
                # No previous post
                if fields is None or fields == []: return

                embed:dict = self._get_embed(title, description, fields, False)
                url:str = webhook_url
                payload:dict = {
                    'content': "",
                    'username': self.bgstally.state.DiscordUsername.get(),
                    'avatar_url': URL_LOGO,
                    'embeds': [embed]}

                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, params={'wait': 'true'}, callback=self._request_complete, data=data)
            else:
                # Previous post
                if fields is not None and fields != []:
                    embed:dict = self._get_embed(title, description, fields, True)
                    url:str = f"{webhook_url}/messages/{previous_messageid}"
                    payload:dict = {
                        'content': "",
                        'username': self.bgstally.state.DiscordUsername.get(),
                        'avatar_url': URL_LOGO,
                        'embeds': [embed]}

                    self.bgstally.request_manager.queue_request(url, RequestMethod.PATCH, payload=payload, callback=self._request_complete, data=data)
                else:
                    url = f"{webhook_url}/messages/{previous_messageid}"

                    self.bgstally.request_manager.queue_request(url, RequestMethod.DELETE, callback=self._request_complete, data=data)


    def _request_complete(self, success:bool, response:Response, request:BGSTallyRequest):
        """
        A discord request has completed
        """
        if not success:
            if request.method == RequestMethod.PATCH:
                # If a PATCH (message update) fails, we can try again with a POST (message create). Note the URL is not the same.
                self.bgstally.request_manager.queue_request(get_by_path(request.data, ['webhookdata', 'url']), RequestMethod.POST, payload=request.payload, params={'wait': 'true'}, callback=self._request_complete, data=request.data)
            else:
                # If POSTs or DELETEs fail, we can't do anything more
                Debug.logger.warning(f"Unable to post message to Discord. Reason: '{response.reason}' Content: '{response.content}' URL: '{request.endpoint}'")

            return

        # This callback is the one we stashed in data - i.e. a callback to where the discord post request originated
        callback:callable = request.data.get('callback')
        if callback:
            if request.method == RequestMethod.DELETE:
                callback(request.data.get('channel'), request.data.get('webhookdata'), "")
            else:
                response_json:dict = response.json()
                callback(request.data.get('channel'), request.data.get('webhookdata'), response_json.get('id', ""))


    def _get_embed(self, title:str, description:str, fields:list, update:bool) -> dict:
        """
        Create a Discord embed JSON structure. If supplied, `fields` should be a List of Dicts, with each Dict containing 'name' (the field title) and
        'value' (the field contents)
        """
        footer_timestamp:str = (__("Updated at {date_time} (game)", lang=self.bgstally.state.discord_lang) if update else __("Posted at {date_time} (game)", lang=self.bgstally.state.discord_lang)).format(date_time=datetime.utcnow().strftime(DATETIME_FORMAT)) # LANG: Discord footer message, modern embed mode
        footer_version:str = f"{self.bgstally.plugin_name} v{str(self.bgstally.version)}"
        footer_pad:int = 108 - len(footer_version)

        embed:dict = {
            "color": 10682531,
            "footer": {
                "text": f"{footer_timestamp: <{footer_pad}}{footer_version}",
                "icon_url": URL_CLOCK_IMAGE
            }}

        if title: embed['title'] = title
        if description: embed['description'] = description
        if fields: embed['fields'] = fields

        return embed


    def valid_webhook_available(self, channel:DiscordChannel):
        """
        Check whether there is a valid webhook available for this channel
        """
        webhooks:dict = self.bgstally.webhook_manager.get_webhooks_as_dict(channel) # No need to deepcopy as we're not altering the data

        for webhook in webhooks.values():
            webhook_url:str = webhook.get('url')
            if self._is_webhook_valid(webhook_url): return True

        return False


    def _is_webhook_valid(self, webhook:str):
        """
        Do a basic check on a Discord webhook
        """
        return webhook.startswith('https://discordapp.com/api/webhooks/') \
                or webhook.startswith('https://discord.com/api/webhooks/') \
                or webhook.startswith('https://ptb.discord.com/api/webhooks/') \
                or webhook.startswith('https://canary.discord.com/api/webhooks/')


    def _truncate(self, text: str, length: int) -> str:
        """Truncate text with awareness of leading / training ```

        Args:
            text (str): The text to truncate
            length (int): The length to truncate at

        Returns:
            str: The truncated text
        """
        if len(text) > length:
            if text[:3] == "```": return text[:length - 4] + "…```"
            else: return text[:length - 1] + "…"
        else:
            return text
