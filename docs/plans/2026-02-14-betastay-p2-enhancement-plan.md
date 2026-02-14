# BetaStay P2: 增强迭代 - RAG + 缓存 + 工具补全 Implementation Plan

> **For Claude:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成设计文档第四阶段（增强迭代）：接入向量数据库实现RAG检索增强、启用Redis缓存、补全缺失的LangChain工具、实现JWT认证鉴权。

**Architecture:**
- RAG层：使用Milvus存储房源描述和历史对话的向量表示，通过Dashscope text-embedding-v4生成embedding，检索相关上下文注入到LLM prompt中
- 缓存层：Redis缓存热点房源数据和会话状态
- 工具层：补全history_query工具，让AI能查询定价历史和反馈记录
- 认证层：JWT Token认证，为后续多租户预留结构

**Tech Stack:**
- Vector DB: Milvus 2.x (pymilvus)
- Embedding: Dashscope text-embedding-v4
- Cache: Redis 7+ (aioredis)
- Auth: python-jose (JWT)

**环境变量（已配置）：**
- `DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4`
- `REDIS_URL` 已配置

**注意：** text-embedding-v4 暂无额度，RAG相关任务先搭建代码骨架，embedding调用部分用mock或跳过测试。

---

## 文件结构规划

```
backend/app/
├── core/
│   ├── config.py          # 修改：添加 DASHSCOPE_EMBEDDING_MODEL, MILVUS_* 配置
│   ├── redis.py           # 新建：Redis连接池和工具函数
│   └── auth.py            # 新建：JWT认证逻辑
├── rag/
│   ├── __init__.py        # 新建
│   ├── embeddings.py      # 新建：Dashscope embedding封装
│   ├── milvus_client.py   # 新建：Milvus连接和操作
│   └── retriever.py       # 新建：RAG检索器
├── tools/
│   └── history_tool.py    # 新建：历史查询工具
├── services/
│   └── cache_service.py   # 新建：Redis缓存服务
└── agent/
    ├── betastay_agent.py  # 修改：注册history_query工具
    └── prompts.py         # 修改：更新工具列表说明
```

---

## Chunk 1: Redis 缓存层

