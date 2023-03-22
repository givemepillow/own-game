from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.store.repository import ThemeRepository, PlayerRepository, GameRepository, DelayedMessageRepository, \
    AdminRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.themes = ThemeRepository(session)
        self.players = PlayerRepository(session)
        self.games = GameRepository(session)
        self.delayed_messages = DelayedMessageRepository(session)
        self.admins = AdminRepository(session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args):
        await self.rollback()
        await self.session.close()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
