"""
Aegis AI — Generic Repository Pattern.

Provides a type-safe, async base repository that all domain-specific
repositories extend. Implements common CRUD operations with filtering,
pagination, and soft-delete support.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import Base

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic async repository providing CRUD + filtering + pagination.

    Subclass and set `model` to get full repository capabilities:

        class UserRepository(BaseRepository[User]):
            model = User
    """

    model: type[ModelType]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        return await self.session.get(self.model, id)

    async def get_by_id_or_raise(self, id: uuid.UUID) -> ModelType:
        obj = await self.get_by_id(id)
        if obj is None:
            raise ValueError(f"{self.model.__name__} with id={id} not found")
        return obj

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: str = "created_at",
        order_dir: str = "desc",
        offset: int = 0,
        limit: int = 50,
        include_deleted: bool = False,
    ) -> tuple[list[ModelType], int]:
        """
        List entities with filtering, ordering, and pagination.

        Returns:
            Tuple of (items, total_count).
        """
        query = select(self.model)
        count_query = select(func.count()).select_from(self.model)

        # Apply soft-delete filter
        if not include_deleted and hasattr(self.model, "deleted_at"):
            condition = self.model.deleted_at.is_(None)  # type: ignore
            query = query.where(condition)
            count_query = count_query.where(condition)

        # Apply additional filters
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    col = getattr(self.model, key)
                    if isinstance(value, list):
                        query = query.where(col.in_(value))
                        count_query = count_query.where(col.in_(value))
                    else:
                        query = query.where(col == value)
                        count_query = count_query.where(col == value)

        # Apply ordering
        if hasattr(self.model, order_by):
            col = getattr(self.model, order_by)
            query = query.order_by(col.desc() if order_dir == "desc" else col.asc())

        # Pagination
        query = query.offset(offset).limit(limit)

        result = await self.session.execute(query)
        items = list(result.scalars().all())
        count_result = await self.session.execute(count_query)
        total = count_result.scalar() or 0

        return items, total

    async def create(self, **kwargs: Any) -> ModelType:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        logger.info("entity_created", model=self.model.__name__, id=str(obj.id))  # type: ignore
        return obj

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ModelType:
        obj = await self.get_by_id_or_raise(id)
        for key, value in kwargs.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, id: uuid.UUID, *, soft: bool = True) -> None:
        obj = await self.get_by_id_or_raise(id)
        if soft and hasattr(obj, "deleted_at"):
            obj.deleted_at = datetime.now(UTC)  # type: ignore
            await self.session.flush()
        else:
            await self.session.delete(obj)
            await self.session.flush()

    async def exists(self, **kwargs: Any) -> bool:
        query = select(func.count()).select_from(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return (result.scalar() or 0) > 0

    async def count(self, **kwargs: Any) -> int:
        query = select(func.count()).select_from(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar() or 0
