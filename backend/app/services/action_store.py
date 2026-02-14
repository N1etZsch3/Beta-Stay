"""
待确认操作的数据库持久化存储。

生命周期：工具返回 pending_confirmation → 存入 → 用户确认 → 弹出执行 → 删除
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pending_action import PendingAction


async def save_pending_action(
    db: AsyncSession, conversation_id: str, action_type: str, data: dict
) -> str:
    """暂存一个待确认操作，返回 action_id。使用 flush 以便调用方管理事务。"""
    action = PendingAction(
        conversation_id=conversation_id,
        action_type=action_type,
        data=data,
    )
    db.add(action)
    await db.flush()
    return action.id


async def get_pending_action(
    db: AsyncSession, action_id: str
) -> dict[str, Any] | None:
    """获取待确认操作"""
    result = await db.execute(
        select(PendingAction).where(PendingAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        return None
    return {
        "conversation_id": action.conversation_id,
        "action_type": action.action_type,
        "data": action.data,
    }


async def pop_pending_action(
    db: AsyncSession, action_id: str
) -> dict[str, Any] | None:
    """获取并删除待确认操作"""
    result = await db.execute(
        select(PendingAction).where(PendingAction.id == action_id)
    )
    action = result.scalar_one_or_none()
    if not action:
        return None
    data = {
        "conversation_id": action.conversation_id,
        "action_type": action.action_type,
        "data": action.data,
    }
    await db.delete(action)
    await db.commit()
    return data
