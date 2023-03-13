"""
Декораторы для наглядного задания сигнатуры обработчиков обновлений бота.
"""

from typing import Type, Callable

from app.bot.signatures import (
    CallbackQuerySignature,
    CommandSignature,
    MessageSignature,
    ActionSignature
)

from app.bot.enums import Origin, ChatType

__all__ = ['message', 'command', 'callback_query', 'action']

from app.bot.updates import BotCallbackQuery, BotAction, BotMessage, BotCommand

from app.abc.bot_view import BotView


def message(
        regex: str | None = None,
        chat_type: ChatType | None = None,
        origin: Origin | None = None
) -> Callable[[Type[BotView]], Type[BotView]]:
    """
    Устанавливает сигнатуру для обработчика сообщений.
    :param regex: регулярное выражение (python re)
    :param chat_type: приватный или групповой.
    :param origin: вк или телеграм.
    :return: обработчик с заданной сигнатурой.
    """

    def _message_view(view: Type[BotView]):
        view.signature = MessageSignature(
            regex=regex,
            chat_type=chat_type,
            origin=origin
        )
        view.update_type = BotMessage

        return view

    return _message_view


def command(
        commands: list[str] | None = None,
        chat_type: ChatType | None = None,
        origin: Origin | None = None
) -> Callable[[Type[BotView]], Type[BotView]]:
    """
    Устанавливает сигнатуру для обработчика команд.
    :param commands: список команд.
    :param chat_type: приватный или групповой.
    :param origin: вк или телеграм.
    :return: обработчик с заданной сигнатурой.
    """

    def _command_view(view: Type[BotView]):
        view.signature = CommandSignature(
            commands=commands,
            chat_type=chat_type,
            origin=origin
        )
        view.update_type = BotCommand

        return view

    return _command_view


def action(
        chat_type: ChatType | None = None,
        origin: Origin | None = None
) -> Callable[[Type[BotView]], Type[BotView]]:
    """
    Устанавливает сигнатуру для обработчика событий.
    :param chat_type: приватный или групповой.
    :param origin: вк или телеграм.
    :return: обработчик с заданной сигнатурой.
    """

    def _action_view(view: Type[BotView]):
        view.signature = ActionSignature(
            chat_type=chat_type,
            origin=origin
        )
        view.update_type = BotAction

        return view

    return _action_view


def callback_query(
        chat_type: ChatType | None = None,
        origin: Origin | None = None,
        data_type: str | None = None
) -> Callable[[Type[BotView]], Type[BotView]]:
    """
    Устанавливает сигнатуру для обработчика событий.
    :param chat_type: приватный или групповой.
    :param origin: вк или телеграм.
    :param data_type: тип данных - CallbackData.type.
    :return: обработчик с заданной сигнатурой.
    """

    def _callback_query_view(view: Type[BotView]):
        view.signature = CallbackQuerySignature(
            chat_type=chat_type,
            origin=origin,
            data_type=data_type
        )
        view.update_type = BotCallbackQuery

        return view

    return _callback_query_view
