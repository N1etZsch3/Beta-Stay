import json
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.action_store import save_pending_action
from app.services.conversation_service import (
    count_messages,
    get_messages,
    save_message,
    update_conversation_title,
)
from app.tools.context import db_session_var


async def process_message(
    db: AsyncSession, conversation_id: str, user_content: str
) -> dict:
    """处理用户消息（非流式）：保存消息 → 构建历史 → 调用Agent → 保存回复"""
    await save_message(db, conversation_id, "user", user_content)

    # 首条用户消息时，自动设置会话标题为消息前10个字
    user_msg_count = await count_messages(db, conversation_id, role="user")
    if user_msg_count == 1:
        title = user_content[:10]
        await update_conversation_title(db, conversation_id, title)

    history = await get_messages(db, conversation_id)
    messages = [{"role": msg.role, "content": msg.content} for msg in history]

    try:
        from app.agent.betastay_agent import create_betastay_agent

        # 注入 DB Session 到 context
        token = db_session_var.set(db)
        try:
            agent = create_betastay_agent()
            result = agent.invoke(
                {"messages": messages},
                config={"configurable": {"thread_id": str(conversation_id)}},
            )
        finally:
            db_session_var.reset(token)

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

    reply = await save_message(db, conversation_id, "assistant", assistant_content)
    return {
        "id": reply.id,
        "role": reply.role,
        "content": reply.content,
        "created_at": reply.created_at.isoformat(),
    }


async def stream_message(
    db: AsyncSession, conversation_id: str, user_content: str
) -> AsyncGenerator[str, None]:
    """流式处理用户消息，yield SSE格式事件

    SSE 事件类型:
    - thinking: AI思考过程片段
    - content: AI回复正文片段
    - action: 待确认操作（前端应显示确认弹窗）
    - pricing: 定价计算结果（前端应显示PriceCard）
    - done: 流结束，附带完整消息信息
    """
    await save_message(db, conversation_id, "user", user_content)

    # 首条用户消息时，自动设置会话标题为消息前10个字
    user_msg_count = await count_messages(db, conversation_id, role="user")
    if user_msg_count == 1:
        title = user_content[:10]
        await update_conversation_title(db, conversation_id, title)

    history = await get_messages(db, conversation_id)
    messages = [{"role": msg.role, "content": msg.content} for msg in history]

    full_content = ""
    full_thinking = ""
    pending_actions = []  # 本轮产生的待确认操作

    try:
        from app.agent.betastay_agent import create_betastay_agent

        # 注入 DB Session 到 context
        token = db_session_var.set(db)
        try:
            agent = create_betastay_agent()
            config = {"configurable": {"thread_id": str(conversation_id)}}

            async for event in agent.astream_events(
                {"messages": messages},
                config=config,
                version="v2",
            ):
                kind = event["event"]

                # --- 模型流式输出 ---
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

                # --- 工具执行完成 ---
                elif kind == "on_tool_end":
                    raw_output = event["data"].get("output")
                    # LangGraph astream_events v2 返回 ToolMessage 对象
                    # .content 是 JSON 字符串，需要解析
                    tool_output = None
                    if hasattr(raw_output, "content"):
                        try:
                            tool_output = json.loads(raw_output.content)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif isinstance(raw_output, dict):
                        tool_output = raw_output

                    if isinstance(tool_output, dict):
                        # 待确认操作 → 存入 ActionStore，发送 action 事件
                        if tool_output.get("pending_confirmation"):
                            action_id = save_pending_action(
                                conversation_id,
                                tool_output["action"],
                                tool_output["data"],
                            )
                            action_event = {
                                "action_id": action_id,
                                "action_type": tool_output["action"],
                                "display": tool_output.get("display", {}),
                                "data": tool_output["data"],
                            }
                            pending_actions.append(action_event)
                            yield f"event: action\ndata: {json.dumps(action_event, ensure_ascii=False)}\n\n"

                        # 定价结果 → 发送 pricing 事件
                        elif tool_output.get("success") and tool_output.get(
                            "pricing_record_id"
                        ):
                            pricing_event = {
                                "pricing_record_id": tool_output["pricing_record_id"],
                                "property_id": tool_output["property_id"],
                                "target_date": tool_output["target_date"],
                                "conservative_price": tool_output["conservative_price"],
                                "suggested_price": tool_output["suggested_price"],
                                "aggressive_price": tool_output["aggressive_price"],
                            }
                            yield f"event: pricing\ndata: {json.dumps(pricing_event, ensure_ascii=False)}\n\n"

        finally:
            db_session_var.reset(token)

    except Exception as e:
        full_content = f"系统处理中遇到问题，请稍后重试。（错误：{str(e)}）"
        yield f"event: content\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

    if not full_content:
        full_content = "抱歉，我暂时无法处理您的请求。"
        yield f"event: content\ndata: {json.dumps({'content': full_content}, ensure_ascii=False)}\n\n"

    # 保存完整回复（包含工具调用元数据）
    tool_calls_meta = None
    if pending_actions:
        tool_calls_meta = {"pending_actions": pending_actions}

    reply = await save_message(
        db, conversation_id, "assistant", full_content, tool_calls=tool_calls_meta
    )

    done_data = {
        "id": reply.id,
        "content": full_content,
        "thinking": full_thinking,
        "created_at": reply.created_at.isoformat(),
        "pending_actions": pending_actions,
    }
    yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"
