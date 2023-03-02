from __future__ import annotations

from datetime import datetime

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
    title: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    author: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    is_available: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now(tz='UTC'))

    questions: Mapped[list[Question]] = relationship(
        back_populates="theme",
        cascade="all, delete-orphan",

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

    points: Mapped[int] = mapped_column(nullable=False, default=0)

    is_current: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_answering: Mapped[bool] = mapped_column(nullable=False, default=False)
    already_answered: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_leading: Mapped[bool] = mapped_column(nullable=False, default=False)

    game_id: Mapped[int] = mapped_column(sa.ForeignKey("games.id"))
    game: Mapped[Game] = relationship(back_populates="players")

    __table_args__ = (
        sa.UniqueConstraint("origin", "user_id"),
    )


game_themes = sa.Table(
    "game_themes",
    Base.metadata,
    sa.Column("theme_id", sa.ForeignKey("themes.id"), primary_key=True),
    sa.Column("game_id", sa.ForeignKey("games.id"), primary_key=True)
)


class Game(Base):
    """
    Игровая сессия.
    """
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    origin: Mapped[Origin] = mapped_column(sa.Enum(Origin), nullable=False, compare=True)
    chat_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, compare=True)
    state: Mapped[GameState] = mapped_column(sa.Enum(GameState), nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=sa.func.now(tz='UTC'))

    is_current: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_answering: Mapped[bool] = mapped_column(nullable=False, default=False)
    already_answered: Mapped[bool] = mapped_column(nullable=False, default=False)
    is_leading: Mapped[bool] = mapped_column(nullable=False, default=False)

    selected_question: Mapped[set[int]] = mapped_column(MutableList.as_mutable(ARRAY(sa.Integer)))

    current_question_id: Mapped[int] = mapped_column(sa.ForeignKey("questions.id"))
    current_question: Mapped[Question] = relationship(lazy="joined")

    players: Mapped[list[Player]] = relationship(back_populates="game", lazy="joined", )
    themes: Mapped[list[Theme]] = relationship(secondary=game_themes)

    __table_args__ = (
        sa.UniqueConstraint("origin", "chat_id"),
    )
