from fastapi import APIRouter
from app.api.property import router as property_router

api_router = APIRouter()
api_router.include_router(property_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
