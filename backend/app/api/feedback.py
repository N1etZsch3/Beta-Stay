from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    pricing_record_id: int
    feedback_type: str  # adopted / rejected / adjusted
    actual_price: float | None = None
    note: str | None = None


@router.post("")
async def create_feedback(data: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    fb = await feedback_service.create_feedback(db, data.model_dump())
    return {
        "id": fb.id,
        "pricing_record_id": fb.pricing_record_id,
        "feedback_type": fb.feedback_type,
        "actual_price": fb.actual_price,
        "note": fb.note,
        "created_at": fb.created_at.isoformat(),
    }


@router.get("/by-property/{property_id}")
async def list_feedback_by_property(property_id: int, db: AsyncSession = Depends(get_db)):
    feedbacks = await feedback_service.list_by_property(db, property_id)
    return [
        {
            "id": f.id,
            "pricing_record_id": f.pricing_record_id,
            "feedback_type": f.feedback_type,
            "actual_price": f.actual_price,
            "note": f.note,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]
