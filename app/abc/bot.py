from abc import abstractmethod, ABC
from typing import Optional

from app.bot.inline import InlineKeyboard


class AbstractBot(ABC):
    @abstractmethod
    async def send(
            self,
            text: str,
            inline_keyboard: Optional[InlineKeyboard] = None, /, *,
            chat_id: int | None = None
    ) -> int | None:
        pass

    @abstractmethod
    async def delete(self, chat_id: int | None = None, message_id: int | None = None):
        pass

    @abstractmethod
    async def edit(
            self,
            text: str | None = None, /, *,
            inline_keyboard: InlineKeyboard | None = None,
            message_id: int | None = None,
            chat_id: int | None = None,
            remove_inline_keyboard: bool = False
    ):
        pass

    @abstractmethod
    async def callback(
            self,
            text: str = '', /, *,
            callback_query_id: str | None = None,
            chat_id: int | None = None,
            user_id: int | None = None
    ):
        pass

    @abstractmethod
    async def get_user(
            self,
            chat_id: int | None = None,
            user_id: int | None = None
    ):
        pass