### Task 1: Redis 连接模块

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/core/redis.py`
- Test: `backend/tests/test_redis.py`

- [ ] **Step 1: 更新 config.py 添加 Redis 配置读取**

在 `Settings` 类中确认 `REDIS_URL` 已正确读取（当前已有）。

- [ ] **Step 2: 创建 Redis 连接模块**

```python
# backend/app/core/redis.py
import redis.asyncio as aioredis
from app.core.config import settings

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取 Redis 连接（单例模式）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis():
    """关闭 Redis 连接"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None
```

- [ ] **Step 3: 写测试**

```python
# backend/tests/test_redis.py
import pytest


@pytest.mark.asyncio
async def test_redis_connection():
    from app.core.redis import get_redis, close_redis

    redis = await get_redis()
    await redis.set("test_key", "test_value")
    value = await redis.get("test_key")
    assert value == "test_value"
    await redis.delete("test_key")
    await close_redis()
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && python -m pytest tests/test_redis.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/redis.py backend/tests/test_redis.py
git commit -m "feat: add Redis connection module"
```

---

### Task 2: 缓存服务层

**Files:**
- Create: `backend/app/services/cache_service.py`
- Test: `backend/tests/test_cache_service.py`

- [ ] **Step 1: 创建缓存服务**

```python
# backend/app/services/cache_service.py
import json
from app.core.redis import get_redis

# 缓存过期时间（秒）
PROPERTY_CACHE_TTL = 3600  # 1小时
SESSION_CACHE_TTL = 1800   # 30分钟


async def cache_property(property_id: int, data: dict) -> None:
    """缓存房源数据"""
    redis = await get_redis()
    key = f"property:{property_id}"
    await redis.setex(key, PROPERTY_CACHE_TTL, json.dumps(data, ensure_ascii=False))


async def get_cached_property(property_id: int) -> dict | None:
    """获取缓存的房源数据"""
    redis = await get_redis()
    key = f"property:{property_id}"
    data = await redis.get(key)
    return json.loads(data) if data else None


async def invalidate_property_cache(property_id: int) -> None:
    """使房源缓存失效"""
    redis = await get_redis()
    key = f"property:{property_id}"
    await redis.delete(key)


async def cache_session_context(conversation_id: str, messages: list) -> None:
    """缓存会话上下文（最近N轮对话）"""
    redis = await get_redis()
    key = f"session:{conversation_id}"
    await redis.setex(key, SESSION_CACHE_TTL, json.dumps(messages, ensure_ascii=False))


async def get_cached_session_context(conversation_id: str) -> list | None:
    """获取缓存的会话上下文"""
    redis = await get_redis()
    key = f"session:{conversation_id}"
    data = await redis.get(key)
    return json.loads(data) if data else None
```

- [ ] **Step 2: 写测试**

```python
# backend/tests/test_cache_service.py
import pytest
from app.services import cache_service
from app.core.redis import close_redis


@pytest.mark.asyncio
async def test_property_cache():
    prop_data = {"id": 999, "name": "测试房源", "address": "测试地址"}
    await cache_service.cache_property(999, prop_data)
    cached = await cache_service.get_cached_property(999)
    assert cached["name"] == "测试房源"
    await cache_service.invalidate_property_cache(999)
    assert await cache_service.get_cached_property(999) is None
    await close_redis()


@pytest.mark.asyncio
async def test_session_cache():
    messages = [{"role": "user", "content": "你好"}]
    await cache_service.cache_session_context("test-conv-id", messages)
    cached = await cache_service.get_cached_session_context("test-conv-id")
    assert len(cached) == 1
    assert cached[0]["content"] == "你好"
    await close_redis()
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_cache_service.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/cache_service.py backend/tests/test_cache_service.py
git commit -m "feat: add cache service for property and session data"
```

---

### Task 3: 集成缓存到 property_query 工具

**Files:**
- Modify: `backend/app/tools/property_tool.py`

- [ ] **Step 1: 修改 property_query 添加缓存逻辑**

在 `property_query` 函数中：
1. 查询单个房源时，先检查缓存
2. 缓存未命中则查DB，查到后写入缓存
3. 返回数据

```python
# 在 property_query 函数开头添加缓存检查
from app.services.cache_service import get_cached_property, cache_property

# 查询单个房源时
if property_id:
    # 先查缓存
    cached = await get_cached_property(property_id)
    if cached:
        return {"success": True, "property": cached, "from_cache": True}

    # 缓存未命中，查DB
    # ... 原有DB查询逻辑 ...

    # 查到后写入缓存
    if prop:
        prop_dict = { ... }  # 构造dict
        await cache_property(property_id, prop_dict)
        return {"success": True, "property": prop_dict}
```

- [ ] **Step 2: 运行现有测试确保不破坏功能**

Run: `cd backend && python -m pytest tests/test_tools.py tests/test_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/app/tools/property_tool.py
git commit -m "feat: integrate Redis cache into property_query tool"
```

---

## Chunk 2: 历史查询工具

### Task 4: history_query 工具

**Files:**
- Create: `backend/app/tools/history_tool.py`
- Modify: `backend/app/agent/betastay_agent.py`
- Modify: `backend/app/agent/prompts.py`
- Test: `backend/tests/test_tools.py`

- [ ] **Step 1: 创建历史查询工具**

```python
# backend/app/tools/history_tool.py
from datetime import datetime, timedelta
from langchain_core.tools import tool
from sqlalchemy import select
from app.tools.context import get_db_session
from app.models.pricing import PricingRecord
from app.models.feedback import Feedback


@tool
async def history_query(
    property_id: int,
    days: int = 30,
    include_feedback: bool = True,
) -> dict:
    """查询指定房源的定价历史和反馈记录。

    Args:
        property_id: 房源ID
        days: 查询最近多少天的记录，默认30天
        include_feedback: 是否包含反馈记录，默认True

    Returns:
        定价历史列表和反馈统计
    """
    db = get_db_session()
    cutoff = datetime.utcnow() - timedelta(days=days)

    # 查询定价记录
    pricing_result = await db.execute(
        select(PricingRecord)
        .where(PricingRecord.property_id == property_id)
        .where(PricingRecord.created_at >= cutoff)
        .order_by(PricingRecord.created_at.desc())
    )
    pricing_records = pricing_result.scalars().all()

    pricing_list = [
        {
            "id": r.id,
            "target_date": r.target_date.isoformat(),
            "conservative_price": float(r.conservative_price),
            "suggested_price": float(r.suggested_price),
            "aggressive_price": float(r.aggressive_price),
            "created_at": r.created_at.isoformat(),
        }
        for r in pricing_records
    ]

    result = {
        "success": True,
        "property_id": property_id,
        "days": days,
        "pricing_count": len(pricing_list),
        "pricing_records": pricing_list,
    }

    if include_feedback and pricing_list:
        pricing_ids = [r.id for r in pricing_records]
        fb_result = await db.execute(
            select(Feedback).where(Feedback.pricing_record_id.in_(pricing_ids))
        )
        feedbacks = fb_result.scalars().all()

        # 统计反馈
        fb_stats = {"adopted": 0, "rejected": 0, "adjusted": 0}
        for fb in feedbacks:
            if fb.feedback_type in fb_stats:
                fb_stats[fb.feedback_type] += 1

        result["feedback_stats"] = fb_stats
        result["feedback_count"] = len(feedbacks)

    return result


history_query_tool = history_query
```

- [ ] **Step 2: 注册到 agent**

修改 `backend/app/agent/betastay_agent.py`：

```python
from app.tools.history_tool import history_query_tool

def get_tools():
    return [
        # ... 现有工具 ...
        history_query_tool,
    ]
```

- [ ] **Step 3: 更新 prompts.py 工具说明**

在 `SYSTEM_PROMPT` 的可用工具列表中添加：

```
- history_query: 查询定价历史和反馈记录
- get_current_time: 获取当前日期时间
```

- [ ] **Step 4: 添加测试**

在 `backend/tests/test_tools.py` 中添加：

```python
def test_history_tool_schema():
    from app.tools.history_tool import history_query_tool
    assert history_query_tool.name == "history_query"
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && python -m pytest tests/test_tools.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/tools/history_tool.py backend/app/agent/betastay_agent.py backend/app/agent/prompts.py backend/tests/test_tools.py
git commit -m "feat: add history_query tool for pricing history and feedback"
```

---

## Chunk 3: RAG 基础设施（骨架）

### Task 5: Embedding 服务

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/rag/__init__.py`
- Create: `backend/app/rag/embeddings.py`
- Test: `backend/tests/test_embeddings.py`

- [ ] **Step 1: 更新 config.py**

```python
# 在 Settings 类中添加
DASHSCOPE_EMBEDDING_MODEL: str = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
```

- [ ] **Step 2: 创建 embedding 服务**

```python
# backend/app/rag/embeddings.py
import dashscope
from dashscope import TextEmbedding
from app.core.config import settings


async def get_embedding(text: str) -> list[float]:
    """获取文本的向量表示"""
    dashscope.api_key = settings.DASHSCOPE_API_KEY

    response = TextEmbedding.call(
        model=settings.DASHSCOPE_EMBEDDING_MODEL,
        input=text,
    )

    if response.status_code != 200:
        raise Exception(f"Embedding API error: {response.message}")

    return response.output["embeddings"][0]["embedding"]


async def get_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """批量获取文本向量"""
    dashscope.api_key = settings.DASHSCOPE_API_KEY

    response = TextEmbedding.call(
        model=settings.DASHSCOPE_EMBEDDING_MODEL,
        input=texts,
    )

    if response.status_code != 200:
        raise Exception(f"Embedding API error: {response.message}")

    return [item["embedding"] for item in response.output["embeddings"]]
```

- [ ] **Step 3: 创建 __init__.py**

```python
# backend/app/rag/__init__.py
```

- [ ] **Step 4: 写测试（标记为skip，等额度）**

```python
# backend/tests/test_embeddings.py
import pytest


@pytest.mark.skip(reason="text-embedding-v4 暂无额度")
@pytest.mark.asyncio
async def test_get_embedding():
    from app.rag.embeddings import get_embedding

    embedding = await get_embedding("测试文本")
    assert isinstance(embedding, list)
    assert len(embedding) > 0
    assert all(isinstance(x, float) for x in embedding)
```

- [ ] **Step 5: 验证模块可导入**

Run: `cd backend && python -c "from app.rag.embeddings import get_embedding; print('OK')"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/rag/ backend/tests/test_embeddings.py
git commit -m "feat: add Dashscope embedding service (skeleton)"
```

---

### Task 6: Milvus 客户端（骨架）

**Files:**
- Create: `backend/app/rag/milvus_client.py`
- Update: `backend/requirements.txt`

- [ ] **Step 1: 添加 pymilvus 依赖**

在 `requirements.txt` 添加：

```
# Vector database
pymilvus>=2.4.0
```

- [ ] **Step 2: 创建 Milvus 客户端**

```python
# backend/app/rag/milvus_client.py
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from app.core.config import settings

COLLECTION_NAME = "betastay_docs"
EMBEDDING_DIM = 1536  # text-embedding-v4 维度


def connect_milvus():
    """连接 Milvus"""
    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT,
    )


def disconnect_milvus():
    """断开 Milvus 连接"""
    connections.disconnect("default")


def create_collection_if_not_exists():
    """创建集合（如果不存在）"""
    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=50),  # property/conversation
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=100),   # 原始文档ID
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
    ]
    schema = CollectionSchema(fields, description="BetaStay RAG documents")
    collection = Collection(COLLECTION_NAME, schema)

    # 创建索引
    index_params = {
        "metric_type": "COSINE",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 128},
    }
    collection.create_index("embedding", index_params)

    return collection


async def insert_document(doc_type: str, doc_id: str, content: str, embedding: list[float]):
    """插入文档"""
    collection = Collection(COLLECTION_NAME)
    collection.insert([
        [doc_type],
        [doc_id],
        [content],
        [embedding],
    ])
    collection.flush()


async def search_similar(query_embedding: list[float], top_k: int = 5, doc_type: str | None = None) -> list[dict]:
    """搜索相似文档"""
    collection = Collection(COLLECTION_NAME)
    collection.load()

    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    expr = f'doc_type == "{doc_type}"' if doc_type else None

    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        expr=expr,
        output_fields=["doc_type", "doc_id", "content"],
    )

    return [
        {
            "doc_type": hit.entity.get("doc_type"),
            "doc_id": hit.entity.get("doc_id"),
            "content": hit.entity.get("content"),
            "score": hit.score,
        }
        for hit in results[0]
    ]
```

- [ ] **Step 3: 验证模块可导入**

Run: `cd backend && python -c "from app.rag.milvus_client import COLLECTION_NAME; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/rag/milvus_client.py backend/requirements.txt
git commit -m "feat: add Milvus client for vector storage (skeleton)"
```

---

### Task 7: RAG 检索器

**Files:**
- Create: `backend/app/rag/retriever.py`

- [ ] **Step 1: 创建检索器**

```python
# backend/app/rag/retriever.py
from app.rag.embeddings import get_embedding
from app.rag.milvus_client import search_similar, connect_milvus, disconnect_milvus


class RAGRetriever:
    """RAG 检索器 - 根据查询检索相关上下文"""

    def __init__(self):
        self._connected = False

    async def connect(self):
        if not self._connected:
            connect_milvus()
            self._connected = True

    async def disconnect(self):
        if self._connected:
            disconnect_milvus()
            self._connected = False

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        doc_type: str | None = None,
    ) -> list[dict]:
        """检索与查询相关的文档

        Args:
            query: 查询文本
            top_k: 返回最相似的K个文档
            doc_type: 限定文档类型（property/conversation）

        Returns:
            相关文档列表，包含 content 和 score
        """
        await self.connect()
        query_embedding = await get_embedding(query)
        results = await search_similar(query_embedding, top_k, doc_type)
        return results

    async def retrieve_context_for_prompt(
        self,
        query: str,
        max_tokens: int = 2000,
    ) -> str:
        """检索并格式化为可注入 prompt 的上下文

        Args:
            query: 用户查询
            max_tokens: 上下文最大token数（粗略估计）

        Returns:
            格式化的上下文字符串
        """
        results = await self.retrieve(query, top_k=5)

        if not results:
            return ""

        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 2  # 粗略估计：1 token ≈ 2 中文字符

        for doc in results:
            content = doc["content"]
            if total_chars + len(content) > max_chars:
                break
            context_parts.append(f"[相关信息] {content}")
            total_chars += len(content)

        return "\n\n".join(context_parts)


# 全局单例
_retriever: RAGRetriever | None = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever
```

- [ ] **Step 2: 验证模块可导入**

Run: `cd backend && python -c "from app.rag.retriever import get_retriever; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/rag/retriever.py
git commit -m "feat: add RAG retriever for context injection"
```

---

## Chunk 4: JWT 认证（预留）

### Task 8: JWT 认证模块

**Files:**
- Create: `backend/app/core/auth.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 创建认证模块**

```python
# backend/app/core/auth.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

security = HTTPBearer(auto_error=False)

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """解码 JWT Token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """获取当前用户（可选认证）

    MVP阶段：认证可选，返回None表示匿名用户
    后续多租户阶段：改为强制认证
    """
    if credentials is None:
        return None  # 匿名用户

    token = credentials.credentials
    payload = decode_token(token)
    return payload


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """强制认证（用于需要登录的接口）"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials
    return decode_token(token)
```

- [ ] **Step 2: 写测试**

```python
# backend/tests/test_auth.py
import pytest
from app.core.auth import create_access_token, decode_token


def test_create_and_decode_token():
    data = {"user_id": "test-user-123", "role": "landlord"}
    token = create_access_token(data)

    decoded = decode_token(token)
    assert decoded["user_id"] == "test-user-123"
    assert decoded["role"] == "landlord"
    assert "exp" in decoded


def test_invalid_token():
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        decode_token("invalid-token")
    assert exc_info.value.status_code == 401
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python -m pytest tests/test_auth.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/app/core/auth.py backend/tests/test_auth.py
git commit -m "feat: add JWT authentication module (optional auth for MVP)"
```

---

## Summary

| Task | 内容 | 关键产出 |
|------|------|---------|
| 1 | Redis 连接模块 | `core/redis.py` |
| 2 | 缓存服务层 | `services/cache_service.py` |
| 3 | 集成缓存到工具 | property_query 缓存优化 |
| 4 | 历史查询工具 | `tools/history_tool.py` |
| 5 | Embedding 服务 | `rag/embeddings.py` |
| 6 | Milvus 客户端 | `rag/milvus_client.py` |
| 7 | RAG 检索器 | `rag/retriever.py` |
| 8 | JWT 认证 | `core/auth.py` |

**后续工作（RAG 额度到位后）：**
- 在 chat_service 中集成 RAG 检索，将相关上下文注入 prompt
- 房源创建/更新时自动向量化存入 Milvus
- 对话结束时向量化存储历史对话
