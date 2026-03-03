from datetime import datetime, timezone
from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, func, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from core.db import Base


class UserEmbedding(Base):
    __tablename__ = "user_embedding"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)
    original_content: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )