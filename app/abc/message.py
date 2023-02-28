from abc import ABC
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Message(ABC):
    """
    Сообщение, которым будут между собой обмениваться
    обработчики через шину сообщений.
    """
    pass


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
