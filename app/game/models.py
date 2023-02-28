from __future__ import annotations

from datetime import datetime, timezone

from app.bot.enums import Origin
from app.game.enums import GameState, QuestionComplexity


class DelayedMessage:
    def __init__(self, name: str, origin: Origin, chat_id: int, data: bytes, delay: int):
        self.name: str = name
        self.delay: int = delay
        self.origin: Origin = origin
        self.chat_id: int = chat_id
        self.data: bytes = data

        self.created_at: datetime = datetime.now()

    @property
    def seconds_remaining(self):
        _delay = self.delay - (datetime.now(tz=timezone.utc).second - self.created_at.second)
        return _delay if _delay > 1 else 0


class MediaFile:
    def __init__(self, filename: str, content_type: str):
        _, ext = content_type.split('/')
        self.filename = '.'.join((filename, 'mp3' if ext == 'mpeg' else ext))
        self.content_type = content_type

        self.question: Question | None = None


class Answer:
    def __init__(self, answer: str):
        self.id: int | None = None
        self.question_id: int | None = None
        self.answer = answer

    @classmethod
    def from_dict(cls, answer: str, **_):
        return cls(answer=answer)


class Question:
    def __init__(self, question: str, cost: int, answers: list[Answer]):
        self.id: int | None = None
        self.theme_id: int | None = None
        self.cost: int = cost
        self.question = question

        self.answers: list[Answer] = answers
        self.theme: Theme | None = None
        self.media_files: list[MediaFile] = []

    @classmethod
    def from_dict(cls, question: str, complexity: QuestionComplexity, answers: list[dict], **_):
        return cls(
            question=question,
            cost=QuestionComplexity(complexity).value,
            answers=[Answer.from_dict(**a) for a in answers]
        )


class Theme:

    def __init__(self, title: str, author: str, questions: list[Question]):
        self.id: int | None = None
        self.title = title
        self.author = author
        self.created_at: datetime | None = None
        self.is_available: bool = False
        self.questions: list[Question] = questions

    def __eq__(self, other: Theme) -> bool:
        return self.id == other.id

    def __hash__(self):
        return hash(self.id)

    @classmethod
    def from_dict(cls, title: str, author: str, questions: list[dict], **_):
        return cls(
            title=title,
            author=author,
            questions=[Question.from_dict(**q) for q in questions]
        )


class Player:
    """
    Игрок - пользователь мессенджера или соц. сети
    """

    def __init__(self, origin: Origin, chat_id: int, user_id: int):
        self.origin = origin
        self.chat_id = chat_id
        self.user_id = user_id
        self.points = 0
        self.in_game: bool = True
        self.is_current: bool = False
        self.is_leading: bool = False

        self.game: Game | None = None

    def __eq__(self, other: Player):
        return all((
            self.origin == other.origin,
            self.chat_id == other.chat_id,
            self.user_id == other.user_id
        ))


class Game:
    """
    Игровая сессия.
    """

    def __init__(self, origin: Origin, chat_id: int):
        self.id: int | None = None
        self.origin = origin
        self.chat_id = chat_id
        self.state: GameState = GameState.REGISTRATION
        self.created_at: datetime = datetime.now()

        self.players: list[Player] = []
        self.themes: list[Theme] = []

        self.current_question: Question | None = None
