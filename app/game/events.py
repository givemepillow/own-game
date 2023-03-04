from dataclasses import dataclass

from app.abc.message import Event
from app.bot.updates import BotCallbackQuery, BotUpdate


@dataclass(frozen=True, slots=True)
class QuestionFinished(Event):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class GameFinished(Event):
    update: BotUpdate
