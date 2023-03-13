from sqlalchemy.orm import Mapped, mapped_column

from app.store.orm import Base
import sqlalchemy as sa


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, compare=True)
    email: Mapped[str] = mapped_column(sa.String(80), nullable=False)
    password: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    __table_args__ = (
        sa.UniqueConstraint("email"),
    )
