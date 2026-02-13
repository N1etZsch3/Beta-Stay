# P0+P1: 打通AI助手 + 完善对话交互 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将AI助手从"空壳"变为真正可用：工具执行真实DB操作，确认流程闭环，前端正确渲染定价卡片和确认弹窗，支持会话切换。

**Architecture:** 使用`contextvars`将每次请求的DB Session注入到async工具中。写操作工具返回待确认数据，通过SSE新增事件类型(`action`/`pricing`)传递结构化数据到前端。前端根据事件类型渲染PriceCard或ConfirmPanel。待确认操作暂存于内存ActionStore，用户确认后执行入库。

**Tech Stack:**
- Backend: Python 3.14, FastAPI, SQLAlchemy 2.0 (async), LangChain 1.2.x
- Frontend: Vue 3 + uni-app + Pinia
- Key pattern: contextvars for DI, SSE structured events, in-memory action store

---

## Task 1: DB Context Layer for Tools

**Why:** LangChain `@tool` 函数需要访问当前请求的 DB Session。使用 Python `contextvars` 实现请求级别的依赖注入，让 async 工具函数在不接收 db 参数的情况下获取到 Session。

**Files:**
- Create: `backend/app/tools/context.py`

**Step 1: Create context module**

```python
# backend/app/tools/context.py
from contextvars import ContextVar
from sqlalchemy.ext.asyncio import AsyncSession

db_session_var: ContextVar[AsyncSession] = ContextVar("db_session")


def get_db_session() -> AsyncSession:
    """工具函数内部调用，获取当前请求的DB Session"""
    return db_session_var.get()
```

**Step 2: Verify the module imports correctly**

Run: `cd backend && python -c "from app.tools.context import db_session_var, get_db_session; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/tools/context.py
git commit -m "feat: add contextvars DB session layer for tool injection"
```

---

## Task 2: Rewrite property_query Tool (Read-Only)

**Why:** 当前 `property_query` 返回的是一个空 dict，不查询任何数据。改为真正查询 DB 并返回房源数据，LLM 才能基于实际数据回答问题。

**Files:**
- Modify: `backend/app/tools/property_tool.py`

**Step 1: Rewrite property_query to query DB**

```python
# backend/app/tools/property_tool.py
from langchain_core.tools import tool
from app.tools.context import get_db_session
from sqlalchemy import select
from app.models.property import Property


@tool
async def property_query(property_id: int | None = None) -> dict:
    """查询已有的民宿房源信息。可以传入property_id查询指定房源，不传则返回所有房源列表。"""
    db = get_db_session()

    if property_id:
        result = await db.execute(select(Property).where(Property.id == property_id))
        prop = result.scalar_one_or_none()
        if not prop:
            return {"success": False, "error": f"未找到ID为{property_id}的房源"}
        return {
            "success": True,
            "property": {
                "id": prop.id,
                "name": prop.name,
                "address": prop.address,
                "room_type": prop.room_type,
                "area": float(prop.area),
                "facilities": prop.facilities or {},
                "description": prop.description,
                "min_price": float(prop.min_price) if prop.min_price else None,
                "max_price": float(prop.max_price) if prop.max_price else None,
                "expected_return_rate": float(prop.expected_return_rate) if prop.expected_return_rate else None,
                "vacancy_tolerance": float(prop.vacancy_tolerance) if prop.vacancy_tolerance else None,
            },
        }
    else:
        result = await db.execute(select(Property).order_by(Property.created_at.desc()))
        props = result.scalars().all()
        return {
            "success": True,
            "total": len(list(props)),
            "properties": [
                {
                    "id": p.id,
                    "name": p.name,
                    "address": p.address,
                    "room_type": p.room_type,
                    "area": float(p.area),
                    "min_price": float(p.min_price) if p.min_price else None,
                    "max_price": float(p.max_price) if p.max_price else None,
                }
                for p in props
            ],
        }


property_query_tool = property_query
```

**Step 2: Run basic import check**

Run: `cd backend && python -c "from app.tools.property_tool import property_query_tool; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/tools/property_tool.py
git commit -m "feat: property_query tool now queries real DB data"
```

---

## Task 3: Rewrite property_create Tool (Write with Confirmation)

**Why:** 当前 `property_create` 返回空 dict，不做任何验证。改为验证数据并返回结构化待确认数据，附带 `pending_confirmation: True` 标记，实际入库操作推迟到用户确认后执行。

**Files:**
- Modify: `backend/app/tools/property_tool.py` (在 Task 2 基础上继续修改)

**Step 1: Rewrite property_create**

在 `backend/app/tools/property_tool.py` 中，修改 `property_create` 函数：

```python
@tool
async def property_create(
    name: str,
    address: str,
    room_type: str,
    area: float,
    facilities: dict | None = None,
    description: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    expected_return_rate: float | None = None,
    vacancy_tolerance: float | None = None,
) -> dict:
    """录入新的民宿房源信息。需要提供房源名称、地址、房型、面积等基础信息，以及房东偏好（最低价、最高价、期望收益率、空置容忍度）。返回的数据需要用户确认后才会入库。"""
    # 基础验证
    if area <= 0:
        return {"success": False, "error": "面积必须大于0"}
    if min_price is not None and max_price is not None and min_price > max_price:
        return {"success": False, "error": "最低价不能大于最高价"}

    data = {
        "name": name,
        "address": address,
        "room_type": room_type,
        "area": area,
        "facilities": facilities or {},
        "description": description,
        "min_price": min_price,
        "max_price": max_price,
        "expected_return_rate": expected_return_rate,
        "vacancy_tolerance": vacancy_tolerance,
    }

    return {
        "action": "create_property",
        "pending_confirmation": True,
        "data": data,
        "display": {
            "title": "新建房源",
            "items": {
                "名称": name,
                "地址": address,
                "房型": room_type,
                "面积": f"{area}㎡",
                "最低价": f"¥{min_price}" if min_price else "未设置",
                "最高价": f"¥{max_price}" if max_price else "未设置",
            },
        },
    }


property_create_tool = property_create
```

**Step 2: Verify import**

Run: `cd backend && python -c "from app.tools.property_tool import property_create_tool, property_query_tool; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/tools/property_tool.py
git commit -m "feat: property_create tool validates data and returns confirmation payload"
```

---

## Task 4: Rewrite pricing_calculate Tool (Compute + Save)

**Why:** 当前 `pricing_calculate` 是空壳。改为真正调用 PricingEngine 计算三档价格。定价记录直接入库（系统计算结果不需要用户确认），结果返回给 Agent 用于展示。

**Files:**
- Modify: `backend/app/tools/pricing_tool.py`

**Step 1: Rewrite pricing_calculate**

```python
# backend/app/tools/pricing_tool.py
from langchain_core.tools import tool
from datetime import date
from app.tools.context import get_db_session
from app.services.pricing_service import calculate_and_save


@tool
async def pricing_calculate(
    property_id: int,
    target_date: str,
    base_price: float | None = None,
) -> dict:
    """计算指定房源在目标日期的建议定价。返回保守价、建议价、激进价三档价格以及计算依据明细。target_date格式为YYYY-MM-DD。"""
    db = get_db_session()

    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        return {"success": False, "error": f"日期格式错误: {target_date}，请使用YYYY-MM-DD格式"}

    record = await calculate_and_save(db, property_id, target, base_price)
    if not record:
        return {"success": False, "error": f"未找到ID为{property_id}的房源"}

    return {
        "success": True,
        "pricing_record_id": record.id,
        "property_id": record.property_id,
        "target_date": record.target_date.isoformat(),
        "conservative_price": float(record.conservative_price),
        "suggested_price": float(record.suggested_price),
        "aggressive_price": float(record.aggressive_price),
        "calculation_details": record.calculation_details,
    }


pricing_calculate_tool = pricing_calculate
```

**Step 2: Verify import**

