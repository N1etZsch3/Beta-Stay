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
