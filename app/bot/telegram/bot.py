from app.abc.bot import AbstractBot
from app.bot.telegram.accessor import TelegramAPIAccessor
from app.bot.inline import InlineKeyboard
from app.bot.updates import BotCallbackQuery, BotUpdate
from app.bot.user import BotUser


class TelegramBot(AbstractBot):

    def __init__(self, telegram_api: TelegramAPIAccessor, update: BotUpdate | None = None):
        self._api = telegram_api
        self._update = update

    @property
    def bot_id(self) -> int:
        return abs(self._api.bot_id)

    async def send(
            self,
            text: str,
            inline_keyboard: InlineKeyboard | None = None,
            /, *,
            chat_id: int | None = None
    ) -> int:
        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if chat_id is None:
            raise ValueError(f"Not enough params! ({chat_id=})")

        return await self._api.send_message(
            chat_id,
            text,
            inline_keyboard
        )

    async def send_photo(
            self,
            photo_path: str,
            text: str = '',
            /, *,
            chat_id: int | None = None
    ) -> int:
        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if chat_id is None:
            raise ValueError(f"Not enough params! ({chat_id=})")

        return await self._api.send_photo(chat_id, photo_path, text)

    async def send_voice(
            self,
            voice_path: str,
            text: str = '',
            /, *,
            chat_id: int | None = None
    ) -> int:
        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if chat_id is None:
            raise ValueError(f"Not enough params! ({chat_id=})")

        return await self._api.send_voice(chat_id, voice_path, text)

    async def send_video(
            self,
            video_path: str,
            text: str = '',
            /, *,
            chat_id: int | None = None
    ) -> int:
        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if chat_id is None:
            raise ValueError(f"Not enough params! ({chat_id=})")

        return await self._api.send_video(chat_id, video_path, text)

    async def edit(
            self,
            text: str | None = None,
            /, *,
            inline_keyboard: InlineKeyboard | None = None,
            photo_path: str | None = None,
            message_id: int | None = None,
            chat_id: int | None = None,
            remove_inline_keyboard: bool = False
    ):
        if inline_keyboard is None and text is None and remove_inline_keyboard is False:
            raise ValueError("Nothing to edit!")

        if isinstance(self._update, BotCallbackQuery):
            message_id = message_id or self._update.message_id

        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if not chat_id or not message_id:
            raise ValueError(f"Not enough params! ({chat_id=}, {message_id=})")

        if text is None:
            await self._api.edit_reply_markup(chat_id, message_id, inline_keyboard)
        else:
            await self._api.edit_message_text(
                chat_id,
                message_id,
                text,
                inline_keyboard,
                remove_inline_keyboard
            )

    async def delete(self, message_id: int | None = None, chat_id: int | None = None):
        if isinstance(self._update, BotCallbackQuery):
            message_id = message_id or self._update.message_id

        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if not chat_id or not message_id:
            raise ValueError(f"Not enough params! ({chat_id=}, {message_id=})")

        await self._api.delete_message(chat_id, message_id)

    async def callback(
            self,
            text: str = '',
            /, *,
            callback_query_id: str | None = None,
            chat_id: int | None = None,
            user_id: int | None = None
    ):
        if isinstance(self._update, BotCallbackQuery):
            callback_query_id = callback_query_id or self._update.callback_query_id

        if callback_query_id is None:
            raise ValueError(f"Not enough params! ({callback_query_id=})")

        await self._api.answer_callback_query(callback_query_id, text)

    async def get_user(self, chat_id: int | None = None, user_id: int | None = None) -> BotUser:
        if self._update is not None:
            chat_id, user_id = chat_id or self._update.chat_id, user_id or self._update.user_id

        if not chat_id or not user_id:
            raise ValueError(f"Not enough params! ({chat_id=}, {user_id=})")

        return await self._api.get_user(user_id=user_id, chat_id=chat_id)