Run: `cd backend && python -c "from app.tools.pricing_tool import pricing_calculate_tool; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/tools/pricing_tool.py
git commit -m "feat: pricing_calculate tool calls real PricingEngine and saves record"
```

---

## Task 5: Rewrite feedback_record Tool (Write with Confirmation)

**Why:** 反馈是用户意图表达（采纳/拒绝/调整），需要确认后入库。改为返回待确认数据。

**Files:**
- Modify: `backend/app/tools/feedback_tool.py`

**Step 1: Rewrite feedback_record**

```python
# backend/app/tools/feedback_tool.py
from langchain_core.tools import tool


@tool
async def feedback_record(
    pricing_record_id: int,
    feedback_type: str,
    actual_price: float | None = None,
    note: str | None = None,
) -> dict:
    """记录房东对定价建议的反馈。feedback_type为adopted(采纳)、rejected(拒绝)或adjusted(调整)。如果是调整，需要提供actual_price。返回的数据需要用户确认后才会入库。"""
    # 验证
    valid_types = {"adopted", "rejected", "adjusted"}
    if feedback_type not in valid_types:
        return {"success": False, "error": f"feedback_type必须是 {valid_types} 之一"}
    if feedback_type == "adjusted" and actual_price is None:
        return {"success": False, "error": "调整反馈需要提供actual_price"}

    data = {
        "pricing_record_id": pricing_record_id,
        "feedback_type": feedback_type,
        "actual_price": actual_price,
        "note": note,
    }

    type_labels = {"adopted": "采纳建议价", "rejected": "拒绝建议", "adjusted": "手动调整"}
    return {
        "action": "record_feedback",
        "pending_confirmation": True,
        "data": data,
        "display": {
            "title": "定价反馈",
            "items": {
                "定价记录ID": str(pricing_record_id),
                "反馈类型": type_labels.get(feedback_type, feedback_type),
                "实际价格": f"¥{actual_price}" if actual_price else "—",
                "备注": note or "无",
            },
        },
    }


feedback_record_tool = feedback_record
```

**Step 2: Verify import**

Run: `cd backend && python -c "from app.tools.feedback_tool import feedback_record_tool; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/tools/feedback_tool.py
git commit -m "feat: feedback_record tool validates and returns confirmation payload"
```

---

## Task 6: Rewrite excel_parse Tool

**Why:** 当前返回空 dict。改为真正调用 `excel_parser` 解析文件并返回结构化数据。Excel 解析是读操作，不需要确认。但后续的数据导入可能需要确认（留作将来）。

**Files:**
- Modify: `backend/app/tools/excel_tool.py`

**Step 1: Rewrite excel_parse**

```python
# backend/app/tools/excel_tool.py
import os
from langchain_core.tools import tool
from app.tools.excel_parser import parse_excel


@tool
async def excel_parse(file_path: str) -> dict:
    """解析用户上传的Excel表格文件。file_path是上传文件的服务器端路径。系统会自动完成数据清洗（去空行、去重、去首尾空格）和统计分析。"""
    if not os.path.exists(file_path):
        return {"success": False, "error": f"文件不存在: {file_path}"}

    result = parse_excel(file_path)
    if not result["success"]:
        return result

    # 如果数据量太大，只返回摘要和前10条
    data = result.get("data", [])
    preview = data[:10] if len(data) > 10 else data

    return {
        "success": True,
        "total_rows": result["total_rows"],
        "stats": result["stats"],
        "preview": preview,
        "full_data_rows": len(data),
    }


excel_parse_tool = excel_parse
```

**Step 2: Verify import**

Run: `cd backend && python -c "from app.tools.excel_tool import excel_parse_tool; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/tools/excel_tool.py
git commit -m "feat: excel_parse tool calls real parser and returns structured data"
```

---

## Task 7: Action Store + Confirmation API

**Why:** 写操作工具（property_create, feedback_record）返回待确认数据后，需要一个地方暂存这些数据，以及一个 API 端点让用户确认后触发实际入库。

