from enum import StrEnum, auto

from app.bot.inline import InlineKeyboard, InlineButton, CallbackData
from app.game.models import Theme, Question


class CallbackType(StrEnum):
    JOIN: str = auto()
    CANCEL_JOIN: str = auto()
    START_GAME: str = auto()
    SELECT_QUESTION: str = auto()
    PRESS_BUTTON: str = auto()
    PEEK: str = auto()
    ACCEPT: str = auto()
    REJECT: str = auto()
    BECOME_LEADING: str = auto()


def make_registration(current_players_number: int = 0) -> InlineKeyboard:
    keyboard = InlineKeyboard()
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
            for q in sorted(t.questions, reverse=False)
        ))
    return keyboard


def make_vertical(theme: Theme, already_selected: list[int]):
    def _question_button(q: Question):
        return InlineButton(str(q.cost), CallbackData(
            CallbackType.SELECT_QUESTION,
            f"{q.id}"
        )) if q.id not in already_selected else InlineButton()

    keyboard = InlineKeyboard()
    questions = sorted(theme.questions, reverse=False)
    keyboard.add(_question_button(questions[0]), _question_button(questions[1]),  _question_button(questions[2]))
    keyboard.add(_question_button(questions[3]), InlineButton(), _question_button(questions[4]))
    return keyboard


def make_answer_button():
    keyboard = InlineKeyboard()
    keyboard.add(InlineButton("Ответить", CallbackData(CallbackType.PRESS_BUTTON)))
    return keyboard


def make_checker():
    keyboard = InlineKeyboard()
    keyboard.add(InlineButton("Подглядеть ответ", CallbackData(CallbackType.PEEK)))
    keyboard.add(
        InlineButton("Принять", CallbackData(CallbackType.ACCEPT)),
        InlineButton("Отклонить", CallbackData(CallbackType.REJECT))
    )
    return keyboard


def make_become_leading():
    keyboard = InlineKeyboard()
    keyboard.add(InlineButton("Я буду ведущим.", CallbackData(CallbackType.BECOME_LEADING)))
    return keyboard
