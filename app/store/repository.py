from abc import ABC, abstractmethod

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.enums import Origin
from app.game.models import Game, Theme, Player, DelayedMessage
from app.store import orm


class AbstractRepository(ABC):

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    def add(self, item: object):
        pass

    @abstractmethod
    def get(self, *args, **kwargs) -> object:
        pass

    @abstractmethod
    def list(self) -> list[object]:
        pass


class GameRepository(AbstractRepository):

    def add(self, game: Game):
        self.session.add(game)

    async def get(self, chat_id: int, origin: Origin) -> Game | None:
        return (await self.session.execute(
            select(Game).
            where(and_(
                orm.games.c.origin == origin,
                orm.games.c.chat_id == chat_id)
            ))).scalar()

    async def list(self) -> list[object]:
        return list((await self.session.execute(select(Game))).scalars())

    async def delete(self, chat_id: int, origin: Origin):
        await self.session.execute(
            delete(Game).where(
                orm.games.c.origin == origin,
                orm.games.c.chat_id == chat_id
            )
        )


class ThemeRepository(AbstractRepository):

    def add(self, theme: Theme):
        self.session.add(theme)

    async def get(self, theme_id: int) -> object:
        return (await self.session.execute(select(Theme))).scalar()

    async def list(self) -> list[object]:
        return list((await self.session.execute(select(Theme))).scalars())


class PlayerRepository(AbstractRepository):
    def add(self, player: Player):
        self.session.add(player)

    async def get(self, origin: Origin, chat_id: int, user_id: int) -> object:
        return (await self.session.query(select(Player).filter(
            (orm.players.c.origin == origin) &
            (orm.players.c.chat_id == chat_id) &
            (orm.players.c.user_id == user_id)
        ))).scalar()

    def list(self) -> list[object]:
        pass


class DelayMessageRepository(AbstractRepository):
    def add(self, delay_message: DelayedMessage):
        self.session.add(delay_message)

    async def get(self, *args, **kwargs) -> object:
        raise NotImplemented

    async def list(self) -> list[DelayedMessage]:
        return list((await self.session.execute(select(DelayedMessage))).scalars())

    async def delete(self, name: str, origin: Origin, chat_id: int):
        await self.session.execute(
            delete(DelayedMessage).where(
                (orm.delayed_messages.c.type == name) &
                (orm.delayed_messages.c.origin == origin) &
                (orm.delayed_messages.c.chat_id == chat_id)
            ))
