from fastapi import APIRouter
from app.api.property import router as property_router
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router

api_router = APIRouter()
api_router.include_router(property_router)
api_router.include_router(upload_router)
api_router.include_router(chat_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
