import asyncio
import json
from functools import cache
from typing import Iterable

import orjson as orjson
from aiohttp import ClientSession, ClientConnectorError
from aiolimiter import AsyncLimiter

from app.bot.updates import BotUpdate
from app.bot.inline import InlineKeyboard
from app.bot.telegram import loaders
from app.bot.user import BotUser

from app.utils.runner import Runner

from app.abc.cleanup_ctx import CleanupCTX


class TelegramAPIAccessor(CleanupCTX):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session: ClientSession | None = None
        self._runner: Runner | None = None
        self._bot_username: str | None = None
        self._bot_id: int | None = None
        self._bot_token = self.app.config.telegram.token
        self._timeout = 30  # seconds
        self._limit = 50
        self._offset = 0
        self._limiter = AsyncLimiter(19)

    @property
    def bot_id(self):
        return self._bot_id

    async def on_startup(self):
        self._session = ClientSession(base_url='https://api.telegram.org')
        await self._get_me()
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
        response = await self._session.get(self._url("getUpdates"), params=self._params)
        match await response.json(loads=orjson.loads):
            case {'result': updates} as data:
                self.logger.debug('get_updates ' + json.dumps(data, indent=2))
                self._offset = (updates[-1]['update_id'] + 1) if updates else self._offset
                return updates
            case error:
                self.logger.error('get_updates ' + json.dumps(error, indent=2))
        return []

    async def get_user(self, user_id: int, chat_id: int) -> BotUser:
        response = await self._session.get(self._url("getChatMember"), params={
            "chat_id": chat_id,
            "user_id": user_id
        })
        match await response.json(loads=orjson.loads):
            case {'result': {'user': user}} as data:
                self.logger.debug('get_user ' + json.dumps(data, indent=2))
                return BotUser(
                    id=user_id,
                    username=user.get("username", ''),
                    first_name=user.get("first_name", ''),
                    last_name=user.get("last_name", '')
                )
            case error:
                self.logger.error('get_user ' + json.dumps(error, indent=2))

    async def edit_reply_markup(
            self,
            chat_id: int,
            message_id: int,
            inline_keyboard: InlineKeyboard | None = None
    ):
        async with self._limiter:
            response = await self._session.get(self._url("editMessageReplyMarkup"), params={
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": self._inline_keyboard_markup(inline_keyboard)
            })
            match await response.json(loads=orjson.loads):
                case data:
                    self.logger.debug('edit_reply_markup ' + json.dumps(data, indent=2))

    async def answer_callback_query(self, callback_query_id: str, text: str = ''):
        async with self._limiter:
            response = await self._session.get(self._url("answerCallbackQuery"), params={
                "callback_query_id": callback_query_id,
                "text": text,
                "show_alert": int(not bool(text)),
                "cache_time": 1
            })
            match await response.json(loads=orjson.loads):
                case data:
                    self.logger.debug('send_alert ' + json.dumps(data, indent=2))

    async def send_message(
            self,
            chat_id: int,
            text: str,
            inline_keyboard: InlineKeyboard | None = None
    ) -> int | None:
        async with self._limiter:
            response = await self._session.get(url=self._url("sendMessage"), params=dict(
                chat_id=chat_id,
                text=text,
                reply_markup=self._inline_keyboard_markup(inline_keyboard)
            ))
        match await response.json(loads=orjson.loads):
            case {"ok": False, "error_code": 429, "parameters": {
                "retry_after": retry_after
            }} as data:
                self.logger.error('send_message ' + json.dumps(data, indent=2))
                await asyncio.sleep(retry_after)
                await self.send_message(chat_id, text)  # RECURSIVE!
            case {"result": {"message_id": message_id}} as data:
                self.logger.debug('send_message ' + json.dumps(data, indent=2))
                return message_id
            case error:
                self.logger.debug('send_message ' + json.dumps(error, indent=2))
                return None

    async def send_photo(self, chat_id: int, photo_path: str, text: str = ''):
        with open(photo_path, mode='rb') as photo_file:
            async with self._limiter:
                response = await self._session.post(
                    self._url("sendPhoto"),
                    params={"chat_id": chat_id, "caption": text, "reply_markup": ''},
                    data={'photo': photo_file}
                )
        match await response.json(loads=orjson.loads):
            case data:
                self.logger.debug('send_photo ' + json.dumps(data, indent=2))

    async def edit_message_text(
            self,
            chat_id: int,
            message_id: int,
            text: str,
            inline_keyboard: InlineKeyboard | None = None,
            remove_inline_keyboard: bool = False
    ):
        async with self._limiter:
            response = await self._session.get(self._url("editMessageText"), params=dict(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                **dict(
                    reply_markup=self._inline_keyboard_markup(inline_keyboard)
                ) if inline_keyboard and not remove_inline_keyboard else {}
            ))
        match await response.json(content_type=response.content_type, loads=orjson.loads):
            case data:
                self.logger.debug('edit_message_text ' + json.dumps(data, indent=2))

    async def delete_message(self, chat_id: int, message_id: int):
        response = await self._session.get(
            self._url("deleteMessage"),
            params=dict(
                message_id=message_id,
                chat_id=chat_id
            )
        )
        match await response.json(content_type=response.content_type, loads=orjson.loads):
            case data:
                self.logger.debug('delete_message ' + json.dumps(data, indent=2))

    def _pack(self, updates: list[dict]) -> Iterable[BotUpdate]:
        for update in updates:
            match update:
                case {"message": {"text": text} as command} as data if text.startswith("/"):
                    command["text"] = text.replace(f"@{self._bot_username}", '')
                    yield loaders.command_from_dict(**data)
                case {"message": {"text": _}} as data:
                    yield loaders.message_from_dict(**data)
                case {"callback_query": _} as data:
                    yield loaders.callback_query_from_dict(**data)
                case {"message": {"new_chat_participant": _}} as data:
                    yield loaders.action_from_dict(**data)
                case data:
                    self.logger.info('_pack: undefined update type =>  ' + json.dumps(data, indent=2))

    async def _get_me(self):
        response = await self._session.get(self._url("getMe"))
        match (await response.json(loads=orjson.loads)):
            case {'result': {'username': username, "id": bot_id}} as data:
                self._bot_username = username
                self._bot_id = bot_id
                self.logger.debug('connect ' + json.dumps(data, indent=2))
            case error:
                self.logger.error('connect ' + json.dumps(error, indent=2))

    @staticmethod
    def _inline_keyboard_markup(inline_keyboard: InlineKeyboard | None = None) -> str:
        if not inline_keyboard:
            return ''
        return orjson.dumps({"inline_keyboard": [
            [
                {
                    'text': b.text,
                    "callback_data": orjson.dumps(b.callback_data).decode("utf-8")
                } for b in line
            ] for line in inline_keyboard
        ]
        }).decode("utf-8")

    @cache
    def _url(self, method: str):
        return f'/bot{self._bot_token}/{method}'

    @property
    def _params(self):
        return dict(timeout=self._timeout, limit=self._limit, offset=self._offset)