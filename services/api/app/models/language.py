from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Language(Base):
    __tablename__ = "languages"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_source_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_target_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
