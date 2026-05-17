from typing import Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base

T = TypeVar("T", bound=Base)


async def get_entities(
    model: Type[T],
    names: list[str],
    db: AsyncSession,
):
    if not names:
        return []
    existing = (
        (await db.execute(select(model).where(model.name.in_(names)))).scalars().all()
    )

    founds = {obj.name: obj for obj in existing}
    new_objs = [model(name=name) for name in names if name not in founds]

    if new_objs:
        db.add_all(new_objs)
        await db.flush()

    return list(founds.values()) + new_objs
