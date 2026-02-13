"""
待确认操作的内存暂存。

生命周期：工具返回 pending_confirmation → 存入 → 用户确认 → 弹出执行 → 删除
生产环境应替换为 Redis 实现。
"""
import uuid
from typing import Any

_store: dict[str, dict[str, Any]] = {}


def save_pending_action(conversation_id: str, action_type: str, data: dict) -> str:
    """暂存一个待确认操作，返回 action_id"""
    action_id = str(uuid.uuid4())
    _store[action_id] = {
        "conversation_id": conversation_id,
        "action_type": action_type,
        "data": data,
    }
    return action_id


def get_pending_action(action_id: str) -> dict[str, Any] | None:
    """获取待确认操作"""
    return _store.get(action_id)


def pop_pending_action(action_id: str) -> dict[str, Any] | None:
    """获取并删除待确认操作"""
    return _store.pop(action_id, None)
