from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.feedback import Feedback
from app.models.pricing import PricingRecord


async def create_feedback(db: AsyncSession, data: dict) -> Feedback:
    fb = Feedback(**data)
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def list_by_property(db: AsyncSession, property_id: int) -> list[Feedback]:
    """通过property_id查询相关的所有反馈（经由pricing_record关联）"""
    result = await db.execute(
        select(Feedback)
        .join(PricingRecord, Feedback.pricing_record_id == PricingRecord.id)
        .where(PricingRecord.property_id == property_id)
        .order_by(Feedback.created_at.desc())
    )
    return list(result.scalars().all())
