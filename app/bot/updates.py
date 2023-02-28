from abc import abstractmethod, ABC
from dataclasses import dataclass

from app.bot.inline import CallbackData
from app.bot.enums import Origin, ChatType, ActionType


@dataclass(frozen=True, slots=True)
class BotUpdate(ABC):
    user_id: int
    chat_id: int
    chat_type: ChatType | str
    origin: Origin | str

    @classmethod
    @abstractmethod
    def load(cls, **data):
        pass

    def __str__(self):
        return f"{self.__class__.__name__}[{self.origin}]"


@dataclass(frozen=True, slots=True)
class BotMessage(BotUpdate, ABC):
    text: str

    def __str__(self):
        return f"{super()}({self.text[0:10]}{'' if len(self.text) < 10 else '...'})"


@dataclass(frozen=True, slots=True)
class BotCommand(BotUpdate, ABC):
    command: str

    def __str__(self):
        return f"{super()}({self.command})"


@dataclass(frozen=True, slots=True)
class BotCallbackQuery(BotUpdate, ABC):
    callback_data: CallbackData
    callback_query_id: str
    message_id: int

    def __str__(self):
        return f"{super()}({self.callback_data.type}: {self.callback_data.value})"


@dataclass(frozen=True, slots=True)
class BotAction(BotUpdate, ABC):
    action: ActionType
    target_id: int

    def __str__(self):
        return f"{super()}({self.action})"
