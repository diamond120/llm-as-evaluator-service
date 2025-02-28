from sqlalchemy import Column, DateTime, Index, Integer
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db_api.database import Base


class TimestampedBase(AsyncAttrs, Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        # Index("idx_created_at", "created_at"),
        Index("idx_updated_at", "updated_at"),
    )
