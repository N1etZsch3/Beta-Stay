from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.property import Property
from app.models.pricing import PricingRecord
from app.models.feedback import Feedback

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    # Property count
    prop_count = await db.execute(select(func.count(Property.id)))
    property_count = prop_count.scalar() or 0

    # Recent pricing count (last 30 days)
    pricing_count_result = await db.execute(select(func.count(PricingRecord.id)))
    recent_pricing_count = pricing_count_result.scalar() or 0

    # Feedback count
    fb_count = await db.execute(select(func.count(Feedback.id)))
    feedback_count = fb_count.scalar() or 0

    # Property list with latest pricing
    props_result = await db.execute(
        select(Property).order_by(Property.updated_at.desc()).limit(10)
    )
    properties = []
    for prop in props_result.scalars().all():
        # Get latest pricing for this property
        latest_pricing = await db.execute(
            select(PricingRecord)
            .where(PricingRecord.property_id == prop.id)
            .order_by(PricingRecord.created_at.desc())
            .limit(1)
        )
        pricing = latest_pricing.scalar_one_or_none()

        properties.append({
            "id": prop.id,
            "name": prop.name,
            "address": prop.address,
            "room_type": prop.room_type,
            "area": prop.area,
            "min_price": prop.min_price,
            "max_price": prop.max_price,
            "latest_suggested_price": pricing.suggested_price if pricing else None,
            "latest_pricing_date": pricing.target_date.isoformat() if pricing else None,
        })

    return {
        "property_count": property_count,
        "recent_pricing_count": recent_pricing_count,
        "feedback_count": feedback_count,
        "properties": properties,
    }
