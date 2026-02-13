import json
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.conversation_service import get_messages, save_message


async def process_message(db: AsyncSession, conversation_id: int, user_content: str) -> dict:
    """处理用户消息（非流式）：保存消息 → 构建历史 → 调用Agent → 保存回复"""
    # 1. 保存用户消息
    await save_message(db, conversation_id, "user", user_content)

    # 2. 获取历史消息
    history = await get_messages(db, conversation_id)
    messages = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # 3. 调用Agent
    try:
        from app.agent.betastay_agent import create_betastay_agent

        agent = create_betastay_agent()
        result = agent.invoke(
            {"messages": messages},
            config={"configurable": {"thread_id": str(conversation_id)}},
        )

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


async def stream_message(db: AsyncSession, conversation_id: int, user_content: str) -> AsyncGenerator[str, None]:
    """流式处理用户消息，yield SSE格式事件"""
    # 1. 保存用户消息
    await save_message(db, conversation_id, "user", user_content)

    # 2. 获取历史消息
    history = await get_messages(db, conversation_id)
    messages = []
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})

    # 3. 流式调用Agent
    full_content = ""
    full_thinking = ""

    try:
        from app.agent.betastay_agent import create_betastay_agent

        agent = create_betastay_agent()
        config = {"configurable": {"thread_id": str(conversation_id)}}

        async for event in agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            kind = event["event"]

            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]

                # 思考内容
                reasoning = ""
                if hasattr(chunk, "additional_kwargs"):
                    reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                if reasoning:
                    full_thinking += reasoning
                    yield f"event: thinking\ndata: {json.dumps({'content': reasoning}, ensure_ascii=False)}\n\n"

                # 正文内容
                text = chunk.content if hasattr(chunk, "content") else ""
                if text:
                    full_content += text
                    yield f"event: content\ndata: {json.dumps({'content': text}, ensure_ascii=False)}\n\n"

    except Exception as e:
        full_content = f"系统处理中遇到问题，请稍后重试。（错误：{str(e)}）"
        yield f"event: content\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

    # 4. 保存完整回复
    if not full_content:
        full_content = "抱歉，我暂时无法处理您的请求。"
        yield f"event: content\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

    reply = await save_message(db, conversation_id, "assistant", full_content)

    # 5. 发送完成事件
    done_data = {
        "id": reply.id,
        "content": full_content,
        "thinking": full_thinking,
        "created_at": reply.created_at.isoformat(),
    }
    yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"
