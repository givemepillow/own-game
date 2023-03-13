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
    WAITING_FOR_CAT_IN_BAG_ANSWER: str = auto()  # Ожидание ответа для вопроса кот в мешке.
    WAITING_FOR_CAT_CATCHER: str = auto()  # Ждём кому достанется кот в мешке.
    WAITING_FOR_CAT_IN_BAG_CHECKING: str = auto()  # Ожидание решения ведущего.
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
    WAIT_PRESS = 20
    WAIT_ANSWER = 10
    WAIT_CHECKING = 25
    PAUSE = 6
    TEXT_QUESTION = 12
    PHOTO_QUESTION = 10
    AUDIO_QUESTION = 10
    VIDEO_QUESTION = 20
    LITTLE_PAUSE = 4
