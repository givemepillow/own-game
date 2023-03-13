from dataclasses import dataclass

from app.abc.message import Event
from app.bot.updates import BotCallbackQuery, BotUpdate, BotMessage


@dataclass(slots=True)
class QuestionFinished(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class GameFinished(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class WaitingForLeadingTimeout(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class RegistrationTimeout(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class WaitingSelectionTimeout(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class WaitingPressTimeout(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class WaitingForAnswerTimeout(Event):
    update: BotUpdate
    message_id: int


@dataclass(slots=True)
class WaitingForCheckingTimeout(Event):
    update: BotUpdate
    message_id: int
