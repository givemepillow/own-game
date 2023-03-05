from abc import ABC
from dataclasses import dataclass, asdict
from typing import Self

from dacite import from_dict
from orjson import orjson

from app.game.models import DelayedMessage


@dataclass(frozen=True, slots=True)
class Message(ABC):
    """
    Сообщение, которым будут между собой обмениваться
    обработчики через шину сообщений.
    """

    @classmethod
    def from_model(cls, delayed_message: DelayedMessage) -> Self:
        raw_message = orjson.loads(delayed_message.data)
        for sub_subclass in (s2 for s1 in cls.__subclasses__() for s2 in s1.__subclasses__()):
            if sub_subclass.__name__ == delayed_message.name:
                return from_dict(sub_subclass, raw_message)

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def __bytes__(self) -> bytes:
        return orjson.dumps((self.__class__.__name__, asdict(self)))


@dataclass(frozen=True, slots=True)
class Event(Message, ABC):
    """
    Сообщения условно делятся на события и на команды.
    """
    pass


@dataclass(frozen=True, slots=True)
class Command(Message, ABC):
    """
    Сообщения условно делятся на команды и на события.
    """
    pass
