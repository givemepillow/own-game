from enum import StrEnum, auto, IntEnum


class GameState(StrEnum):
    """
    Состояния игры.
    """
    REGISTRATION: str = auto()  # Регистрация на игру.
    SELECTION: str = auto()  # Выбор вопроса.
    QUESTION: str = auto()  # Ожидание нажатия на кнопку для ответа на вопрос.
    ANSWER: str = auto()  # Ожидание ответа.


class QuestionComplexity(IntEnum):
    """
    Сложность вопросов и соответсвующая цена
    """
    VERY_EASY = 10
    EASY = 20
    MEDIUM = 30
    DIFFICULT = 40
    VERY_DIFFICULT = 50
