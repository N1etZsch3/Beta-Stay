from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date
from app.core.database import get_db
from app.services import pricing_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


class PricingCalculateRequest(BaseModel):
    property_id: int
    target_date: str  # YYYY-MM-DD
    base_price: float | None = None


class PricingRecordResponse(BaseModel):
    id: int
    property_id: int
    target_date: str
    conservative_price: float
    suggested_price: float
    aggressive_price: float
    calculation_details: dict
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/calculate")
async def calculate_pricing(data: PricingCalculateRequest, db: AsyncSession = Depends(get_db)):
    target = date.fromisoformat(data.target_date)
    record = await pricing_service.calculate_and_save(db, data.property_id, target, data.base_price)
    if not record:
        raise HTTPException(status_code=404, detail="Property not found")
    return {
        "id": record.id,
        "property_id": record.property_id,
        "target_date": record.target_date.isoformat(),
        "conservative_price": record.conservative_price,
        "suggested_price": record.suggested_price,
        "aggressive_price": record.aggressive_price,
        "calculation_details": record.calculation_details,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/records/{property_id}")
async def list_pricing_records(property_id: int, db: AsyncSession = Depends(get_db)):
    records = await pricing_service.list_by_property(db, property_id)
    return [
        {
            "id": r.id,
            "property_id": r.property_id,
            "target_date": r.target_date.isoformat(),
            "conservative_price": r.conservative_price,
            "suggested_price": r.suggested_price,
            "aggressive_price": r.aggressive_price,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
