from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.config import settings
from core.db import Base


class AvatarCategory(StrEnum):
    PERSONALITY_CONVERSATION_STYLE = "PERSONALITY_CONVERSATION_STYLE"
    USER_INTERESTS = "USER_INTERESTS"
    USER_INFO = "USER_INFO"
    OTHER = "OTHER"


class AvatarProfile(Base):
    __tablename__ = "avatar_profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    personality: Mapped[str | None] = mapped_column(String(255), nullable=True)
    speech_style: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AvatarEmbedding(Base):
    __tablename__ = "avatar_embedding"
    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_avatar_embedding_user_category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(settings.EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )
