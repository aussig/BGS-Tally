from copy import deepcopy
from datetime import datetime

from requests import Response

from bgstally.constants import DiscordChannel, RequestMethod
from bgstally.debug import Debug
from bgstally.requestmanager import BGSTallyRequest
from thirdparty.colors import *

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S (game)"
URL_CLOCK_IMAGE = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/84/Fxemoji_u1F556.svg/240px-Fxemoji_u1F556.svg.png"


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

        for webhook in webhooks.values():
            webhook_url:str = webhook.get('url')
            if not self._is_webhook_valid(webhook_url): return

            # Get the previous state for this webhook's uuid from the passed in data, if it exists. Default to the state from the webhook manager
            specific_webhook_data:dict = {} if webhooks_data is None else webhooks_data.get(webhook.get('uuid', ""), webhook)

            utc_time_now:str = datetime.utcnow().strftime(DATETIME_FORMAT)
            data:dict = {'channel': channel, 'callback': callback, 'webhookdata': specific_webhook_data} # Data that's carried through the request queue and back to the callback

            # Fetch the previous post ID, if present, from the webhook data for the channel we're posting in. May be the default True / False value
            previous_messageid:str = specific_webhook_data.get(channel, None)

            if previous_messageid == "" or previous_messageid == None or previous_messageid == True or previous_messageid == False:
                # No previous post
                if discord_text == "": return

                discord_text += f"```ansi\n{blue(f'Posted at: {utc_time_now} | {self.bgstally.plugin_name} v{str(self.bgstally.version)}')}```"
                url:str = webhook_url
                payload:dict = {'content': discord_text, 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': []}

                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, callback=self._request_complete, data=data)
            else:
                # Previous post
                if discord_text != "":
                    discord_text += f"```ansi\n{green(f'Updated at: {utc_time_now} | {self.bgstally.plugin_name} v{str(self.bgstally.version)}')}```"
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

        Debug.logger.info(f"webhooks: {webhooks}")
        Debug.logger.info(f"webhooks_data: {webhooks_data}")
        Debug.logger.info(f"channel: {channel}")

        for webhook in webhooks.values():
            webhook_url:str = webhook.get('url')
            if not self._is_webhook_valid(webhook_url): return

            # Get the previous state for this webhook's uuid from the passed in data, if it exists. Default to the state from the webhook manager
            specific_webhook_data:dict = {} if webhooks_data is None else webhooks_data.get(webhook.get('uuid', ""), webhook)

            data:dict = {'channel': channel, 'callback': callback, 'webhookdata': specific_webhook_data} # Data that's carried through the request queue and back to the callback

            Debug.logger.info(f"data: {data}")

            # Fetch the previous post ID, if present, from the webhook data for the channel we're posting in. May be the default True / False value
            previous_messageid:str = specific_webhook_data.get(channel, None)

            Debug.logger.info(f"previous_messageid: {previous_messageid}")

            if previous_messageid == "" or previous_messageid == None or previous_messageid == True or previous_messageid == False:
                # No previous post
                if fields is None or fields == []: return

                embed:dict = self._get_embed(title, description, fields, False)
                url:str = webhook_url
                payload:dict = {'content': "", 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': [embed]}

                self.bgstally.request_manager.queue_request(url, RequestMethod.POST, payload=payload, params={'wait': 'true'}, callback=self._request_complete, data=data)
            else:
                # Previous post
                if fields is not None and fields != []:
                    embed:dict = self._get_embed(title, description, fields, True)
                    url:str = f"{webhook_url}/messages/{previous_messageid}"
                    payload:dict = {'content': "", 'username': self.bgstally.state.DiscordUsername.get(), 'embeds': [embed]}

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
                self.bgstally.request_manager.queue_request(request.data.get('webhook_url'), RequestMethod.POST, payload=request.payload, params={'wait': 'true'}, callback=self._request_complete, data=request.data)
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
        footer_timestamp:str = f"Updated at {datetime.utcnow().strftime(DATETIME_FORMAT)}" if update else f"Posted at {datetime.utcnow().strftime(DATETIME_FORMAT)}"
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


    def is_webhook_valid(self, channel:DiscordChannel):
        """
        Check a channel's webhook is valid
        """
        return self._is_webhook_valid(self._get_webhook(channel))


    def _get_webhook(self, channel:DiscordChannel):
        """
        Get the webhook url for the given channel
        """
        match channel:
            case DiscordChannel.BGS:
                return self.bgstally.state.DiscordBGSWebhook.get().strip()
            case DiscordChannel.CMDR_INFORMATION:
                return self.bgstally.state.DiscordCMDRInformationWebhook.get().strip()
            case DiscordChannel.FLEETCARRIER_MATERIALS:
                return self.bgstally.state.DiscordFCMaterialsWebhook.get().strip()
            case DiscordChannel.FLEETCARRIER_OPERATIONS:
                return self.bgstally.state.DiscordFCOperationsWebhook.get().strip()
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
