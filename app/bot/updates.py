from abc import ABC
from dataclasses import dataclass

from app.bot.inline import CallbackData
from app.bot.enums import Origin, ChatType, ActionType
from app.bot.user import BotUser


@dataclass(frozen=True, slots=True)
class BotUpdate(ABC):
    user_id: int
    chat_id: int
    chat_type: ChatType | str
    origin: Origin | str
    user: BotUser | None

    def __str__(self):
        return f"{self.__class__.__name__}[{self.origin}]"


@dataclass(frozen=True, slots=True)
class BotMessage(BotUpdate):
    text: str

    def __str__(self):
        return f"{self.__class__.__name__}[{self.origin}]" \
               f"({self.text[0:10]}{'' if len(self.text) < 10 else '...'})"


@dataclass(frozen=True, slots=True)
class BotCommand(BotUpdate):
    command: str

    def __str__(self):
        return f"{self.__class__.__name__}[{self.origin}]({self.command})"


@dataclass(frozen=True, slots=True)
class BotCallbackQuery(BotUpdate):
    callback_data: CallbackData
    callback_query_id: str
    message_id: int

    def __str__(self):
        return f"{self.__class__.__name__}[{self.origin}]({self.callback_data.type}: {self.callback_data.value})"


@dataclass(frozen=True, slots=True)
class BotAction(BotUpdate):
    action: ActionType
    target_id: int

    def __str__(self):
        return f"{self.__class__.__name__}[{self.origin}]({self.action})"
