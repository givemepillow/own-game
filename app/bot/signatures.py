import re

from dataclasses import dataclass, field

from app.bot.enums import Origin, ChatType
from app.bot.updates import BotAction, BotUpdate, BotCommand, BotMessage, BotCallbackQuery


@dataclass
class AbstractSignature:
    origin: Origin
    chat_type: ChatType

    def match(self, update: BotUpdate) -> bool:
        return all((
            self.origin is None or self.origin == update.origin,
            self.chat_type is None or self.chat_type == update.chat_type
        ))


@dataclass
class MessageSignature(AbstractSignature):
    regex: str
    pattern: re.Pattern | None = None

    def __post_init__(self):
        if self.regex:
            self.pattern = re.compile(self.regex)

    def match(self, message: BotMessage) -> bool:
        return all((
            super().match(message),
            self.pattern is None or self.pattern.fullmatch(message.text)
        ))


@dataclass
class CommandSignature(AbstractSignature):
    commands: list[str]
    commands_set: set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.commands:
            self.commands_set.update(self.commands)

    def match(self, command: BotCommand) -> bool:
        return all((
            super().match(command),
            self.commands is None or command.command in self.commands
        ))


@dataclass
class CallbackQuerySignature(AbstractSignature):
    data_type: str

    def match(self, callback_query: BotCallbackQuery) -> bool:
        return all((
            super().match(callback_query),
            self.data_type is None or callback_query.callback_data.type == self.data_type

        ))


@dataclass
class ActionSignature(AbstractSignature):

    def match(self, callback_query: BotAction) -> bool:
        return super().match(callback_query)
