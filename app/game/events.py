from dataclasses import dataclass

from app.abc.message import Event
from app.bot.updates import BotCallbackQuery, BotUpdate


@dataclass(slots=True)
class QuestionFinished(Event):
    update: BotCallbackQuery


@dataclass(slots=True)
class GameFinished(Event):
    update: BotUpdate


@dataclass(slots=True)
class GameTimeout(Event):
    update: BotUpdate


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
    update: BotCallbackQuery


@dataclass(slots=True)
class WaitingPressTimeout(Event):
    update: BotCallbackQuery


@dataclass(slots=True)
class WaitingAnswerTimeout(Event):
    update: BotUpdate


@dataclass(slots=True)
class WaitingForCheckingTimeout(Event):
    update: BotCallbackQuery
