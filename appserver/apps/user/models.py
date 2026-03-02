from sqlmodel import SQLModel, Field, Column
from pgvector.sqlalchemy import Vector

class UserEmbedding(SQLModel, table=True):
    __tablename__ = "user_embedding"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    embedding: list[float] = Field(sa_column=Column(Vector(1536)))
    original_content: str = Field(nullable=False)