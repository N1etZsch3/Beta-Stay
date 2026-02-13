from sqlalchemy.ext.asyncio import AsyncSession
from app.services.conversation_service import get_messages, save_message


async def process_message(db: AsyncSession, conversation_id: int, user_content: str) -> dict:
    """处理用户消息：保存消息 → 构建历史 → 调用Agent → 保存回复"""
    # 1. 保存用户消息
    await save_message(db, conversation_id, "user", user_content)

    # 2. 获取历史消息
    history = await get_messages(db, conversation_id)
    messages = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # 3. 调用Agent（MVP先用简单方式，后续接入LangGraph checkpointer）
    try:
        from app.agent.betastay_agent import create_betastay_agent

        agent = create_betastay_agent()
        result = agent.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": str(conversation_id)}},
        )

        # 提取最后一条assistant消息
        assistant_content = ""
        if result and "messages" in result:
            for msg in reversed(result["messages"]):
                if hasattr(msg, "content") and msg.type == "ai":
                    assistant_content = msg.content
                    break

        if not assistant_content:
            assistant_content = "抱歉，我暂时无法处理您的请求。"

    except Exception as e:
        assistant_content = f"系统处理中遇到问题，请稍后重试。（错误：{str(e)}）"

    # 4. 保存助手回复
    reply = await save_message(db, conversation_id, "assistant", assistant_content)

    return {
        "id": reply.id,
        "role": reply.role,
        "content": reply.content,
        "created_at": reply.created_at.isoformat(),
    }
