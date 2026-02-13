from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import chat_service, conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str | None
    status: str
    model_config = {"from_attributes": True}


class MessageSend(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    model_config = {"from_attributes": True}


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate, db: AsyncSession = Depends(get_db)
):
    conv = await conversation_service.create_conversation(db, data.title)
    return conv


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    return await conversation_service.list_conversations(db)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str, data: MessageSend, db: AsyncSession = Depends(get_db)
):
    """非流式发送消息（保留兼容）"""
    conv = await conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await chat_service.process_message(db, conversation_id, data.content)


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_stream(
    conversation_id: str, data: MessageSend, db: AsyncSession = Depends(get_db)
):
    """流式发送消息，返回SSE事件流"""
    conv = await conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return StreamingResponse(
        chat_service.stream_message(db, conversation_id, data.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, db: AsyncSession = Depends(get_db)):
    messages = await conversation_service.get_messages(db, conversation_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
