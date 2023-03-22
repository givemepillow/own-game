from dataclasses import dataclass
from hashlib import sha256

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

    @classmethod
    def create(cls, email: str, password: str):
        return cls(
            email=email,
            password=sha256(password.encode()).hexdigest()
        )

    def is_password_valid(self, password: str):
        return self.password == sha256(password.encode()).hexdigest()


@dataclass
class SessionAdmin:
    id: int
    email: str

    @classmethod
    def from_model(cls, admin: Admin):
        return cls(id=admin.id, email=admin.email)
