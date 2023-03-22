from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker

from app.abc.cleanup_ctx import CleanupCTX
from app.admin.models import Admin
from app.store.unit_of_work import UnitOfWork


class Database(CleanupCTX):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    async def on_startup(self) -> None:
        self.engine = create_async_engine(
            self.app.config.database.dsn,
            echo=self.app.config.settings.debug
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        await self.create_admin()

    async def on_shutdown(self) -> None:
        await self.engine.dispose(close=True)

    def __call__(self) -> UnitOfWork:
        return UnitOfWork(self.session_factory())

    async def create_admin(self):
        try:
            async with self() as uow:
                uow.admins.add(Admin.create(
                    email=self.app.config.admin.email,
                    password=self.app.config.admin.password
                ))
                await uow.commit()
        except IntegrityError:
            pass
