import asyncio
import json
from random import randint
from typing import Iterable
from functools import cache

from aiohttp import ClientSession, ClientConnectorError
from orjson import orjson

from app.abc.cleanup_ctx import CleanupCTX
from app.bot.updates import BotUpdate
from app.bot.inline import InlineKeyboard
from app.bot.user import BotUser
from app.utils.runner import Runner
from app.bot.vk import loaders


class VkAPIAccessor(CleanupCTX):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session: ClientSession | None = None
        self._runner: Runner | None = None
        self._base_url = "https://api.vk.com"
        self._key: str | None = None
        self._server: str | None = None
        self._ts: int = 1
        self._v = "5.131"
        self._act = "a_check"
        self._wait = 25  # seconds
        self._access_token = self.app.config.vk.token
        self._group_id = self.app.config.vk.group_id

    @property
    def bot_id(self):
        return self._group_id

    async def on_startup(self):
        self._session = ClientSession()
        try:
            await self._set_long_poll_settings()
            await self._get_long_poll_service()
        except Exception as e:
            self.logger.error("Exception: ", exc_info=e)
        else:
            self._runner = Runner(self.poll)
            await self._runner.start()

    async def on_shutdown(self):
        await self._runner.stop()
        await self._session.close()

    async def poll(self):
        while True:
            try:
                for update in self._pack(await self.get_updates()):
                    await self.app.bot.dispatcher.handle(update)
            except (TimeoutError, ClientConnectorError, ConnectionRefusedError) as e:
                self.logger.warning(str(e), exc_info=e)
                await asyncio.sleep(5)

    async def get_updates(self) -> list[dict]:
        async with self._session.get(url=self._server, params=self._get_updates_params) as response:
            match (await response.json(content_type=response.content_type, loads=orjson.loads)):
                case {"ts": ts, "updates": updates} as data:
                    self.logger.debug('get_updates: ' + json.dumps(data, indent=2))
                    self._ts = ts
                    return updates
                case error:
                    self.logger.error('get_updates: ' + json.dumps(error, indent=2))
                    await self._get_long_poll_service()
        return []

    async def send_message(
            self,
            chat_id: int,
            text: str,
            attachment: str = '',
            inline_keyboard: InlineKeyboard | None = None
    ) -> int | None:
        async with self._session.get(
                url=self._url("messages.send"),
                params=self._params(
                    random_id=randint(-2147483648, 2147483648),
                    peer_ids=[chat_id],
                    message=text,
                    keyboard=self._inline_keyboard_markup(inline_keyboard),
                    attachment=attachment
                )
        ) as response:
            match (await response.json(content_type=response.content_type, loads=orjson.loads)):
                case {"response": [{"conversation_message_id": conversation_message_id}, *_]} as data:
                    self.logger.debug('send_message: ' + json.dumps(data, indent=2))
                    return conversation_message_id
                case error:
                    print(error)
                    self.logger.error('send_message: ' + json.dumps(error, indent=2))
                    return None

    async def send_event_answer(self, text: str, event_id: str, user_id: int, chat_id: int):
        async with self._session.get(
                self._url("messages.sendMessageEventAnswer"),
                params=self._params(
                    event_id=event_id,
                    user_id=user_id,
                    peer_id=chat_id,
                    event_data=self._snackbar(text),
                )
        ) as response:
            match (await response.json(content_type=response.content_type, loads=orjson.loads)):
                case {"response": _} as data:
                    self.logger.debug('send_event_answer: ' + json.dumps(data, indent=2))
                case error:
                    self.logger.error('send_event_answer: ' + json.dumps(error, indent=2))

    async def edit_message(
            self,
            chat_id: int,
            conversation_message_id: int,
            text: str | None = None,
            inline_keyboard: InlineKeyboard | None = None,
            remove_inline_keyboard: bool = False
    ):

        async with self._session.get(self._url("messages.edit"), params=self._params(
                conversation_message_id=conversation_message_id,
                message=text or await self._get_message_text(chat_id, conversation_message_id),
                peer_id=chat_id,
                **dict(
                    keyboard=self._inline_keyboard_markup(inline_keyboard)
                ) if inline_keyboard and not remove_inline_keyboard else {}
        )) as response:
            match (await response.json(content_type=response.content_type, loads=orjson.loads)):
                case {"response": 1} as data:
                    self.logger.debug('edit_message: ' + json.dumps(data, indent=2))
                case error:
                    self.logger.error('edit_message: ' + json.dumps(error, indent=2))

    async def delete_message(self, chat_id: int, message_id: int):
        response = await self._session.get(
            self._url("messages.delete"),
            params=self._params(
                cmids=str(message_id),
                delete_for_all=1,
                peer_id=chat_id
            )
        )
        match await response.json(content_type=response.content_type, loads=orjson.loads):
            case data:
                self.logger.debug('delete_message ' + json.dumps(data, indent=2))

    async def get_user(self, user_id: int) -> (str, str, str):
        async with self._session.get(
                self._url("users.get"),
                params=self._params(user_ids=[user_id], fields=['screen_name'])
        ) as response:
            match await response.json(content_type=response.content_type, loads=orjson.loads):
                case {"response": [
                    {
                        "first_name": first_name,
                        "last_name": last_name,
                        "screen_name": screen_name
                    }, *_
                ]} as data:
                    self.logger.debug('get_user ' + json.dumps(data, indent=2))
                    return BotUser(id=user_id, username=screen_name, first_name=first_name, last_name=last_name)
                case error:
                    self.logger.error('get_user: ' + json.dumps(error, indent=2))

    def _pack(self, updates: list[dict]) -> Iterable[BotUpdate]:
        for update in updates:
            match update:
                case {
                    "type": "message_new",
                    "object": {"message": {"text": text}}
                } as data if text.startswith("/") or text.startswith(f"[club{self._group_id}|"):
                    yield loaders.command_from_dict(**data)
                case {
                    "type": "message_new",
                    "object": {"message": {"text": text}}
                } as data if text:
                    yield loaders.message_from_dict(**data)
                case {"type": "message_event", "object": {"payload": _}} as data:
                    yield loaders.callback_query_from_dict(**data)
                case {
                    "type": "message_new",
                    "object": {"message": {"action": {"member_id": _}}}
                } as data:
                    yield loaders.action_from_dict(**data)
                case data:
                    self.logger.error('_pack: unsupported update type => : ' + json.dumps(data, indent=2))

    async def _set_long_poll_settings(self):
        async with self._session.get(
                url=self._url("groups.setLongPollSettings"),
                params=self._params(
                    group_id=self._group_id,
                    api_version=self._v,
                    enabled=1,
                    message_new=1,
                    message_event=1,
                    message_edit=0,
                    message_typing_state=0,
                    message_reply=0
                )
        ) as response:
            self.logger.debug('_set_long_poll_settings ' + json.dumps(
                await response.json(content_type=response.content_type, loads=orjson.loads), indent=2
            ))

    async def _get_long_poll_service(self):
        async with self._session.get(
                url=self._url("groups.getLongPollServer"),
                params=self._params(group_id=self._group_id)
        ) as response:
            match (await response.json(content_type=response.content_type, loads=orjson.loads)):
                case {"response": {"server": server, "key": key, "ts": ts}} as data:
                    self._server, self._key, self._ts = server, key, ts
                    self.logger.debug('_get_long_poll_service  ' + json.dumps(data, indent=2))
                case error:
                    self.logger.error('_get_long_poll_service ' + json.dumps(error, indent=2))

    async def get_upload_url(self, chat_id: int) -> str | None:
        async with self._session.post(
                self._url("photos.getMessagesUploadServer"),
                params=self._params(peer_id=chat_id)
        ) as response:
            match await response.json(content_type=response.content_type, loads=orjson.loads):
                case {"response": {"upload_url": upload_url}} as data:
                    self.logger.debug('_get_upload_url ' + json.dumps(data, indent=2))
                    return upload_url
                case error:
                    self.logger.error('_get_upload_url ' + json.dumps(error, indent=2))
            return None

    async def upload_photo(self, upload_url: str, photo_path: str) -> (str | None, str | None, str | None):
        with open(photo_path, mode='rb') as photo_file:
            async with self._session.post(upload_url, data=dict(photo=photo_file)) as response:
                # Иногда ВК присылает 'text/html'
                match await response.json(content_type=response.content_type, loads=orjson.loads):
                    case {"hash": photo_hash, "photo": photo, "server": server} as data:
                        self.logger.debug('_upload_photo: ' + json.dumps(data, indent=2))
                        return server, photo, photo_hash
                    case error:
                        self.logger.error('_upload_photo: ' + json.dumps(error, indent=2))
                return None, None, None

    async def save_photo(self, photo: str, server: str, photo_hash: str) -> str | None:
        response = await self._session.post(
            self._url('photos.saveMessagesPhoto'),
            params=self._params(server=server, hash=photo_hash, photo=photo)
        )
        match await response.json(content_type=response.content_type, loads=orjson.loads):
            case {"response": [{"id": media_id, "owner_id": owner_id}, *_]} as data:
                self.logger.debug('_save_photo: ' + json.dumps(data, indent=2))
                return f"photo{owner_id}_{media_id}"
            case error:
                self.logger.error('_save_photo: ' + json.dumps(error, indent=2))
        return None

    async def get_message_text(self, chat_id: int, conversation_message_id: int) -> str:
        async with self._session.get(self._url("messages.getByConversationMessageId"), params=self._params(
                peer_id=chat_id,
                conversation_message_ids=[conversation_message_id]
        )) as response:
            match await response.json(content_type=response.content_type, loads=orjson.loads):
                case {"response": {"count": 1, "items": [{"text": text}, *_]}} as data:
                    self.logger.debug('_get_message_text: ' + json.dumps(data, indent=2))
                    return text
                case error:
                    self.logger.error('_get_message_text: ' + json.dumps(error, indent=2))

    @staticmethod
    def _inline_keyboard_markup(inline_keyboard: InlineKeyboard | None = None) -> str:
        if not inline_keyboard:
            return ''
        return orjson.dumps({
            "one_time": False,
            "inline": True,
            "buttons": [
                [
                    {
                        "action": {
                            "type": "callback",
                            "payload": b.callback_data,
                            "label": b.text
                        },
                        # "color": b.color
                    } for b in line
                ] for line in inline_keyboard
            ]
        }).decode("utf-8")

    @cache
    def _url(self, method: str) -> str:
        return f"{self._base_url}/method/{method}"

    def _params(self, **params):
        return params | dict(access_token=self._access_token, v=self._v)

    @property
    def _get_updates_params(self):
        return dict(act=self._act, wait=self._wait, v=self._v, ts=self._ts, key=self._key)

    @staticmethod
    def _snackbar(text: str) -> str:
        """
        Возвращает описание всплывающего окна с текстом.
        :param text: текст всплывающего сообщения.
        :return: json-представление.
        """
        if not text:
            return ""
        return json.dumps({
            "type": "show_snackbar",
            "text": text
        })
