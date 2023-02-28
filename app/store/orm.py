from sqlalchemy import MetaData, Table, Column, String, DateTime, func, ForeignKey, Integer, Boolean, Enum, \
    UniqueConstraint, LargeBinary
from sqlalchemy.orm import registry, relationship

from app.bot.enums import Origin
from app.game.enums import GameState
from app.game.models import Game, Answer, Player, MediaFile, Question, Theme, DelayedMessage

_convention = {
    'all_column_names': lambda constraint, table: '.'.join([
        column.name for column in constraint.columns.values()
    ]),
    'ix': 'ix-%(table_name)s-%(all_column_names)s',
    'uq': 'uq-%(table_name)s-%(all_column_names)s',
    'ck': 'ck-%(table_name)s-%(constraint_name)s',
    'fk': 'fk-%(table_name)s-%(all_column_names)s-%(referred_table_name)s',
    'pk': 'pk-%(table_name)s'
}

_metadata = MetaData(naming_convention=_convention)

delayed_messages = Table(
    "delayed_messages",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String(100), primary_key=True),
    Column("origin", Enum(Origin), nullable=False),
    Column("chat_id", Integer, nullable=False),
    Column("delay", Integer, nullable=False),
    Column("data", LargeBinary, nullable=False),
    Column("created_at", DateTime(), default=func.now(tz='UTC')),
)

admins = Table(
    "admins",
    _metadata,
    Column("email", String(20), primary_key=True),
    Column("password", String(100), nullable=False),
    Column("registered_at", DateTime(timezone=True), default=func.now(tz='UTC')),
)

themes = Table(
    "themes",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(100), unique=True),
    Column("author", String(50)),
    Column("is_available", Boolean(), default=True),
    Column("created_at", DateTime(), default=func.now(tz='UTC'))
)

media_files = Table(
    "media_files",
    _metadata,
    Column("id", Integer(), primary_key=True),
    Column("content_type", String(), nullable=False),
    Column("filename", String(), nullable=False),

    Column("question_id", Integer(), ForeignKey("questions.id"), nullable=False),
)

questions = Table(
    "questions",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("cost", Integer, nullable=False),
    Column("question", String(200), nullable=False),

    Column("theme_id", Integer, ForeignKey("themes.id"), nullable=False),

    UniqueConstraint("cost", "theme_id")
)

answers = Table(
    "answers",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("answer", String(50), nullable=False),

    Column("question_id", Integer, ForeignKey("questions.id"), nullable=False),
)

players = Table(
    "players",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("origin", Enum(Origin), nullable=False),
    Column("chat_id", Integer, nullable=False),
    Column("user_id", Integer, nullable=False),
    Column("points", Integer, nullable=False),
    Column("in_game", Boolean, default=True),
    Column("is_current", Boolean, default=False),
    Column("is_leading", Boolean, default=False),

    Column("game_id", Integer, ForeignKey("games.id", ondelete='CASCADE'), nullable=False),

    UniqueConstraint("user_id", "origin", "chat_id")
)

games = Table(
    "games",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("chat_id", Integer, nullable=False),
    Column("origin", Enum(Origin), nullable=False),
    Column("state", Enum(GameState), nullable=False),
    Column("created_at", DateTime(timezone=True), default=func.now(tz='UTC')),

    Column("current_question_id", Integer, ForeignKey("questions.id")),

    UniqueConstraint("chat_id", "origin")
)

game_themes = Table(
    "game_themes",
    _metadata,
    Column("theme_id", ForeignKey("themes.id"), nullable=False),
    Column("game_id", ForeignKey("games.id"), nullable=False),

    UniqueConstraint("theme_id", "game_id")
)


def setup_mappers() -> MetaData:
    mapper_registry = registry(metadata=_metadata)

    mapper_registry.map_imperatively(DelayedMessage, delayed_messages)

    mapper_registry.map_imperatively(Theme, themes, properties={
        "questions": relationship(
            Question,
            lazy="joined",
            cascade="all, delete-orphan",
            innerjoin=True
        )
    })
    mapper_registry.map_imperatively(Question, questions, properties={
        "answers": relationship(
            Answer,
            lazy="joined",
            cascade="all, delete-orphan",
            innerjoin=True
        ),
        "media_files": relationship(
            MediaFile,
            lazy="joined",
            back_populates="question",
            cascade="all, delete-orphan",
            innerjoin=True
        ),
        "theme": relationship(
            Theme,
            lazy="noload",
            back_populates="questions"
        )
    })
    mapper_registry.map_imperatively(MediaFile, media_files, properties={
        "question": relationship(
            Question,
            lazy="noload",
            back_populates="media_files",
        )
    })
    mapper_registry.map_imperatively(Answer, answers)
    mapper_registry.map_imperatively(Player, players, properties={
        "game": relationship(
            Game,
            foreign_keys="Player.game_id",
            back_populates="players",
            lazy="joined",
            innerjoin=True
        )
    })
    mapper_registry.map_imperatively(Game, games, properties={
        "players": relationship(
            Player,
            foreign_keys="Player.game_id",
            back_populates="game",
            lazy="joined",
            cascade="all, delete-orphan",
            innerjoin=True
        ),
        "themes": relationship(
            Theme,
            secondary=game_themes,
            lazy="joined",
            innerjoin=True
        ),
        "current_question": relationship(
            Question,
            lazy="joined",
            innerjoin=True
        )
    })
    return mapper_registry.metadata
