from enum import StrEnum, auto, IntEnum


class GameState(StrEnum):
    """
    Состояния игры.
    """
    WAITING_FOR_LEADING: str = auto()  # # Ожидание ведущего (кто им станет).
    REGISTRATION: str = auto()  # Регистрация на игру.
    QUESTION_SELECTION: str = auto()  # Выбор вопроса.
    WAITING_FOR_PRESS: str = auto()  # Ожидание нажатия на кнопку для ответа на вопрос.
    WAITING_FOR_ANSWER: str = auto()  # Ожидание ответа.
    WAITING_FOR_CHECKING: str = auto()  # Ожидание решения ведущего.


class QuestionComplexity(IntEnum):
    """
    Сложность вопросов и соответсвующая цена
    """
    VERY_EASY = 100
    EASY = 200
    MEDIUM = 300
    DIFFICULT = 400
    VERY_DIFFICULT = 500


class Delay(IntEnum):
    WAIT_LEADING = 15
    REGISTRATION = 30
    WAIT_SELECTION = 20
    WAIT_PRESS = 25
    WAIT_ANSWER = 15
    WAIT_CHECKING = 25
    PAUSE = 7
