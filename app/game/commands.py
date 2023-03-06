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
    update: BotCallbackQuery


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


# @dataclass(slots=True)
# class ShowPress(Command):
#     update: BotCallbackQuery
#     text: str


@dataclass(slots=True)
class VkRenderQuestions(Command):
    text: str
    update: BotCallbackQuery


@dataclass(slots=True)
class TelegramRenderQuestions(Command):
    text: str
    update: BotCallbackQuery


@dataclass(slots=True)
class HideQuestions(Command):
    update: BotCallbackQuery
    message_ids: list[int]


@dataclass(slots=True)
class HideQuestionsTimeout(Command):
    update: BotCallbackQuery
    message_ids: list[int]
