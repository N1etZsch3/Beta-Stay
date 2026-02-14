# BetaStay P2: 增强迭代 - RAG/向量数据库 + 工具补全 + 缓存层

> **For Claude:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 接入向量数据库实现RAG检索增强，补全缺失的LangChain工具，接入Redis缓存层，为生产环境做准备。

**Architecture:** 使用Milvus/Zilliz作为向量数据库，Dashscope text-embedding-v4作为embedding模型。房源描述和历史对话向量化存储，Agent回答前先检索相关上下文注入prompt。Redis用于会话状态缓存和热点数据缓存。补全历史查询工具，让Agent能查询定价历史和反馈记录。

**Tech Stack:**
- Vector DB: Milvus (pymilvus) 或 Zilliz Cloud
- Embedding: Dashscope text-embedding-v4
- Cache: Redis 7+ (aioredis)
- Backend: Python 3.14, FastAPI, LangChain 1.2.x

**环境变量（已配置）：**
- `DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4`
- `REDIS_URL=redis://:password@host:port/db`

**注意：** text-embedding-v4 暂无额度，Task 1-3 可先搭建代码骨架，等额度到位后再跑通测试。

---

## 文件结构规划

```
backend/app/
├── core/
│   ├── config.py              # 修改：添加 MILVUS_* 和 EMBEDDING 配置
│   ├── redis.py               # 新建：Redis 连接池
│   └── milvus.py              # 新建：Milvus 连接
├── services/
│   ├── embedding_service.py   # 新建：文本向量化服务
│   ├── vector_service.py      # 新建：向量存储/检索服务
│   └── cache_service.py       # 新建：Redis 缓存服务
├── tools/
│   ├── history_tool.py        # 新建：历史查询工具
│   └── datetime_tool.py       # 已完成
└── agent/
    ├── betastay_agent.py      # 修改：注册新工具
    ├── prompts.py             # 修改：添加 RAG 上下文注入
    └── rag.py                 # 新建：RAG 检索链
```

---

## Chunk 1: 基础设施层

### Task 1: Redis 连接池与缓存服务

**Files:**
- Create: `backend/app/core/redis.py`
- Create: `backend/app/services/cache_service.py`
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_cache_service.py`

- [ ] **Step 1: 添加 Redis 配置到 config.py**

在 `backend/app/core/config.py` 的 Settings 类中确认 REDIS_URL 已存在（已有）。

- [ ] **Step 2: 创建 Redis 连接模块**

```python
# backend/app/core/redis.py
import redis.asyncio as aioredis
from app.core.config import settings

redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 连接"""
    global redis_pool
    if redis_pool is None:
        redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_pool


async def close_redis():
    """关闭 Redis 连接"""
    global redis_pool
    if redis_pool:
        await redis_pool.close()
        redis_pool = None
```

- [ ] **Step 3: 创建缓存服务**

```python
# backend/app/services/cache_service.py
import json
from typing import Any
from app.core.redis import get_redis

DEFAULT_TTL = 3600  # 1 hour


async def cache_get(key: str) -> Any | None:
    """获取缓存值"""
    redis = await get_redis()
    value = await redis.get(key)
    if value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return None


async def cache_set(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """设置缓存值"""
    redis = await get_redis()
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    await redis.set(key, value, ex=ttl)
    return True


async def cache_delete(key: str) -> bool:
    """删除缓存"""
    redis = await get_redis()
    await redis.delete(key)
    return True


async def cache_get_or_set(key: str, factory, ttl: int = DEFAULT_TTL) -> Any:
    """获取缓存，不存在则调用 factory 生成并缓存"""
    value = await cache_get(key)
    if value is not None:
        return value
    value = await factory() if callable(factory) else factory
    await cache_set(key, value, ttl)
    return value
```

- [ ] **Step 4: 写测试**

```python
# backend/tests/test_cache_service.py
import pytest


@pytest.mark.asyncio
async def test_cache_set_and_get():
    from app.services.cache_service import cache_set, cache_get, cache_delete

    key = "test:cache:key"
    value = {"name": "测试", "price": 500}

    await cache_set(key, value, ttl=60)
    result = await cache_get(key)
    assert result == value

    await cache_delete(key)
    result = await cache_get(key)
    assert result is None
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_cache_service.py -v`
Expected: PASS（需要 Redis 服务可用）

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/redis.py backend/app/services/cache_service.py backend/tests/test_cache_service.py
git commit -m "feat: add Redis connection pool and cache service"
```

---

### Task 2: Embedding 服务（Dashscope text-embedding-v4）

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/embedding_service.py`
- Test: `backend/tests/test_embedding_service.py`

- [ ] **Step 1: 添加 Embedding 配置**

```python
# backend/app/core/config.py - 在 Settings 类中添加
DASHSCOPE_EMBEDDING_MODEL: str = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
```

- [ ] **Step 2: 创建 Embedding 服务**

```python
# backend/app/services/embedding_service.py
import dashscope
from dashscope import TextEmbedding
from app.core.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY


async def get_embedding(text: str) -> list[float]:
    """获取单个文本的向量表示"""
    response = TextEmbedding.call(
        model=settings.DASHSCOPE_EMBEDDING_MODEL,
        input=text,
    )
    if response.status_code == 200:
        return response.output["embeddings"][0]["embedding"]
    raise Exception(f"Embedding failed: {response.code} - {response.message}")


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """批量获取文本向量"""
    response = TextEmbedding.call(
        model=settings.DASHSCOPE_EMBEDDING_MODEL,
        input=texts,
    )
    if response.status_code == 200:
        return [item["embedding"] for item in response.output["embeddings"]]
    raise Exception(f"Embedding failed: {response.code} - {response.message}")
```

- [ ] **Step 3: 写测试（标记为 skip 直到有额度）**

```python
# backend/tests/test_embedding_service.py
import pytest


@pytest.mark.skip(reason="text-embedding-v4 暂无额度")
@pytest.mark.asyncio
async def test_get_embedding():
    from app.services.embedding_service import get_embedding

    text = "杭州西湖边的精品民宿，三室两厅"
    embedding = await get_embedding(text)
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.skip(reason="text-embedding-v4 暂无额度")
@pytest.mark.asyncio
async def test_get_embeddings_batch():
    from app.services.embedding_service import get_embeddings

    texts = ["民宿A", "民宿B", "民宿C"]
    embeddings = await get_embeddings(texts)
    assert len(embeddings) == 3
```

- [ ] **Step 4: 验证模块可导入**

Run: `cd backend && python -c "from app.services.embedding_service import get_embedding, get_embeddings; print('OK')"`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/services/embedding_service.py backend/tests/test_embedding_service.py
git commit -m "feat: add Dashscope embedding service for text vectorization"
```

---

### Task 3: Milvus 向量数据库连接与服务

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/core/milvus.py`
- Create: `backend/app/services/vector_service.py`
- Modify: `backend/requirements.txt`
- Test: `backend/tests/test_vector_service.py`

- [ ] **Step 1: 添加 pymilvus 依赖**

在 `backend/requirements.txt` 添加：

```
# Vector database
pymilvus>=2.4.0
```

- [ ] **Step 2: 添加 Milvus 配置**

```python
# backend/app/core/config.py - 在 Settings 类中添加
MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION_NAME: str = os.getenv("MILVUS_COLLECTION_NAME", "betastay_vectors")
EMBEDDING_DIM: int = 1536  # text-embedding-v4 输出维度
```

- [ ] **Step 3: 创建 Milvus 连接模块**

```python
# backend/app/core/milvus.py
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from app.core.config import settings

_connected = False


def connect_milvus():
    """连接 Milvus"""
    global _connected
    if not _connected:
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
        )
        _connected = True


def get_or_create_collection() -> Collection:
    """获取或创建向量集合"""
    connect_milvus()
    collection_name = settings.MILVUS_COLLECTION_NAME

    if utility.has_collection(collection_name):
        return Collection(collection_name)

    # 创建 schema
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=50),  # property/conversation
        FieldSchema(name="source_id", dtype=DataType.INT64),  # property_id 或 conversation_id
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM),
    ]
    schema = CollectionSchema(fields, description="BetaStay RAG vectors")
    collection = Collection(collection_name, schema)

    # 创建索引
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    collection.create_index("embedding", index_params)
    return collection
```

- [ ] **Step 4: 创建向量服务**

```python
# backend/app/services/vector_service.py
from app.core.milvus import get_or_create_collection
from app.services.embedding_service import get_embedding, get_embeddings


async def store_vector(source_type: str, source_id: int, content: str) -> int:
    """存储单个向量"""
    collection = get_or_create_collection()
    embedding = await get_embedding(content)

    data = [
        [source_type],
        [source_id],
        [content],
        [embedding],
    ]
    result = collection.insert(data)
    collection.flush()
    return result.primary_keys[0]


async def store_vectors(items: list[dict]) -> list[int]:
    """批量存储向量
    items: [{"source_type": "property", "source_id": 1, "content": "..."}]
    """
    if not items:
        return []

    collection = get_or_create_collection()
    contents = [item["content"] for item in items]
    embeddings = await get_embeddings(contents)

    data = [
        [item["source_type"] for item in items],
        [item["source_id"] for item in items],
        contents,
        embeddings,
    ]
    result = collection.insert(data)
    collection.flush()
    return list(result.primary_keys)


async def search_similar(query: str, top_k: int = 5, source_type: str | None = None) -> list[dict]:
    """检索相似内容"""
    collection = get_or_create_collection()
    collection.load()

    query_embedding = await get_embedding(query)

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    expr = f'source_type == "{source_type}"' if source_type else None

    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=["source_type", "source_id", "content"],
    )

    return [
        {
            "id": hit.id,
            "score": hit.score,
            "source_type": hit.entity.get("source_type"),
            "source_id": hit.entity.get("source_id"),
            "content": hit.entity.get("content"),
        }
        for hit in results[0]
    ]


async def delete_by_source(source_type: str, source_id: int) -> int:
    """删除指定来源的向量"""
    collection = get_or_create_collection()
    expr = f'source_type == "{source_type}" and source_id == {source_id}'
    result = collection.delete(expr)
    return result.delete_count
```

- [ ] **Step 5: 写测试（标记为 skip）**

```python
# backend/tests/test_vector_service.py
import pytest


@pytest.mark.skip(reason="需要 Milvus 服务和 embedding 额度")
@pytest.mark.asyncio
async def test_store_and_search():
    from app.services.vector_service import store_vector, search_similar, delete_by_source

    # 存储
    vec_id = await store_vector("property", 999, "西湖边精品民宿，三室两厅，湖景房")
    assert vec_id > 0

    # 检索
    results = await search_similar("西湖民宿", top_k=3)
    assert len(results) > 0
    assert any(r["source_id"] == 999 for r in results)

    # 清理
    await delete_by_source("property", 999)
```

- [ ] **Step 6: 验证模块可导入**

Run: `cd backend && python -c "from app.services.vector_service import store_vector, search_similar; print('OK')"`
Expected: `OK`（可能因 Milvus 未连接而警告，但导入应成功）

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/core/config.py backend/app/core/milvus.py backend/app/services/vector_service.py backend/tests/test_vector_service.py
git commit -m "feat: add Milvus vector database connection and vector service"
```

---

## Chunk 2: 工具层补全

### Task 4: 历史查询工具（history_tool）

**Files:**
- Create: `backend/app/tools/history_tool.py`
- Modify: `backend/app/agent/betastay_agent.py`
- Modify: `backend/app/agent/prompts.py`
- Test: `backend/tests/test_tools.py`

- [ ] **Step 1: 创建历史查询工具**

```python
# backend/app/tools/history_tool.py
from langchain_core.tools import tool
from sqlalchemy import select
from app.tools.context import get_db_session
from app.models.pricing import PricingRecord
from app.models.feedback import Feedback


@tool
async def history_query(
    property_id: int,
    query_type: str = "pricing",
    limit: int = 10,
) -> dict:
    """查询房源的定价历史或反馈记录。

    Args:
        property_id: 房源ID
        query_type: 查询类型，"pricing"查定价历史，"feedback"查反馈记录
        limit: 返回记录数量，默认10条
    """
    db = get_db_session()

    if query_type == "pricing":
        result = await db.execute(
            select(PricingRecord)
            .where(PricingRecord.property_id == property_id)
            .order_by(PricingRecord.created_at.desc())
            .limit(limit)
        )
        records = result.scalars().all()
        return {
            "success": True,
            "query_type": "pricing",
            "total": len(records),
            "records": [
                {
                    "id": r.id,
                    "target_date": r.target_date.isoformat(),
                    "conservative_price": float(r.conservative_price),
                    "suggested_price": float(r.suggested_price),
                    "aggressive_price": float(r.aggressive_price),
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ],
        }

    elif query_type == "feedback":
        # 查询该房源所有定价记录的反馈
        result = await db.execute(
            select(Feedback, PricingRecord)
            .join(PricingRecord, Feedback.pricing_record_id == PricingRecord.id)
            .where(PricingRecord.property_id == property_id)
            .order_by(Feedback.created_at.desc())
            .limit(limit)
        )
        rows = result.all()
        type_labels = {"adopted": "采纳", "rejected": "拒绝", "adjusted": "调整"}
        return {
            "success": True,
            "query_type": "feedback",
            "total": len(rows),
            "records": [
                {
                    "id": fb.id,
                    "pricing_record_id": fb.pricing_record_id,
                    "target_date": pr.target_date.isoformat(),
                    "suggested_price": float(pr.suggested_price),
                    "feedback_type": type_labels.get(fb.feedback_type, fb.feedback_type),
                    "actual_price": float(fb.actual_price) if fb.actual_price else None,
                    "note": fb.note,
                    "created_at": fb.created_at.isoformat(),
                }
                for fb, pr in rows
            ],
        }

    else:
        return {"success": False, "error": f"query_type 必须是 'pricing' 或 'feedback'，收到: {query_type}"}


history_query_tool = history_query
```

- [ ] **Step 2: 注册工具到 Agent**

修改 `backend/app/agent/betastay_agent.py`：

```python
# 添加 import
from app.tools.history_tool import history_query_tool

# 在 get_tools() 中添加
def get_tools():
    return [
        property_create_tool,
        property_query_tool,
        show_property_form_tool,
        pricing_calculate_tool,
        feedback_record_tool,
        excel_parse_tool,
        get_current_time_tool,
        history_query_tool,  # 新增
    ]
```

- [ ] **Step 3: 更新 System Prompt**

在 `backend/app/agent/prompts.py` 的可用工具列表中添加：

```
- history_query: 查询定价历史和反馈记录
- get_current_time: 获取当前日期时间
```

- [ ] **Step 4: 添加工具测试**

在 `backend/tests/test_tools.py` 中添加：

```python
def test_history_tool_schema():
    from app.tools.history_tool import history_query_tool
    assert history_query_tool.name == "history_query"


def test_datetime_tool_schema():
    from app.tools.datetime_tool import get_current_time_tool
    assert get_current_time_tool.name == "get_current_time"
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/tools/history_tool.py backend/app/agent/betastay_agent.py backend/app/agent/prompts.py backend/tests/test_tools.py
git commit -m "feat: add history_query tool for pricing and feedback history"
```

---

## Chunk 3: RAG 集成

### Task 5: RAG 检索链集成到 Agent

**Files:**
- Create: `backend/app/agent/rag.py`
- Modify: `backend/app/services/chat_service.py`
- Modify: `backend/app/agent/prompts.py`

- [ ] **Step 1: 创建 RAG 模块**

```python
# backend/app/agent/rag.py
from app.services.vector_service import search_similar


async def retrieve_context(query: str, top_k: int = 3) -> str:
    """检索相关上下文，格式化为 prompt 注入内容"""
    try:
        results = await search_similar(query, top_k=top_k)
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results, 1):
            source_label = "房源信息" if r["source_type"] == "property" else "历史对话"
            context_parts.append(f"[{source_label} #{r['source_id']}] {r['content']}")

        return "\n".join(context_parts)
    except Exception:
        # Milvus 未连接或其他错误，静默降级
        return ""


def build_rag_prompt(base_prompt: str, context: str) -> str:
    """将检索到的上下文注入到 system prompt"""
    if not context:
        return base_prompt

    rag_section = f"""
