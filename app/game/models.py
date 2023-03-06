from __future__ import annotations

from datetime import datetime, timezone
from random import choice, sample
from typing import Optional, NoReturn

from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import MutableList

from app.bot.enums import Origin
from app.game.enums import GameState, QuestionComplexity
import sqlalchemy as sa

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.store.orm import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, compare=True)

    cost: Mapped[int] = mapped_column(nullable=False)
    question: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    answer: Mapped[str] = mapped_column(sa.String(80), nullable=False)

    theme_id: Mapped[int] = mapped_column(sa.ForeignKey("themes.id"))
    theme: Mapped[Theme] = relationship(
        back_populates="questions", innerjoin=True
    )

    __table_args__ = (
        sa.UniqueConstraint("theme_id", "cost"),
    )

    def __le__(self, other: Question):
        return self.cost <= other.cost

    def __lt__(self, other: Question):
        return self.cost < other.cost

    def __ge__(self, other: Question):
        return self.cost >= other.cost

    def __gt__(self, other: Question):
        return self.cost < other.cost

    @classmethod
    def from_dict(cls, question: str, complexity: QuestionComplexity, answer: str, **_):
        return cls(
            question=question,
            cost=QuestionComplexity(complexity).value,
            answer=answer
        )


class Theme(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True, compare=True)
    title: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True)
    author: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    is_available: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now(tz='UTC'))

    questions: Mapped[list[Question]] = relationship(
        back_populates="theme",
        cascade="all, delete-orphan",
        lazy='joined',
        innerjoin=True
    )

    @classmethod
    def from_dict(cls, title: str, author: str, questions: list[dict], **_):
        return cls(
            title=title,
            author=author,
            questions=[Question.from_dict(**q) for q in questions]
        )


class Player(Base):
    """
    Игрок - пользователь мессенджера или соц. сети
    """
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    origin: Mapped[Origin] = mapped_column(sa.Enum(Origin), nullable=False, compare=True)
    user_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, compare=True)
    chat_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, compare=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)

    points: Mapped[int] = mapped_column(nullable=False, default=0)

    already_answered: Mapped[bool] = mapped_column(nullable=False, default=False)

    game_id: Mapped[int] = mapped_column(sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False)
    game: Mapped[Game] = relationship(back_populates="players", lazy='noload')

    __table_args__ = (sa.UniqueConstraint("origin", "user_id", "chat_id"),)


game_themes = sa.Table(
    "game_themes",
    Base.metadata,
    sa.Column("theme_id", sa.ForeignKey("themes.id"), primary_key=True),
    sa.Column("game_id", sa.ForeignKey("games.id"), primary_key=True),
)


class Game(Base):
    """
    Игровая сессия.
    """
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True, compare=True)
    origin: Mapped[Origin] = mapped_column(sa.Enum(Origin), nullable=False, compare=True)
    chat_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, compare=True)
    state: Mapped[GameState] = mapped_column(sa.Enum(GameState), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now(tz='UTC'))
    selected_questions: Mapped[set[int]] = mapped_column(MutableList.as_mutable(ARRAY(sa.Integer)), default=[])

    leading_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    current_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)
    answering_user_id: Mapped[int | None] = mapped_column(sa.BigInteger, nullable=True)

    current_question_id: Mapped[Optional[Player]] = mapped_column(sa.ForeignKey("questions.id"), nullable=True)
    current_question: Mapped[Optional[Question]] = relationship(lazy="joined")

    players: Mapped[list[Player]] = relationship(
        back_populates="game", cascade="all, delete-orphan", lazy='joined', innerjoin=False,
    )
    themes: Mapped[list[Theme]] = relationship(secondary=game_themes, lazy="joined", innerjoin=False)

    __table_args__ = (sa.UniqueConstraint("origin", "chat_id"),)

    def set_leading(self, user_id: int):
        self.state: GameState = GameState.REGISTRATION
        self.leading_user_id: int = user_id

    def register(self, player: Player):
        self.players.append(player)

    def unregister(self, player: Player) -> bool:
        try:
            self.players.remove(player)
            return True
        except ValueError:
            return False

    def start(self, themes: list[Theme]) -> Player:
        self.state: GameState = GameState.QUESTION_SELECTION
        self.themes.extend(sample(themes, k=2))
        player = choice(self.players)
        self.current_user_id = player.user_id
        return player

    def select(self, question_id: int) -> Optional[Question]:
        self.state: GameState = GameState.WAITING_FOR_PRESS
        for t in self.themes:
            for q in t.questions:
                if q.id == question_id:
                    self.selected_questions.append(q.id)
                    self.current_question = q
                    return q

    def press(self, player: Player) -> NoReturn:
        self.state: GameState = GameState.WAITING_FOR_ANSWER
        self.answering_user_id = player.user_id

    def answer(self) -> NoReturn:
        self.state: GameState = GameState.WAITING_FOR_CHECKING

    def accept(self, player: Player) -> NoReturn:
        self.answering_user_id: int | None = None
        self.current_user_id = player.user_id
        player.points += self.current_question.cost

    def start_selection(self) -> Player:
        self.state: GameState = GameState.QUESTION_SELECTION
        for p in self.players:
            p.already_answered = False
        return self.get_current_player()

    def reject(self, player: Player):
        self.state: GameState = GameState.WAITING_FOR_PRESS
        self.answering_user_id: int | None = None

        player.already_answered = True
        player.points -= self.current_question.cost

    def is_all_answered(self):
        for p in self.players:
            if not p.already_answered:
                return False
        return True

    def get_answering_player(self) -> Player:
        for p in self.players:
            if p.user_id == self.answering_user_id:
                return p

    def get_current_player(self) -> Player:
        for p in self.players:
            if p.user_id == self.current_user_id:
                return p

    def any_questions(self) -> bool:
        return len(self.selected_questions) < 10

    def finish(self):
        self.themes.clear()


class DelayedMessage(Base):
    __tablename__ = "delayed_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    origin: Mapped[Origin] = mapped_column(sa.Enum(Origin), nullable=False)
    delay: Mapped[int] = mapped_column(nullable=False)
    chat_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    data: Mapped[bytes] = mapped_column(sa.LargeBinary(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now(tz='UTC'))

    @property
    def seconds_remaining(self):
        _delay = int(self.delay - (datetime.now(tz=timezone.utc) - self.created_at).total_seconds())
        return _delay if _delay > 1 else 1