**Files:**
- Create: `backend/app/services/action_store.py`
- Modify: `backend/app/api/chat.py`

**Step 1: Create action store**

```python
# backend/app/services/action_store.py
"""
待确认操作的内存暂存。

生命周期：工具返回 pending_confirmation → 存入 → 用户确认 → 弹出执行 → 删除
生产环境应替换为 Redis 实现。
"""
import uuid
from typing import Any

_store: dict[str, dict[str, Any]] = {}


def save_pending_action(conversation_id: int, action_type: str, data: dict) -> str:
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
```

**Step 2: Add confirmation API endpoint to chat.py**

在 `backend/app/api/chat.py` 添加：

```python
# 在文件顶部 import 区域添加:
from app.services.action_store import pop_pending_action
from app.services import property_service, feedback_service

# 添加请求模型:
class ConfirmAction(BaseModel):
    action_id: str

# 添加新路由:
@router.post("/conversations/{conversation_id}/confirm")
async def confirm_action(conversation_id: int, data: ConfirmAction, db: AsyncSession = Depends(get_db)):
    """用户确认待执行操作"""
    action = pop_pending_action(data.action_id)
    if not action:
        raise HTTPException(status_code=404, detail="操作已过期或不存在")
    if action["conversation_id"] != conversation_id:
        raise HTTPException(status_code=400, detail="操作不属于当前会话")

    action_type = action["action_type"]
    action_data = action["data"]

    if action_type == "create_property":
        result = await property_service.create_property(db, action_data)
        # 保存系统消息
        await conversation_service.save_message(
            db, conversation_id, "assistant",
            f"✅ 房源「{result.name}」已成功录入（ID: {result.id}）"
        )
        return {"success": True, "type": "property", "id": result.id, "name": result.name}

    elif action_type == "record_feedback":
        result = await feedback_service.create_feedback(db, action_data)
        await conversation_service.save_message(
            db, conversation_id, "assistant",
            f"✅ 反馈已记录（ID: {result.id}，类型: {result.feedback_type}）"
        )
        return {"success": True, "type": "feedback", "id": result.id}

    else:
        raise HTTPException(status_code=400, detail=f"未知操作类型: {action_type}")
```

**Step 3: Verify imports**

Run: `cd backend && python -c "from app.services.action_store import save_pending_action, pop_pending_action; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add backend/app/services/action_store.py backend/app/api/chat.py
git commit -m "feat: add action store and confirmation API endpoint"
```

---

## Task 8: Update chat_service — DB Context + Tool Event Propagation

**Why:** 这是最关键的改动。chat_service 需要：(1) 在调用 Agent 前设置 DB context，让工具可以访问 Session；(2) 拦截 `on_tool_end` 事件，识别待确认操作并存入 ActionStore；(3) 通过 SSE 新增事件类型将结构化数据传递给前端。

**Files:**
- Modify: `backend/app/services/chat_service.py`

**Step 1: Rewrite stream_message**

完整替换 `backend/app/services/chat_service.py`：

```python
# backend/app/services/chat_service.py
import json
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.conversation_service import get_messages, save_message
from app.tools.context import db_session_var
from app.services.action_store import save_pending_action


async def process_message(db: AsyncSession, conversation_id: int, user_content: str) -> dict:
    """处理用户消息（非流式）：保存消息 → 构建历史 → 调用Agent → 保存回复"""
    await save_message(db, conversation_id, "user", user_content)

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


async def stream_message(db: AsyncSession, conversation_id: int, user_content: str) -> AsyncGenerator[str, None]:
    """流式处理用户消息，yield SSE格式事件

    SSE 事件类型:
    - thinking: AI思考过程片段
    - content: AI回复正文片段
    - action: 待确认操作（前端应显示确认弹窗）
    - pricing: 定价计算结果（前端应显示PriceCard）
    - done: 流结束，附带完整消息信息
    """
    await save_message(db, conversation_id, "user", user_content)

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
                    tool_output = event["data"].get("output")
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
                        elif tool_output.get("success") and tool_output.get("pricing_record_id"):
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

    reply = await save_message(db, conversation_id, "assistant", full_content, tool_calls=tool_calls_meta)

    done_data = {
        "id": reply.id,
        "content": full_content,
        "thinking": full_thinking,
        "created_at": reply.created_at.isoformat(),
        "pending_actions": pending_actions,
    }
    yield f"event: done\ndata: {json.dumps(done_data, ensure_ascii=False)}\n\n"
```