## 相关上下文（基于用户问题检索）

以下是与用户问题相关的已有数据，回答时应优先参考：

{context}

---
"""
    return base_prompt + rag_section
```

- [ ] **Step 2: 在 chat_service 中集成 RAG（可选启用）**

修改 `backend/app/services/chat_service.py` 中的 `_invoke_agent_stream` 函数，在调用 agent 前检索上下文：

```python
# 在 _invoke_agent_stream 函数开头添加（agent 调用前）
# RAG 上下文检索（可选，需要 Milvus 可用）
rag_context = ""
try:
    from app.agent.rag import retrieve_context
    user_query = messages[-1]["content"] if messages else ""
    rag_context = await retrieve_context(user_query, top_k=3)
except Exception:
    pass  # RAG 不可用时静默降级
```

- [ ] **Step 3: 更新 prompts.py 添加 RAG 说明**

在 `backend/app/agent/prompts.py` 的核心原则中强化：

```
3. **所有你的回答必须基于已有数据** - 优先使用检索到的上下文信息，如果没有相关数据，明确告知用户
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/agent/rag.py backend/app/services/chat_service.py backend/app/agent/prompts.py
git commit -m "feat: add RAG retrieval chain for context-aware responses"
```

---

### Task 6: 房源向量化钩子

**Files:**
- Modify: `backend/app/api/chat.py`
- Modify: `backend/app/services/property_service.py`

- [ ] **Step 1: 在房源创建后触发向量化**

修改 `backend/app/services/property_service.py`：

```python
async def create_property(db: AsyncSession, data: dict) -> Property:
    prop = Property(**data)
    db.add(prop)
    await db.commit()
    await db.refresh(prop)

    # 异步触发向量化（不阻塞主流程）
    try:
        from app.services.vector_service import store_vector
        content = f"{prop.name} - {prop.address} - {prop.room_type} - {prop.area}平米"
        if prop.description:
            content += f" - {prop.description}"
        await store_vector("property", prop.id, content)
    except Exception:
        pass  # 向量化失败不影响主流程

    return prop
```

- [ ] **Step 2: 在房源删除时清理向量**

```python
async def delete_property(db: AsyncSession, property_id: int) -> bool:
    prop = await get_property(db, property_id)
    if not prop:
        return False

    await db.delete(prop)
    await db.commit()

    # 清理向量
    try:
        from app.services.vector_service import delete_by_source
        await delete_by_source("property", property_id)
    except Exception:
        pass

    return True
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/property_service.py
git commit -m "feat: add property vectorization hooks for RAG"
```

---

## Summary

| Task | 内容 | 关键产出 |
|------|------|---------|
| 1 | Redis 缓存层 | redis.py + cache_service.py |
| 2 | Embedding 服务 | embedding_service.py (Dashscope) |
| 3 | Milvus 向量库 | milvus.py + vector_service.py |
| 4 | 历史查询工具 | history_tool.py |
| 5 | RAG 检索链 | rag.py + chat_service 集成 |
| 6 | 房源向量化钩子 | property_service 自动向量化 |

**依赖说明：**
- Task 1 可独立运行（只需 Redis）
- Task 2-3 需要 Dashscope embedding 额度
- Task 4 可独立运行
- Task 5-6 依赖 Task 2-3

**测试策略：**
- Task 1, 4 可立即测试
- Task 2, 3, 5, 6 的测试标记为 skip，等额度到位后移除 skip 标记
