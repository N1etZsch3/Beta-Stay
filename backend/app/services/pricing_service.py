from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pricing import PricingRecord
from app.models.property import Property
from app.engine.pricing_engine import PricingEngine


async def calculate_and_save(
    db: AsyncSession,
    property_id: int,
    target_date: date,
    base_price: float | None = None,
) -> PricingRecord | None:
    # Fetch property
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        return None

    # Use min_price as base if not provided
    effective_base = base_price or prop.min_price or 300.0

    engine = PricingEngine()
    pricing = engine.calculate(
        base_price=effective_base,
        owner_preference={
            "min_price": prop.min_price or 0,
            "max_price": prop.max_price or float("inf"),
            "expected_return_rate": prop.expected_return_rate or 0,
            "vacancy_tolerance": prop.vacancy_tolerance or 0.5,
        },
        property_info={
            "room_type": prop.room_type,
            "area": prop.area,
            "facilities": prop.facilities or {},
        },
        target_date=target_date,
    )

    record = PricingRecord(
        property_id=property_id,
        target_date=target_date,
        conservative_price=pricing["conservative_price"],
        suggested_price=pricing["suggested_price"],
        aggressive_price=pricing["aggressive_price"],
        calculation_details=pricing["calculation_details"],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_by_property(db: AsyncSession, property_id: int) -> list[PricingRecord]:
    result = await db.execute(
        select(PricingRecord)
        .where(PricingRecord.property_id == property_id)
        .order_by(PricingRecord.created_at.desc())
    )
    return list(result.scalars().all())