**Step 2: Verify import chain**

Run: `cd backend && python -c "from app.services.chat_service import stream_message, process_message; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add backend/app/services/chat_service.py
git commit -m "feat: chat_service injects DB context, propagates tool events via SSE"
```

---

## Task 9: Update Frontend SSE Event Handling

**Why:** 后端新增了 `action` 和 `pricing` SSE 事件类型，前端需要解析这些事件并存储数据，以便 Chat 页面正确渲染 PriceCard 和 ConfirmPanel。

**Files:**
- Modify: `frontend/src/api/chat.ts` — 新增回调类型
- Modify: `frontend/src/stores/chat.ts` — 新增状态字段和处理逻辑

**Step 1: Update chat API types**

修改 `frontend/src/api/chat.ts`，扩展 `sendMessageStream` 的回调：

在 callbacks 类型定义中添加 `onAction` 和 `onPricing`：

```typescript
// frontend/src/api/chat.ts — sendMessageStream 的 callbacks 参数类型更新为:
export interface StreamCallbacks {
  onThinking?: (chunk: string) => void
  onContent?: (chunk: string) => void
  onAction?: (data: {
    action_id: string
    action_type: string
    display: { title: string; items: Record<string, string> }
    data: Record<string, any>
  }) => void
  onPricing?: (data: {
    pricing_record_id: number
    property_id: number
    target_date: string
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }) => void
  onDone?: (data: {
    id: number
    content: string
    thinking: string
    created_at: string
    pending_actions: any[]
  }) => void
  onError?: (error: Error) => void
}
```

在 SSE 解析 switch 中添加对 `action` 和 `pricing` 事件的处理：

```typescript
// 在 SSE 事件分发区域，现有的 thinking/content/done 之后添加:
else if (currentEvent === 'action' && callbacks.onAction) {
  callbacks.onAction(parsed)
} else if (currentEvent === 'pricing' && callbacks.onPricing) {
  callbacks.onPricing(parsed)
}
```

同时新增确认 API 函数：

```typescript
export function confirmAction(conversationId: number, actionId: string) {
  return request({
    url: `/chat/conversations/${conversationId}/confirm`,
    method: 'POST',
    data: { action_id: actionId },
  })
}
```

**Step 2: Update chat store**

修改 `frontend/src/stores/chat.ts`，新增 `pendingAction` 和 `pricingResult` 状态：

在 store 中添加新的 ref：

```typescript
// 新增状态
const pendingAction = ref<{
  action_id: string
  action_type: string
  display: { title: string; items: Record<string, string> }
  data: Record<string, any>
} | null>(null)

const pricingResult = ref<{
  pricing_record_id: number
  property_id: number
  target_date: string
  conservative_price: number
  suggested_price: number
  aggressive_price: number
} | null>(null)
```

在 `sendMessage` 中的 `sendMessageStream` 回调里添加：

```typescript
onAction: (data) => {
  pendingAction.value = data
},
onPricing: (data) => {
  pricingResult.value = data
},
```

在 `onDone` 回调中，清空 pricingResult（因为消息已完成）：
```typescript
// 在 onDone 中的 resolve() 之前:
// 不清空 pendingAction，因为需要等用户确认后才清空
// pricingResult 保留，直到下一轮消息
```

新增 `confirmPendingAction` 方法：

