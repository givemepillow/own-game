from enum import StrEnum, auto, IntEnum

from app.bot.enums import Origin


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
    REGISTRATION = 45
    WAIT_SELECTION = 20
    WAIT_PRESS = 20
    WAIT_ANSWER = 15
    WAIT_CHECKING = 25
    PAUSE = 6
    LITTLE_PAUSE = 4


class GameConfig(IntEnum):
    MIN_PLAYERS_COUNT = 2
    MAX_VK_PLAYERS_COUNT = 7
    MAX_TELEGRAM_PLAYERS_COUNT = 7
    GAME_THEMES_COUNT = 2

    @classmethod
    def MAX_PLAYERS_COUNT(cls, origin: Origin):  # noqa
        if origin == Origin.VK:
            return cls.MAX_VK_PLAYERS_COUNT
        return cls.MAX_TELEGRAM_PLAYERS_COUNT
