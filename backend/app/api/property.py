from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services import property_service

router = APIRouter(prefix="/property", tags=["property"])


class PropertyCreate(BaseModel):
    name: str
    address: str
    room_type: str
    area: float
    facilities: dict = {}
    description: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    expected_return_rate: float | None = None
    vacancy_tolerance: float | None = None


class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    room_type: str
    area: float
    facilities: dict
    description: str | None
    min_price: float | None
    max_price: float | None
    expected_return_rate: float | None
    vacancy_tolerance: float | None

    model_config = {"from_attributes": True}


class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    room_type: str | None = None
    area: float | None = None
    facilities: dict | None = None
    description: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    expected_return_rate: float | None = None
    vacancy_tolerance: float | None = None


@router.post("", response_model=PropertyResponse)
async def create_property(data: PropertyCreate, db: AsyncSession = Depends(get_db)):
    prop = await property_service.create_property(db, data.model_dump())
    return prop


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: int, db: AsyncSession = Depends(get_db)):
    prop = await property_service.get_property(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.get("", response_model=list[PropertyResponse])
async def list_properties(db: AsyncSession = Depends(get_db)):
    return await property_service.list_properties(db)


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(property_id: int, data: PropertyUpdate, db: AsyncSession = Depends(get_db)):
    prop = await property_service.update_property(db, property_id, data.model_dump(exclude_unset=True))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.delete("/{property_id}")
async def delete_property(property_id: int, db: AsyncSession = Depends(get_db)):
    success = await property_service.delete_property(db, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Property deleted"}
