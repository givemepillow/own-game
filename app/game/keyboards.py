from enum import StrEnum, auto

from app.bot.inline import InlineKeyboard, InlineButton, CallbackData
from app.game.models import Theme


class CallbackType(StrEnum):
    JOIN: str = auto()
    CANCEL_JOIN: str = auto()
    START_GAME: str = auto()
    SELECT_QUESTION: str = auto()
    PRESS_ANSWER: str = auto()
    PEEK: str = auto()
    ACCEPT: str = auto()
    REJECT: str = auto()


def make_registration(current_players_number: int = 0) -> InlineKeyboard:
    keyboard = InlineKeyboard()
    keyboard.add(InlineButton(f"Игроков зарегистрировано: {current_players_number}"))
    keyboard.add(
        InlineButton("Играю", CallbackData(CallbackType.JOIN)),
        InlineButton("Не играю", CallbackData(CallbackType.CANCEL_JOIN))
    )
    if current_players_number > 0:
        keyboard.add(InlineButton("Начать", CallbackData(CallbackType.START_GAME)))
    return keyboard


def make_table(themes: list[Theme], already_selected: list[int]):
    keyboard = InlineKeyboard()
    for t in themes:
        keyboard.add(InlineButton(t.title))
        keyboard.add(*(
            InlineButton(str(q.cost), CallbackData(
                CallbackType.SELECT_QUESTION,
                f"{q.id}"
            ))
            if q.id not in already_selected else InlineButton()
            for q in t.questions
        ))
    return keyboard


def make_answer_button():
    keyboard = InlineKeyboard()
    keyboard.add(InlineButton("Ответить", CallbackData(CallbackType.PRESS_ANSWER)))
    return keyboard


def make_checker():
    keyboard = InlineKeyboard()
    keyboard.add(InlineButton("Подглядеть ответ", CallbackData(CallbackType.PEEK)))
    keyboard.add(
        InlineButton("Принять", CallbackData(CallbackType.ACCEPT)),
        InlineButton("Отклонить", CallbackData(CallbackType.REJECT))
    )
    return keyboard
