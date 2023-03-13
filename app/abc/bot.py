from abc import abstractmethod, ABC

from app.bot.inline import InlineKeyboard
from app.bot.user import BotUser


class AbstractBot(ABC):

    @property
    @abstractmethod
    def bot_id(self) -> int:
        pass

    @abstractmethod
    async def send(
            self,
            text: str,
            inline_keyboard: InlineKeyboard | None = None,
            /, *,
            chat_id: int | None = None
    ) -> int:
        pass

    @abstractmethod
    async def send_photo(
            self,
            photo_path: str,
            text: str = '',
            /, *,
            chat_id: int | None = None
    ) -> int:
        pass

    @abstractmethod
    async def send_voice(
            self,
            voice_path: str,
            text: str = '',
            /, *,
            chat_id: int | None = None
    ) -> int:
        pass

    @abstractmethod
    async def send_video(
            self,
            video_path: str,
            text: str = '',
            /, *,
            chat_id: int | None = None
    ) -> int:
        pass

    @abstractmethod
    async def delete(self, message_id: int | None = None, chat_id: int | None = None):
        pass

    @abstractmethod
    async def edit(
            self,
            text: str | None = None,
            /, *,
            inline_keyboard: InlineKeyboard | None = None,
            message_id: int | None = None,
            chat_id: int | None = None,
            remove_inline_keyboard: bool = False
    ):
        pass

    @abstractmethod
    async def callback(
            self,
            text: str = '',
            /, *,
            callback_query_id: str | None = None,
            chat_id: int | None = None,
            user_id: int | None = None
    ):
        pass

    @abstractmethod
    async def get_user(self, chat_id: int | None = None, user_id: int | None = None) -> BotUser:
        pass
