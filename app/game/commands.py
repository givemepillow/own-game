from dataclasses import dataclass

from app.abc.message import Command
from app.bot.updates import BotUpdate, BotCallbackQuery, BotMessage


@dataclass(frozen=True, slots=True)
class Play(Command):
    update: BotUpdate


@dataclass(frozen=True, slots=True)
class Finish(Command):
    update: BotUpdate


@dataclass(frozen=True, slots=True)
class Join(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class CancelJoin(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class StartGame(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class SelectQuestion(Command):
    update: BotCallbackQuery
    question_id: int


@dataclass(frozen=True, slots=True)
class PressAnswerButton(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class Answer(Command):
    update: BotMessage


@dataclass(frozen=True, slots=True)
class PeekAnswer(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class AcceptAnswer(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class RejectAnswer(Command):
    update: BotCallbackQuery
