from dataclasses import dataclass

from app.abc.message import Command
from app.bot.updates import BotUpdate, BotCallbackQuery, BotMessage


@dataclass(slots=True)
class Play(Command):
    update: BotUpdate


@dataclass(slots=True)
class CancelGame(Command):
    update: BotUpdate


@dataclass(slots=True)
class Join(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class CancelJoin(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class StartGame(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class SelectQuestion(Command):
    update: BotCallbackQuery
    question_id: int


@dataclass(slots=True)
class PressButton(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class Answer(Command):
    update: BotUpdate


@dataclass(slots=True)
class PeekAnswer(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class AcceptAnswer(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class RejectAnswer(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class StartRegistration(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class SetLeading(Command):
    update: BotCallbackQuery


@dataclass(slots=True)
class ShowRating(Command):
    update: BotUpdate


@dataclass(slots=True)
class VkRenderQuestions(Command):
    update: BotUpdate
    text: str
    message_id: int


@dataclass(slots=True)
class TelegramRenderQuestions(Command):
    update: BotUpdate
    text: str
    message_id: int


@dataclass(slots=True)
class HideQuestions(Command):
    update: BotUpdate
    message_ids: list[int]


@dataclass(slots=True)
class ShowPress(Command):
    update: BotUpdate
    text: str


@dataclass(slots=True)
class ShowTextQuestion(Command):
    update: BotUpdate
    text: str


@dataclass(slots=True)
class ShowPhotoQuestion(Command):
    update: BotUpdate
    text: str
    path: str
