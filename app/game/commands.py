from dataclasses import dataclass

from app.abc.message import Command
from app.bot.updates import BotUpdate, BotCallbackQuery, BotMessage


@dataclass(frozen=True, slots=True)
class Play(Command):
    update: BotUpdate


@dataclass(frozen=True, slots=True)
class CancelGame(Command):
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
class PressButton(Command):
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


@dataclass(frozen=True, slots=True)
class StartRegistration(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class SetLeading(Command):
    update: BotCallbackQuery


@dataclass(frozen=True, slots=True)
class ShowRating(Command):
    update: BotUpdate


@dataclass(frozen=True, slots=True)
class VkRenderQuestions(Command):
    text: str
    update: BotUpdate


@dataclass(frozen=True, slots=True)
class TelegramRenderQuestions(Command):
    text: str
    update: BotUpdate


@dataclass(frozen=True, slots=True)
class NextQuestion(Command):
    update: BotUpdate
