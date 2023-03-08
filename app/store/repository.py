from abc import ABC, abstractmethod

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.enums import Origin
from app.game.models import Game, Theme, Player, DelayedMessage


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

    async def get(self, origin: Origin, chat_id: int) -> Game | None:
        return (await self.session.execute(
            select(Game).
            where(and_(
                Game.origin == origin,
                Game.chat_id == chat_id)
            )
        )).scalar()

    async def list(self) -> list[object]:
        return list((await self.session.execute(select(Game))).scalars())

    async def delete(self, origin: Origin, chat_id: int):
        result = (await self.session.execute(
            delete(Game).where(
                Game.origin == origin,
                Game.chat_id == chat_id
            )
        ))
        return result.rowcount  # noqa


class ThemeRepository(AbstractRepository):

    def add(self, theme: Theme):
        self.session.add(theme)

    async def get(self, theme_id: int) -> object:
        return (await self.session.execute(select(Theme).where(Theme.id == theme_id))).scalar()

    async def list(self) -> list[object]:
        return list((await self.session.execute(select(Theme))).unique().scalars())


class PlayerRepository(AbstractRepository):
    def add(self, player: Player):
        self.session.add(player)

    async def get(self, origin: Origin, chat_id: int, user_id: int) -> Player:
        return (await self.session.execute(select(Player).where(
            (Player.origin == origin) &
            (Player.user_id == user_id) &
            (Player.chat_id == chat_id)
        ))).scalar()

    def list(self) -> list[object]:
        pass


class DelayedMessageRepository(AbstractRepository):
    def add(self, delayed_message: DelayedMessage):
        self.session.add(delayed_message)

    async def get(self, origin: Origin, chat_id: int, user_id: int) -> DelayedMessage:
        pass

    async def list(self) -> list[DelayedMessage]:
        return list((await self.session.execute(select(DelayedMessage))).scalars())

    async def delete(self, name: str, origin: Origin, chat_id: int):
        return await self.session.execute(
            delete(DelayedMessage).
            where(
                (DelayedMessage.origin == origin) &
                (DelayedMessage.chat_id == chat_id) &
                (DelayedMessage.name == name)
            )
        )