```typescript
async function confirmPendingAction() {
  if (!pendingAction.value || !currentConversationId.value) return
  const result = await chatApi.confirmAction(
    currentConversationId.value,
    pendingAction.value.action_id,
  )
  pendingAction.value = null
  // 追加确认成功消息
  if (result && result.success) {
    const confirmMsg = result.type === 'property'
      ? `✅ 房源「${result.name}」已成功录入`
      : `✅ 反馈已记录`
    messages.value.push({
      role: 'assistant',
      content: confirmMsg,
      created_at: new Date().toISOString(),
    })
  }
  return result
}

function cancelPendingAction() {
  pendingAction.value = null
}
```

在 return 中导出新增的状态和方法：

```typescript
return {
  conversations, currentConversationId, messages, loading, thinking, error,
  pendingAction, pricingResult,
  createConversation, sendMessage, loadMessages,
  confirmPendingAction, cancelPendingAction,
}
```

**Step 3: Commit**

```bash
git add frontend/src/api/chat.ts frontend/src/stores/chat.ts
git commit -m "feat: frontend handles action/pricing SSE events with confirm flow"
```

---

## Task 10: Integrate PriceCard in Chat Page

**Why:** PriceCard 组件已存在但未在聊天页面中使用。当后端返回 `pricing` 事件时，应在对话中渲染定价卡片，并支持直接在卡片上操作（采纳/拒绝/调整）。

**Files:**
- Modify: `frontend/src/pages/chat/index.vue`
- Modify: `frontend/src/stores/chat.ts` (ChatMessage 接口扩展)

**Step 1: Extend ChatMessage interface**

在 `frontend/src/stores/chat.ts` 中扩展 ChatMessage：

```typescript
export interface ChatMessage {
  id?: number
  role: string
  content: string
  thinking?: string
  created_at: string
  // 新增：消息附带的结构化数据
  pricing?: {
    pricing_record_id: number
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }
}
```

在 `sendMessage` 的 `onDone` 回调中，如果当前有 pricingResult，附加到消息上：

```typescript
// onDone 回调内，在 msg.content = data.content 之后:
if (pricingResult.value) {
  msg.pricing = {
    pricing_record_id: pricingResult.value.pricing_record_id,
    conservative_price: pricingResult.value.conservative_price,
    suggested_price: pricingResult.value.suggested_price,
    aggressive_price: pricingResult.value.aggressive_price,
  }
  pricingResult.value = null
}
```

**Step 2: Update chat page to render PriceCard**

在 `frontend/src/pages/chat/index.vue` 的 template 中，ChatBubble 之后添加 PriceCard 渲染：

```html
<!-- Messages -->
<template v-for="(msg, idx) in chatStore.messages" :key="idx">
  <ChatBubble :message="msg" />
  <!-- 定价卡片（跟在助手消息后面） -->
  <PriceCard
    v-if="msg.role === 'assistant' && msg.pricing"
    :pricing="msg.pricing"
    @adopt="handleAdopt(msg.pricing!.pricing_record_id, $event)"
    @reject="handleReject(msg.pricing!.pricing_record_id)"
    @adjust="handleAdjust(msg.pricing!.pricing_record_id)"
  />
</template>
```

在 script 中添加反馈处理函数：

```typescript
async function handleAdopt(pricingRecordId: number, price: number) {
  inputText.value = `我采纳建议价 ¥${price}（定价记录ID: ${pricingRecordId}）`
  await handleSend()
}

function handleReject(pricingRecordId: number) {
  inputText.value = `这个定价不太合适（定价记录ID: ${pricingRecordId}）`
  handleSend()
}

function handleAdjust(pricingRecordId: number) {
  inputText.value = `我想手动调整价格（定价记录ID: ${pricingRecordId}），调整为 `
  // 留给用户输入价格
}
```

**Step 3: Wire up ConfirmPanel with real data**

在 `frontend/src/pages/chat/index.vue` 中替换 ConfirmPanel 的逻辑：

```html
<!-- Confirm panel -->
<ConfirmPanel
  :visible="!!chatStore.pendingAction"
  :data="chatStore.pendingAction?.display?.items || {}"
  @confirm="handleConfirmAction"
  @cancel="chatStore.cancelPendingAction()"
/>
```

