from __future__ import annotations

from datetime import datetime, timezone
from random import choice

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


class Question:
    def __init__(self, question: str, cost: int, answer: str):
        self.id: int | None = None
        self.theme_id: int | None = None
        self.cost: int = cost
        self.question = question
        self.answer: str = answer

        self.theme: Theme | None = None
        self.media_files: list[MediaFile] = []

    @classmethod
    def from_dict(cls, question: str, complexity: QuestionComplexity, answer: str, **_):
        return cls(
            question=question,
            cost=QuestionComplexity(complexity).value,
            answer=answer
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

    def __init__(self, origin: Origin, user_id: int):
        self.origin = origin
        self.user_id = user_id
        self.points = 0
        self.in_game: bool = True
        self.is_current: bool = False
        self.is_leading: bool = False
        self.is_answering: bool = False
        self.already_answered: bool = False
        self.game: Game | None = None

    def __eq__(self, other: Player):
        return all((
            self.origin == other.origin,
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
        self.selected_questions: list[int] = []
        self.created_at: datetime = datetime.now()

        self.players: list[Player] = []
        self.themes: list[Theme] = []

        self.current_question: Question | None = None

    def start_game(self) -> Player:
        self.state = GameState.QUESTION_SELECTION
        player = choice(self.players)
        player.is_current = True
        return player

    def select_question(self, question_id: int) -> Question:
        for t in self.themes:
            for q in t.questions:
                if q.id == question_id:
                    self.current_question = q
                    self.selected_questions.append(q.id)
                    self.state = GameState.WAITING_FOR_PRESS
                    return q
            else:
                raise ValueError("undefined question")

    def press_answer_button(self, player: Player):
        self.state = GameState.WAITING_FOR_ANSWER
        player.is_answering = True

    def answer(self, player: Player):
        self.state = GameState.WAITING_FOR_CHECKING
        player.already_answered = True

    def reject_answer(self, player: Player):
        self.state = GameState.WAITING_FOR_PRESS
        player.points -= self.current_question.cost
        player.is_answering = False
        player.is_current = False
        self._reset_answered()

    def accept_answer(self, player: Player):
        self.state = GameState.QUESTION_SELECTION
        player.points += self.current_question.cost
        player.is_answering = False
        player.is_current = True
        self._reset_answered()

    def finish(self):
        self.themes.clear()

    def _reset_answered(self):
        for p in self.players:
            p.already_answered = False

    def get_current_player(self) -> Player | None:
        for p in self.players:
            if p.is_current:
                return p
        return None

    def get_answering_player(self) -> Player | None:
        for p in self.players:
            if p.is_answering:
                return p
        return None

    def get_leading_player(self) -> Player | None:
        for p in self.players:
            if p.is_leading:
                return p
        return None
