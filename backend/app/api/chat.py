from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import (
    chat_service,
    conversation_service,
    feedback_service,
    property_service,
)
from app.services.action_store import pop_pending_action

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


class MessageEdit(BaseModel):
    message_id: int
    content: str


class MessageRegenerate(BaseModel):
    message_id: int


class ConfirmAction(BaseModel):
    action_id: str


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


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    success = await conversation_service.delete_conversation(db, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"success": True}


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


@router.post("/conversations/{conversation_id}/messages/edit")
async def edit_message_stream(
    conversation_id: str, data: MessageEdit, db: AsyncSession = Depends(get_db)
):
    """编辑消息后重新生成，返回SSE事件流"""
    conv = await conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return StreamingResponse(
        chat_service.stream_edit(db, conversation_id, data.message_id, data.content),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/conversations/{conversation_id}/messages/regenerate")
async def regenerate_message_stream(
    conversation_id: str, data: MessageRegenerate, db: AsyncSession = Depends(get_db)
):
    """重新生成AI回复，返回SSE事件流"""
    conv = await conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return StreamingResponse(
        chat_service.stream_regenerate(db, conversation_id, data.message_id),
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


@router.post("/conversations/{conversation_id}/confirm")
async def confirm_action(
    conversation_id: str, data: ConfirmAction, db: AsyncSession = Depends(get_db)
):
    """用户确认待执行操作"""
    action = await pop_pending_action(db, data.action_id)
    if not action:
        raise HTTPException(status_code=404, detail="操作已过期或不存在")
    if action["conversation_id"] != conversation_id:
        raise HTTPException(status_code=400, detail="操作不属于当前会话")

    action_type = action["action_type"]
    action_data = action["data"]

    if action_type == "create_property":
        result = await property_service.create_property(db, action_data)
        await conversation_service.save_message(
            db,
            conversation_id,
            "assistant",
            f"房源「{result.name}」已成功录入（ID: {result.id}）",
        )
        return {
            "success": True,
            "type": "property",
            "id": result.id,
            "name": result.name,
        }

    elif action_type == "record_feedback":
        result = await feedback_service.create_feedback(db, action_data)
        await conversation_service.save_message(
            db,
            conversation_id,
            "assistant",
            f"反馈已记录（ID: {result.id}，类型: {result.feedback_type}）",
        )
        return {"success": True, "type": "feedback", "id": result.id}

    else:
        raise HTTPException(status_code=400, detail=f"未知操作类型: {action_type}")