修改 script：

```typescript
// 删除旧的 showConfirm / confirmData ref 和旧的 handleConfirm 函数
// 替换为:
async function handleConfirmAction() {
  try {
    await chatStore.confirmPendingAction()
    scrollToBottom()
  } catch {
    // 确认失败，保持弹窗
  }
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/chat/index.vue frontend/src/stores/chat.ts
git commit -m "feat: integrate PriceCard and ConfirmPanel into chat with real data flow"
```

---

## Task 11: Add Conversation List & Switching

**Why:** 当前聊天页面没有会话列表，用户无法查看历史会话或切换会话。添加侧边抽屉式会话列表。

**Files:**
- Modify: `frontend/src/pages/chat/index.vue`
- Modify: `frontend/src/stores/chat.ts`

**Step 1: Add loadConversations to store**

在 `frontend/src/stores/chat.ts` 中添加：

```typescript
async function loadConversations() {
  conversations.value = await chatApi.listConversations()
}

async function switchConversation(conversationId: number) {
  currentConversationId.value = conversationId
  pendingAction.value = null
  pricingResult.value = null
  await loadMessages(conversationId)
}

async function newConversation() {
  currentConversationId.value = null
  messages.value = []
  pendingAction.value = null
  pricingResult.value = null
}
```

在 return 中导出新方法：

```typescript
return {
  // ... 已有导出 ...
  loadConversations, switchConversation, newConversation,
}
```

**Step 2: Add conversation drawer to chat page**

在 `frontend/src/pages/chat/index.vue` 的 template 中 header 区域添加：

```html
<!-- Header -->
<view class="chat-header">
  <view class="header-left" @click="showDrawer = !showDrawer">
    <text class="menu-icon">☰</text>
  </view>
  <text class="header-title">{{ currentTitle }}</text>
  <view class="header-right" @click="handleNewChat">
    <text class="new-icon">+</text>
  </view>
</view>

<!-- Conversation drawer -->
<view v-if="showDrawer" class="drawer-mask" @click="showDrawer = false">
  <view class="drawer-panel" @click.stop>
    <view class="drawer-title">历史会话</view>
    <scroll-view scroll-y class="drawer-list">
      <view
        v-for="conv in chatStore.conversations"
        :key="conv.id"
        :class="['drawer-item', { active: conv.id === chatStore.currentConversationId }]"
        @click="handleSwitchConv(conv.id)"
      >
        <text class="drawer-item-title">{{ conv.title || '新对话' }}</text>
      </view>
      <view v-if="chatStore.conversations.length === 0" class="drawer-empty">
        <text>暂无历史会话</text>
      </view>
    </scroll-view>
  </view>
</view>
```

在 script 中添加：

```typescript
import { ref, nextTick, watch, onMounted, computed } from 'vue'

const showDrawer = ref(false)

const currentTitle = computed(() => {
  if (!chatStore.currentConversationId) return '新对话'
  const conv = chatStore.conversations.find(c => c.id === chatStore.currentConversationId)
  return conv?.title || '对话'
})

onMounted(() => {
  chatStore.loadConversations()
})

function handleNewChat() {
  chatStore.newConversation()
  showDrawer.value = false
}

async function handleSwitchConv(convId: number) {
  await chatStore.switchConversation(convId)
  showDrawer.value = false
  await nextTick()
  scrollToBottom()
}
```

**Step 3: Add drawer styles**

在 `<style scoped lang="scss">` 中添加 header 和 drawer 样式：

