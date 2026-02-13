from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.property import Property


async def create_property(db: AsyncSession, data: dict) -> Property:
    prop = Property(**data)
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return prop


async def get_property(db: AsyncSession, property_id: int) -> Property | None:
    result = await db.execute(select(Property).where(Property.id == property_id))
    return result.scalar_one_or_none()


async def list_properties(db: AsyncSession) -> list[Property]:
    result = await db.execute(select(Property).order_by(Property.created_at.desc()))
    return list(result.scalars().all())


async def update_property(db: AsyncSession, property_id: int, data: dict) -> Property | None:
    prop = await get_property(db, property_id)
    if not prop:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(prop, key, value)
    await db.commit()
    await db.refresh(prop)
    return prop


async def delete_property(db: AsyncSession, property_id: int) -> bool:
    prop = await get_property(db, property_id)
    if not prop:
        return False
    await db.delete(prop)
    await db.commit()
    return True
