from dataclasses import dataclass

from app.abc.message import Event
from app.bot.updates import BotCallbackQuery


@dataclass(frozen=True, slots=True)
class QuestionFinished(Event):
    update: BotCallbackQuery
