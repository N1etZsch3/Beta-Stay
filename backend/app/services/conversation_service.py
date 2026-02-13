from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message


async def create_conversation(
    db: AsyncSession, title: str | None = None
) -> Conversation:
    conv = Conversation(title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_conversations(db: AsyncSession) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.status == "active")
        .order_by(Conversation.last_active_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession, conversation_id: str
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def save_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    tool_calls: dict | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_calls=tool_calls,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_messages(db: AsyncSession, conversation_id: str) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def count_messages(
    db: AsyncSession, conversation_id: str, role: str | None = None
) -> int:
    """统计会话中的消息数量，可选按角色筛选"""
    stmt = select(func.count(Message.id)).where(
        Message.conversation_id == conversation_id
    )
    if role:
        stmt = stmt.where(Message.role == role)
    result = await db.execute(stmt)
    return result.scalar() or 0


async def update_conversation_title(
    db: AsyncSession, conversation_id: str, title: str
) -> None:
    """更新会话标题"""
    conv = await get_conversation(db, conversation_id)
    if conv:
        conv.title = title
        await db.commit()


async def delete_conversation(db: AsyncSession, conversation_id: str) -> bool:
    """删除会话及其所有消息"""
    conv = await get_conversation(db, conversation_id)
    if not conv:
        return False
    await db.execute(
        sa_delete(Message).where(Message.conversation_id == conversation_id)
    )
    await db.delete(conv)
    await db.commit()
    return True