```scss
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24rpx;
  height: 88rpx;
  background: #fff;
  border-bottom: 1rpx solid $uni-border-color;
  flex-shrink: 0;
}

.header-left, .header-right {
  width: 72rpx;
  height: 72rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-icon, .new-icon {
  font-size: 40rpx;
  color: $uni-text-color;
}

.header-title {
  font-size: 32rpx;
  font-weight: 600;
  color: $uni-color-title;
}

.drawer-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.4);
  z-index: 998;
}

.drawer-panel {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 70%;
  max-width: 600rpx;
  background: #fff;
  padding: 40rpx 0;
  box-shadow: 4rpx 0 16rpx rgba(0,0,0,0.1);
}

.drawer-title {
  font-size: 32rpx;
  font-weight: 700;
  padding: 0 32rpx 24rpx;
  border-bottom: 1rpx solid $uni-border-color;
  color: $uni-color-title;
}

.drawer-list {
  height: calc(100% - 80rpx);
}

.drawer-item {
  padding: 24rpx 32rpx;
  border-bottom: 1rpx solid #f5f5f5;
  transition: background 0.2s;

  &.active {
    background: rgba($uni-color-primary, 0.08);
  }

  &:active {
    background: $uni-bg-color-hover;
  }
}

.drawer-item-title {
  font-size: 28rpx;
  color: $uni-text-color;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-empty {
  padding: 60rpx 32rpx;
  text-align: center;
  color: $uni-text-color-placeholder;
  font-size: 26rpx;
}
```

**Step 4: Commit**

```bash
git add frontend/src/pages/chat/index.vue frontend/src/stores/chat.ts
git commit -m "feat: add conversation list drawer and switching"
```

---

## Task 12: End-to-End Verification

**Why:** 验证整个链路是否跑通：前端发消息 → 后端 Agent 调用工具 → 工具执行真实操作 → SSE 事件正确传播 → 前端正确渲染。

**Files:** 无新建文件

**Step 1: Start backend**

```bash
cd backend
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Step 2: Start frontend**

```bash
cd frontend
npm run dev:h5
```

**Step 3: Test property query flow**

1. 在前端聊天页面输入："帮我查一下我有哪些房源"
2. 预期：Agent 调用 `property_query`，返回实际房源列表（如果为空则提示没有房源）
3. 验证：AI 回复中包含实际数据或"暂无房源"

**Step 4: Test property create flow**

1. 输入："帮我录入一个新房源，名称叫测试民宿，地址是杭州西湖区，大床房，面积30平米，最低价200，最高价500"
2. 预期：
   - Agent 调用 `property_create`
   - 前端收到 `action` SSE 事件
   - ConfirmPanel 弹出，显示房源信息
   - 点击"确认入库"
   - 系统消息"房源已成功录入"出现

**Step 5: Test pricing flow**

1. 输入："帮我算一下测试民宿明天的定价"
2. 预期：
   - Agent 调用 `pricing_calculate`
   - 前端收到 `pricing` SSE 事件
   - PriceCard 在消息下方显示三档价格
   - 点击"采纳建议价"触发反馈流程

**Step 6: Test conversation switching**

1. 点击左上角 ☰ 按钮
2. 预期：侧边栏弹出，显示当前会话
3. 点击 + 新建对话
4. 预期：对话清空，可开始新的对话

**Step 7: Final commit**

如果有修复任何问题：
```bash
git add -A
git commit -m "fix: end-to-end verification fixes"
```

---

## Summary

| Task | 内容 | 类型 |
|------|------|------|
| 1 | DB Context Layer (contextvars) | 基础设施 |
| 2 | property_query 真实查询 | 工具重写 |
| 3 | property_create 验证+待确认 | 工具重写 |
| 4 | pricing_calculate 调用引擎 | 工具重写 |
| 5 | feedback_record 验证+待确认 | 工具重写 |
| 6 | excel_parse 真实解析 | 工具重写 |
| 7 | ActionStore + 确认API | 后端新增 |
| 8 | chat_service 注入+事件传播 | 后端重写 |
| 9 | 前端 SSE 事件处理 | 前端修改 |
| 10 | PriceCard + ConfirmPanel 集成 | 前端修改 |
| 11 | 会话列表 + 切换 | 前端新增 |
| 12 | 端到端验证 | 测试 |

依赖关系：Task 1 → Tasks 2-6 → Tasks 7-8 → Tasks 9-11 → Task 12
