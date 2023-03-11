from app.abc.bot import AbstractBot
from app.bot.user import BotUser
from app.bot.vk.accessor import VkAPIAccessor
from app.bot.inline import InlineKeyboard
from app.bot.updates import BotCallbackQuery, BotUpdate


class VkBot(AbstractBot):
    def __init__(self, api: VkAPIAccessor, update: BotUpdate | None = None):
        self._api = api
        self._update = update

    @property
    def bot_id(self) -> int:
        return abs(self._api.bot_id)

    async def get_user(self, chat_id: int | None = None, user_id: int | None = None) -> BotUser:
        if self._update is not None:
            user_id = user_id or self._update.user_id

        if not user_id:
            raise ValueError(f"Not enough params! ({user_id=})")

        return await self._api.get_user(user_id)

    async def send(
            self,
            text: str,
            inline_keyboard: InlineKeyboard | None = None,
            photo_path: str | None = None,
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
            inline_keyboard=inline_keyboard
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

        upload_url = await self._api.get_photos_upload_url(chat_id)
        server, photo, photo_hash = await self._api.upload_photo(upload_url, photo_path)
        attachment = await self._api.save_photo(photo, server, photo_hash)

        return await self._api.send_message(chat_id, text=text, attachment=attachment)

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

        upload_url = await self._api.get_voice_upload_url(chat_id)
        file = await self._api.upload_doc(upload_url, voice_path)

        attachment = await self._api.save_voice(file)

        return await self._api.send_message(chat_id, text=text, attachment=attachment)

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

        upload_url = await self._api.get_doc_upload_url(chat_id)

        file = await self._api.upload_doc(upload_url, video_path)

        attachment = await self._api.save_doc(file)

        return await self._api.send_message(chat_id, text=text, attachment=attachment)

    async def delete(self, message_id: int | None = None, chat_id: int | None = None):
        if isinstance(self._update, BotCallbackQuery):
            message_id = message_id or self._update.message_id

        if self._update is not None:
            chat_id = chat_id or self._update.chat_id

        if not chat_id or not message_id:
            raise ValueError(f"Not enough params! ({chat_id=}, {message_id=})")

        await self._api.delete_message(chat_id, message_id)

    async def edit(
            self,
            text: str | None = None,
            /, *,
            inline_keyboard: InlineKeyboard | None = None,
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

        await self._api.edit_message(
            chat_id=chat_id,
            conversation_message_id=message_id,
            text=text,
            inline_keyboard=inline_keyboard,
            remove_inline_keyboard=remove_inline_keyboard
        )

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

        if self._update:
            chat_id, user_id = chat_id or self._update.chat_id, user_id or self._update.user_id

        if callback_query_id is None or chat_id is None or user_id is None:
            raise ValueError(f"Not enough params! ({callback_query_id=}, {chat_id=}, {user_id=})")

        await self._api.send_event_answer(
            text=text,
            event_id=callback_query_id,
            user_id=user_id,
            chat_id=chat_id
        )
