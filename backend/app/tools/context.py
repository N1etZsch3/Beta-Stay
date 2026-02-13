from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

db_session_var: ContextVar[AsyncSession] = ContextVar("db_session")


def get_db_session() -> AsyncSession:
    """工具函数内部调用，获取当前请求的DB Session"""
    return db_session_var.get()
