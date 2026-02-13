# BetaStay MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 跑通最小闭环——房源录入（含Excel上传）→ 获取定价建议 → 记录反馈

**Architecture:** LLM(Dashscope)作为智能调度层，通过LangChain Agent调用工具层完成操作。定价规则引擎作为工具被调用，所有写操作需用户确认。前端uni-app移动端优先，仪表盘+对话交互。

**Tech Stack:**
- Backend: Python 3.14, FastAPI, SQLAlchemy 2.0, Alembic
- AI: LangChain 1.2.x, LangGraph, langchain-community (ChatTongyi/Dashscope)
- Database: PostgreSQL 15+, Redis 7+
- Frontend: Vue3 + uni-app + Pinia
- Excel: pandas + openpyxl + xlrd

---

## Task 1: Backend Project Scaffolding

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/router.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/tools/__init__.py`
- Create: `backend/app/engine/__init__.py`
- Create: `backend/app/agent/__init__.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`

**Step 1: Create requirements.txt**

```txt
# Web framework
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
python-multipart>=0.0.18

# Database
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.30.0
alembic>=1.14.0
redis>=5.0.0

# AI
langchain>=1.2.0
langchain-core>=1.2.0
langchain-community>=0.4.0
langgraph>=1.0.0
langgraph-checkpoint-postgres>=1.0.0
dashscope>=1.20.0

# Excel parsing
pandas>=2.2.0
openpyxl>=3.1.0
xlrd>=2.0.0

# Utilities
pydantic>=2.10.0
pydantic-settings>=2.7.0
python-jose[cryptography]>=3.3.0
python-dotenv>=1.0.0
httpx>=0.28.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
pytest-cov>=6.0.0
httpx>=0.28.0
```

**Step 2: Create core config**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BetaStay"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/betastay"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/betastay"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Dashscope
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_MODEL: str = "qwen-max"

    # JWT
    SECRET_KEY: str = "betastay-secret-key-change-in-production"
    ALGORITHM: str = "HS256"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

**Step 3: Create FastAPI main app**

```python
# backend/app/main.py
from fastapi import FastAPI
from app.core.config import settings
from app.api.router import api_router


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
```

```python
# backend/app/api/router.py
from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
```

**Step 4: Create .env.example**

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/betastay
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/betastay
REDIS_URL=redis://localhost:6379/0
DASHSCOPE_API_KEY=your-dashscope-api-key
DASHSCOPE_MODEL=qwen-max
SECRET_KEY=change-this-in-production
```

**Step 5: Create test conftest**

```python
# backend/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

**Step 6: Write smoke test**

```python
# backend/tests/test_health.py
import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "BetaStay"
```

**Step 7: Run test to verify**

Run: `cd backend && python -m pytest tests/test_health.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project with FastAPI"
```

---

## Task 2: Database Models & Migration Setup

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/property.py`
- Create: `backend/app/models/pricing.py`
- Create: `backend/app/models/feedback.py`
- Create: `backend/app/models/transaction.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Test: `backend/tests/test_models.py`

**Step 1: Create database connection module**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 2: Create property model**

```python
# backend/app/models/property.py
from sqlalchemy import String, Float, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class Property(Base):
    __tablename__ = "property"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="房源名称")
    address: Mapped[str] = mapped_column(String(500), nullable=False, comment="地址")
    room_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="房型")
    area: Mapped[float] = mapped_column(Float, nullable=False, comment="面积(平方米)")
    facilities: Mapped[dict] = mapped_column(JSON, default=dict, comment="设施配置")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="房源描述")

    # 房东偏好
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="最低可接受价")
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="最高价格")
    expected_return_rate: Mapped[float | None] = mapped_column(Float, nullable=True, comment="期望收益率")
    vacancy_tolerance: Mapped[float | None] = mapped_column(Float, nullable=True, comment="空置容忍度(0-1)")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Step 3: Create pricing record model**

```python
# backend/app/models/pricing.py
from sqlalchemy import Integer, Float, DateTime, JSON, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from app.core.database import Base


class PricingRecord(Base):
    __tablename__ = "pricing_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("property.id"), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False, comment="目标日期")
    conservative_price: Mapped[float] = mapped_column(Float, nullable=False, comment="保守价")
    suggested_price: Mapped[float] = mapped_column(Float, nullable=False, comment="建议价")
    aggressive_price: Mapped[float] = mapped_column(Float, nullable=False, comment="激进价")
    calculation_details: Mapped[dict] = mapped_column(JSON, default=dict, comment="计算依据明细")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 4: Create feedback model**

```python
# backend/app/models/feedback.py
from sqlalchemy import Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pricing_record_id: Mapped[int] = mapped_column(Integer, ForeignKey("pricing_record.id"), nullable=False)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="采纳/拒绝/调整")
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True, comment="实际采用价格")
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="用户备注")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 5: Create transaction model**

```python
# backend/app/models/transaction.py
from sqlalchemy import Integer, Float, String, DateTime, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from app.core.database import Base


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    property_id: Mapped[int] = mapped_column(Integer, ForeignKey("property.id"), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False, comment="入住日期")
    actual_price: Mapped[float] = mapped_column(Float, nullable=False, comment="实际成交价")
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="来源平台")
    advance_days: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="提前预订天数")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 6: Create conversation & message models**

```python
# backend/app/models/conversation.py
from sqlalchemy import Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.core.database import Base


class Conversation(Base):
    __tablename__ = "conversation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="会话标题")
    status: Mapped[str] = mapped_column(String(20), default="active", comment="active/archived")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey("conversation.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="user/assistant/system/tool")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="工具调用记录")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 7: Update models __init__.py to export all models**

```python
# backend/app/models/__init__.py
from app.models.property import Property
from app.models.pricing import PricingRecord
from app.models.feedback import Feedback
from app.models.transaction import Transaction
from app.models.conversation import Conversation, Message

__all__ = [
    "Property",
    "PricingRecord",
    "Feedback",
    "Transaction",
    "Conversation",
    "Message",
]
```

**Step 8: Initialize Alembic**

Run: `cd backend && alembic init alembic`

Then modify `alembic/env.py` to use async engine and import models:

```python
# Key changes in backend/alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

from app.core.config import settings
from app.core.database import Base
from app.models import *  # noqa: F401, F403 - import all models for autogenerate

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = settings.DATABASE_URL
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

**Step 9: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial tables"`

**Step 10: Write model test**

```python
# backend/tests/test_models.py
from app.models.property import Property
from app.models.pricing import PricingRecord
from app.models.feedback import Feedback
from app.models.transaction import Transaction
from app.models.conversation import Conversation, Message


def test_property_model_fields():
    p = Property(
        name="测试民宿",
        address="杭州市西湖区",
        room_type="整套",
        area=80.0,
        facilities={"wifi": True, "ac": True},
        min_price=200.0,
        max_price=800.0,
    )
    assert p.name == "测试民宿"
    assert p.facilities["wifi"] is True
    assert p.min_price == 200.0


def test_pricing_record_model_fields():
    from datetime import date
    pr = PricingRecord(
        property_id=1,
        target_date=date(2026, 5, 1),
        conservative_price=300.0,
        suggested_price=400.0,
        aggressive_price=500.0,
        calculation_details={"weight_owner_pref": 0.35},
    )
    assert pr.suggested_price == 400.0
    assert pr.calculation_details["weight_owner_pref"] == 0.35


def test_feedback_model_fields():
    f = Feedback(
        pricing_record_id=1,
        feedback_type="adopted",
        actual_price=380.0,
        note="价格合理",
    )
    assert f.feedback_type == "adopted"


def test_conversation_and_message_fields():
    c = Conversation(title="定价咨询")
    assert c.title == "定价咨询"

    m = Message(
        conversation_id=1,
        role="user",
        content="帮我看看明天的建议价",
    )
    assert m.role == "user"
```

**Step 11: Run tests**

Run: `cd backend && python -m pytest tests/test_models.py -v`
Expected: PASS

**Step 12: Commit**

```bash
git add backend/
git commit -m "feat: add database models and Alembic migration setup"
```

---

## Task 3: Property CRUD API

**Files:**
- Create: `backend/app/api/property.py`
- Create: `backend/app/services/property_service.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_property_api.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_property_api.py
import pytest


@pytest.mark.asyncio
async def test_create_property(client):
    payload = {
        "name": "西湖美宿",
        "address": "杭州市西湖区北山路100号",
        "room_type": "整套",
        "area": 85.5,
        "facilities": {"wifi": True, "ac": True, "parking": False},
        "min_price": 300.0,
        "max_price": 1000.0,
        "expected_return_rate": 0.15,
        "vacancy_tolerance": 0.2,
    }
    response = await client.post("/api/v1/property", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "西湖美宿"
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_get_property(client):
    # Create first
    payload = {
        "name": "测试房源",
        "address": "测试地址",
        "room_type": "单间",
        "area": 30.0,
    }
    create_resp = await client.post("/api/v1/property", json=payload)
    property_id = create_resp.json()["id"]

    # Fetch
    response = await client.get(f"/api/v1/property/{property_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "测试房源"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_property_api.py -v`
Expected: FAIL (404 - route not found)

**Step 3: Create property service**

```python
# backend/app/services/property_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.property import Property


async def create_property(db: AsyncSession, data: dict) -> Property:
    prop = Property(**data)
    db.add(prop)
    await db.commit()
    await db.refresh(prop)
    return prop


async def get_property(db: AsyncSession, property_id: int) -> Property | None:
    result = await db.execute(select(Property).where(Property.id == property_id))
    return result.scalar_one_or_none()


async def list_properties(db: AsyncSession) -> list[Property]:
    result = await db.execute(select(Property).order_by(Property.created_at.desc()))
    return list(result.scalars().all())
```

**Step 4: Create property API route**

```python
# backend/app/api/property.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services import property_service

router = APIRouter(prefix="/property", tags=["property"])


class PropertyCreate(BaseModel):
    name: str
    address: str
    room_type: str
    area: float
    facilities: dict = {}
    description: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    expected_return_rate: float | None = None
    vacancy_tolerance: float | None = None


class PropertyResponse(BaseModel):
    id: int
    name: str
    address: str
    room_type: str
    area: float
    facilities: dict
    description: str | None
    min_price: float | None
    max_price: float | None
    expected_return_rate: float | None
    vacancy_tolerance: float | None

    model_config = {"from_attributes": True}


@router.post("", response_model=PropertyResponse)
async def create_property(data: PropertyCreate, db: AsyncSession = Depends(get_db)):
    prop = await property_service.create_property(db, data.model_dump())
    return prop


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(property_id: int, db: AsyncSession = Depends(get_db)):
    prop = await property_service.get_property(db, property_id)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.get("", response_model=list[PropertyResponse])
async def list_properties(db: AsyncSession = Depends(get_db)):
    return await property_service.list_properties(db)
```

**Step 5: Register route in router**

```python
# backend/app/api/router.py
from fastapi import APIRouter
from app.api.property import router as property_router

api_router = APIRouter()
api_router.include_router(property_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
```

**Step 6: Update test conftest for database**

需要为测试创建内存SQLite或测试数据库的fixture，覆盖`get_db`依赖：

```python
# backend/tests/conftest.py
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

添加测试依赖到 requirements.txt:

```
aiosqlite>=0.20.0
```

**Step 7: Run tests**

Run: `cd backend && python -m pytest tests/test_property_api.py -v`
Expected: PASS

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: add property CRUD API with service layer"
```

---

## Task 4: Excel Upload & Parsing Tool

**Files:**
- Create: `backend/app/tools/excel_parser.py`
- Create: `backend/app/api/upload.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_excel_parser.py`
- Test: `backend/tests/fixtures/test_property.xlsx` (测试用Excel文件)

**Step 1: Write the failing test**

```python
# backend/tests/test_excel_parser.py
import pytest
import pandas as pd
import os
from io import BytesIO


def create_test_excel(path: str):
    """创建测试用Excel文件"""
    df = pd.DataFrame({
        "房源名称": ["湖景房A", "山景房B", "  花园房C  "],
        "地址": ["杭州西湖区1号", "杭州西湖区2号", "杭州西湖区3号"],
        "房型": ["整套", "单间", "整套"],
        "面积": [80.0, 35.5, 120.0],
        "最低价": [300, 150, 500],
        "最高价": [800, 400, 1200],
    })
    # 添加一行空行和一行重复行来测试清洗
    empty_row = pd.DataFrame({col: [None] for col in df.columns})
    duplicate_row = df.iloc[[0]]
    df = pd.concat([df, empty_row, duplicate_row], ignore_index=True)
    df.to_excel(path, index=False)


def test_parse_excel_basic():
    from app.tools.excel_parser import parse_excel

    path = "tests/fixtures/test_property.xlsx"
    os.makedirs("tests/fixtures", exist_ok=True)
    create_test_excel(path)

    result = parse_excel(path)
    assert result["success"] is True
    assert result["total_rows"] == 3  # 去重去空后
    assert len(result["data"]) == 3
    assert result["data"][0]["房源名称"] == "湖景房A"
    assert result["data"][2]["房源名称"] == "花园房C"  # 去除首尾空格


def test_parse_excel_bytes():
    from app.tools.excel_parser import parse_excel_bytes

    df = pd.DataFrame({
        "房源名称": ["测试房源"],
        "地址": ["测试地址"],
        "房型": ["整套"],
        "面积": [50.0],
    })
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    result = parse_excel_bytes(buffer.read(), "test.xlsx")
    assert result["success"] is True
    assert result["total_rows"] == 1


def test_parse_excel_invalid_file():
    from app.tools.excel_parser import parse_excel_bytes

    result = parse_excel_bytes(b"not an excel file", "bad.xlsx")
    assert result["success"] is False
    assert "error" in result
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_excel_parser.py -v`
Expected: FAIL (import error)

**Step 3: Implement Excel parser tool**

```python
# backend/app/tools/excel_parser.py
import pandas as pd
from io import BytesIO


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清洗DataFrame：去空行、去重、去首尾空格、标准化列名"""
    # 去除全空行
    df = df.dropna(how="all")

    # 字符串列去首尾空格
    string_cols = df.select_dtypes(include=["object"]).columns
    for col in string_cols:
        df[col] = df[col].str.strip()

    # 去重
    df = df.drop_duplicates()

    # 重置索引
    df = df.reset_index(drop=True)

    return df


def _get_stats(df: pd.DataFrame) -> dict:
    """生成数据统计摘要"""
    stats = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }
    # 数值列统计
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        stats[f"{col}_min"] = float(df[col].min()) if not df[col].isnull().all() else None
        stats[f"{col}_max"] = float(df[col].max()) if not df[col].isnull().all() else None
        stats[f"{col}_mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
    return stats


def parse_excel(file_path: str, sheet_name: str | int | None = 0) -> dict:
    """解析Excel文件路径"""
    try:
        engine = "xlrd" if file_path.endswith(".xls") else "openpyxl"
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
        df = _clean_dataframe(df)
        return {
            "success": True,
            "total_rows": len(df),
            "stats": _get_stats(df),
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_excel_bytes(content: bytes, filename: str, sheet_name: str | int | None = 0) -> dict:
    """解析Excel字节内容（用于文件上传场景）"""
    try:
        buffer = BytesIO(content)
        engine = "xlrd" if filename.endswith(".xls") else "openpyxl"
        df = pd.read_excel(buffer, sheet_name=sheet_name, engine=engine)
        df = _clean_dataframe(df)
        return {
            "success": True,
            "filename": filename,
            "total_rows": len(df),
            "stats": _get_stats(df),
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_excel_parser.py -v`
Expected: PASS

**Step 5: Create upload API endpoint**

```python
# backend/app/api/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.tools.excel_parser import parse_excel_bytes

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post("/excel")
async def upload_excel(file: UploadFile = File(...)):
    """上传并解析Excel文件，返回结构化数据（待确认）"""
    filename = file.filename or ""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"仅支持 {', '.join(ALLOWED_EXTENSIONS)} 格式")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大支持10MB")

    result = parse_excel_bytes(content, filename)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=f"解析失败: {result['error']}")

    # 标记为待确认，前端需展示确认弹窗
    result["pending_confirmation"] = True
    return result
```

**Step 6: Register upload route**

```python
# backend/app/api/router.py (更新)
from fastapi import APIRouter
from app.api.property import router as property_router
from app.api.upload import router as upload_router

api_router = APIRouter()
api_router.include_router(property_router)
api_router.include_router(upload_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
```

**Step 7: Write upload API test**

```python
# backend/tests/test_upload_api.py
import pytest
import pandas as pd
from io import BytesIO


@pytest.mark.asyncio
async def test_upload_excel(client):
    df = pd.DataFrame({
        "房源名称": ["测试民宿"],
        "地址": ["杭州"],
        "房型": ["整套"],
        "面积": [60.0],
    })
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)

    response = await client.post(
        "/api/v1/upload/excel",
        files={"file": ("test.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["total_rows"] == 1
    assert data["pending_confirmation"] is True


@pytest.mark.asyncio
async def test_upload_invalid_format(client):
    response = await client.post(
        "/api/v1/upload/excel",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
```

**Step 8: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add backend/
git commit -m "feat: add Excel upload parsing tool with data cleaning"
```

---

## Task 5: Pricing Engine (Simplified MVP)

**Files:**
- Create: `backend/app/engine/pricing_engine.py`
- Create: `backend/app/engine/config.py`
- Test: `backend/tests/test_pricing_engine.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_pricing_engine.py
import pytest
from datetime import date


def test_basic_pricing():
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()
    result = engine.calculate(
        base_price=500.0,
        owner_preference={
            "min_price": 300.0,
            "max_price": 800.0,
            "expected_return_rate": 0.15,
            "vacancy_tolerance": 0.2,
        },
        property_info={
            "room_type": "整套",
            "area": 80.0,
            "facilities": {"wifi": True, "ac": True},
        },
        target_date=date(2026, 5, 1),
    )
    assert "conservative_price" in result
    assert "suggested_price" in result
    assert "aggressive_price" in result
    assert "calculation_details" in result
    assert result["conservative_price"] <= result["suggested_price"] <= result["aggressive_price"]
    assert result["conservative_price"] >= 300.0  # 不低于最低价
    assert result["aggressive_price"] <= 800.0  # 不高于最高价


def test_weekend_adjustment():
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()
    # 2026-05-02 是周六
    weekend_result = engine.calculate(
        base_price=500.0,
        owner_preference={"min_price": 200.0, "max_price": 1000.0},
        property_info={"room_type": "整套", "area": 80.0},
        target_date=date(2026, 5, 2),
    )
    # 2026-05-04 是周一
    weekday_result = engine.calculate(
        base_price=500.0,
        owner_preference={"min_price": 200.0, "max_price": 1000.0},
        property_info={"room_type": "整套", "area": 80.0},
        target_date=date(2026, 5, 4),
    )
    assert weekend_result["suggested_price"] > weekday_result["suggested_price"]


def test_price_boundary_enforcement():
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()
    result = engine.calculate(
        base_price=100.0,
        owner_preference={"min_price": 300.0, "max_price": 400.0},
        property_info={"room_type": "单间", "area": 20.0},
        target_date=date(2026, 5, 1),
    )
    # 即使基准价很低，也不低于最低价
    assert result["conservative_price"] >= 300.0
    assert result["aggressive_price"] <= 400.0
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_pricing_engine.py -v`
Expected: FAIL

**Step 3: Create engine config**

```python
# backend/app/engine/config.py

# 因素权重配置
WEIGHTS = {
    "owner_preference": 0.35,
    "historical_performance": 0.25,
    "time_factor": 0.18,
    "market_factor": 0.12,
    "property_base": 0.07,
    "external_event": 0.03,
}

# 时间因素参数
TIME_FACTORS = {
    "weekend_multiplier": 1.15,       # 周末上浮15%
    "weekday_multiplier": 0.95,       # 工作日下调5%
    "holiday_multiplier": 1.30,       # 节假日上浮30%
}

# 三档价格偏移
PRICE_TIERS = {
    "conservative_offset": -0.10,     # 保守价下浮10%
    "aggressive_offset": 0.10,        # 激进价上浮10%
}

# 中国法定节假日 (2026年示例，后续可配置化)
HOLIDAYS_2026 = {
    "元旦": ["2026-01-01", "2026-01-02", "2026-01-03"],
    "春节": ["2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22", "2026-02-23"],
    "清明": ["2026-04-04", "2026-04-05", "2026-04-06"],
    "劳动节": ["2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04", "2026-05-05"],
    "端午": ["2026-06-19", "2026-06-20", "2026-06-21"],
    "中秋+国庆": ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08"],
}
```

**Step 4: Implement pricing engine**

```python
# backend/app/engine/pricing_engine.py
from datetime import date
from app.engine.config import WEIGHTS, TIME_FACTORS, PRICE_TIERS, HOLIDAYS_2026


class PricingEngine:
    """定价规则引擎 - MVP简化版，支持房东偏好+时间因素+基础属性"""

    def __init__(self):
        self.weights = WEIGHTS.copy()
        self._holiday_dates: set[str] = set()
        for dates in HOLIDAYS_2026.values():
            self._holiday_dates.update(dates)

    def calculate(
        self,
        base_price: float,
        owner_preference: dict,
        property_info: dict,
        target_date: date,
        historical_data: dict | None = None,
        market_data: dict | None = None,
        external_events: list[dict] | None = None,
    ) -> dict:
        min_price = owner_preference.get("min_price", 0)
        max_price = owner_preference.get("max_price", float("inf"))

        details = {}

        # 1. 房东偏好调整
        pref_adj = self._calc_owner_preference(base_price, owner_preference)
        details["owner_preference"] = {"adjustment": pref_adj, "weight": self.weights["owner_preference"]}

        # 2. 历史表现调整（MVP阶段：无历史数据则为0）
        hist_adj = self._calc_historical(historical_data) if historical_data else 0.0
        details["historical_performance"] = {"adjustment": hist_adj, "weight": self.weights["historical_performance"]}

        # 3. 时间因素调整
        time_adj = self._calc_time_factor(target_date)
        details["time_factor"] = {"adjustment": time_adj, "weight": self.weights["time_factor"]}

        # 4. 市场因素调整（MVP阶段：预留接口，默认0）
        market_adj = self._calc_market(market_data) if market_data else 0.0
        details["market_factor"] = {"adjustment": market_adj, "weight": self.weights["market_factor"]}

        # 5. 基础属性调整
        base_adj = self._calc_property_base(property_info)
        details["property_base"] = {"adjustment": base_adj, "weight": self.weights["property_base"]}

        # 6. 外部事件调整（MVP阶段：预留接口，默认0）
        ext_adj = self._calc_external(external_events) if external_events else 0.0
        details["external_event"] = {"adjustment": ext_adj, "weight": self.weights["external_event"]}

        # 综合调整系数
        composite = (
            pref_adj * self.weights["owner_preference"]
            + hist_adj * self.weights["historical_performance"]
            + time_adj * self.weights["time_factor"]
            + market_adj * self.weights["market_factor"]
            + base_adj * self.weights["property_base"]
            + ext_adj * self.weights["external_event"]
        )

        suggested = base_price * (1 + composite)
        conservative = suggested * (1 + PRICE_TIERS["conservative_offset"])
        aggressive = suggested * (1 + PRICE_TIERS["aggressive_offset"])

        # 边界约束
        conservative = max(min_price, min(max_price, conservative))
        suggested = max(min_price, min(max_price, suggested))
        aggressive = max(min_price, min(max_price, aggressive))

        # 保持三档排序
        conservative = min(conservative, suggested)
        aggressive = max(aggressive, suggested)

        return {
            "conservative_price": round(conservative, 2),
            "suggested_price": round(suggested, 2),
            "aggressive_price": round(aggressive, 2),
            "base_price": base_price,
            "composite_adjustment": round(composite, 4),
            "calculation_details": details,
        }

    def _calc_owner_preference(self, base_price: float, pref: dict) -> float:
        """根据房东偏好计算调整系数"""
        adj = 0.0
        expected_rate = pref.get("expected_return_rate", 0)
        if expected_rate > 0:
            adj += expected_rate * 0.5  # 期望收益率部分转化为价格上浮

        vacancy_tol = pref.get("vacancy_tolerance", 0.5)
        # 空置容忍度低 → 价格趋向保守（下调）
        # 空置容忍度高 → 价格可以激进（上调）
        adj += (vacancy_tol - 0.5) * 0.2

        return adj

    def _calc_historical(self, data: dict) -> float:
        """根据历史表现计算调整系数（MVP预留）"""
        return 0.0

    def _calc_time_factor(self, target_date: date) -> float:
        """根据日期计算时间因素调整系数"""
        date_str = target_date.isoformat()

        # 节假日
        if date_str in self._holiday_dates:
            return TIME_FACTORS["holiday_multiplier"] - 1.0

        # 周末 (5=Saturday, 6=Sunday)
        if target_date.weekday() >= 5:
            return TIME_FACTORS["weekend_multiplier"] - 1.0

        # 工作日
        return TIME_FACTORS["weekday_multiplier"] - 1.0

    def _calc_market(self, data: dict) -> float:
        """市场因素调整（MVP预留）"""
        return 0.0

    def _calc_property_base(self, info: dict) -> float:
        """根据房源基础属性计算调整系数"""
        adj = 0.0
        # 整套 vs 单间
        if info.get("room_type") == "整套":
            adj += 0.05
        # 面积因素
        area = info.get("area", 50)
        if area > 100:
            adj += 0.03
        elif area < 30:
            adj -= 0.03
        return adj

    def _calc_external(self, events: list[dict]) -> float:
        """外部事件调整（MVP预留）"""
        return 0.0
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_pricing_engine.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: implement pricing engine with weighted factors"
```

---

## Task 6: LangChain Tools (Wrapping Services)

**Files:**
- Create: `backend/app/tools/property_tool.py`
- Create: `backend/app/tools/pricing_tool.py`
- Create: `backend/app/tools/feedback_tool.py`
- Create: `backend/app/tools/excel_tool.py`
- Test: `backend/tests/test_tools.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_tools.py
def test_property_tool_schema():
    from app.tools.property_tool import property_create_tool, property_query_tool
    assert property_create_tool.name == "property_create"
    assert property_query_tool.name == "property_query"


def test_pricing_tool_schema():
    from app.tools.pricing_tool import pricing_calculate_tool
    assert pricing_calculate_tool.name == "pricing_calculate"


def test_feedback_tool_schema():
    from app.tools.feedback_tool import feedback_record_tool
    assert feedback_record_tool.name == "feedback_record"


def test_excel_tool_schema():
    from app.tools.excel_tool import excel_parse_tool
    assert excel_parse_tool.name == "excel_parse"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_tools.py -v`
Expected: FAIL

**Step 3: Implement LangChain tools**

```python
# backend/app/tools/property_tool.py
from langchain_core.tools import tool


@tool
def property_create(
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
    return {
        "action": "create_property",
        "pending_confirmation": True,
        "data": {
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
        },
    }


property_create_tool = property_create


@tool
def property_query(property_id: int | None = None) -> dict:
    """查询已有的民宿房源信息。可以传入property_id查询指定房源，不传则返回所有房源列表。"""
    return {
        "action": "query_property",
        "property_id": property_id,
    }


property_query_tool = property_query
```

```python
# backend/app/tools/pricing_tool.py
from langchain_core.tools import tool


@tool
def pricing_calculate(
    property_id: int,
    target_date: str,
    base_price: float | None = None,
) -> dict:
    """计算指定房源在目标日期的建议定价。返回保守价、建议价、激进价三档价格以及计算依据明细。target_date格式为YYYY-MM-DD。"""
    return {
        "action": "calculate_pricing",
        "property_id": property_id,
        "target_date": target_date,
        "base_price": base_price,
    }


pricing_calculate_tool = pricing_calculate
```

```python
# backend/app/tools/feedback_tool.py
from langchain_core.tools import tool


@tool
def feedback_record(
    pricing_record_id: int,
    feedback_type: str,
    actual_price: float | None = None,
    note: str | None = None,
) -> dict:
    """记录房东对定价建议的反馈。feedback_type为adopted(采纳)、rejected(拒绝)或adjusted(调整)。如果是调整，需要提供actual_price。返回的数据需要用户确认后才会入库。"""
    return {
        "action": "record_feedback",
        "pending_confirmation": True,
        "data": {
            "pricing_record_id": pricing_record_id,
            "feedback_type": feedback_type,
            "actual_price": actual_price,
            "note": note,
        },
    }


feedback_record_tool = feedback_record
```

```python
# backend/app/tools/excel_tool.py
from langchain_core.tools import tool


@tool
def excel_parse(file_key: str) -> dict:
    """解析用户上传的Excel表格文件。file_key是上传文件后返回的临时文件标识。系统会自动完成数据清洗（去空行、去重、去首尾空格）和统计分析。返回的数据需要用户确认后才会入库。"""
    return {
        "action": "parse_excel",
        "file_key": file_key,
        "pending_confirmation": True,
    }


excel_parse_tool = excel_parse
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_tools.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: add LangChain tool definitions for agent integration"
```

---

## Task 7: LangChain Agent Setup

**Files:**
- Create: `backend/app/agent/betastay_agent.py`
- Create: `backend/app/agent/prompts.py`
- Test: `backend/tests/test_agent.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_agent.py
import pytest


def test_agent_creation():
    from app.agent.betastay_agent import create_betastay_agent
    agent = create_betastay_agent()
    assert agent is not None


def test_agent_has_tools():
    from app.agent.betastay_agent import create_betastay_agent
    # Agent应该有工具绑定
    agent = create_betastay_agent()
    # create_agent返回的是CompiledGraph，验证它可以被调用
    assert hasattr(agent, "invoke")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_agent.py -v`
Expected: FAIL

**Step 3: Create system prompt**

```python
# backend/app/agent/prompts.py
SYSTEM_PROMPT = """你是BetaStay智能民宿定价助手。你的职责是帮助房东管理房源、获取定价建议、记录反馈。

## 核心原则

1. **你不能直接给出价格数字** - 所有价格必须通过pricing_calculate工具计算得出
2. **你不能直接操作数据库** - 所有数据操作必须通过工具完成
3. **所有你的回答必须基于已有数据** - 如果没有相关数据，明确告知用户
4. **涉及数据写入的操作需要用户确认** - 调用写入工具后，提醒用户确认

## 可用工具

- property_create: 录入新房源（需用户确认）
- property_query: 查询房源信息
- pricing_calculate: 计算定价建议
- feedback_record: 记录定价反馈（需用户确认）
- excel_parse: 解析上传的Excel表格（需用户确认）

## 交互规范

- 用中文与用户交流
- 当用户意图不明确时，主动询问澄清
- 返回定价建议时，解释计算依据
- 涉及写操作时，先展示待写入数据，等待用户确认
"""
```

**Step 4: Create agent**

```python
# backend/app/agent/betastay_agent.py
from langchain.agents import create_agent
from langchain_community.chat_models import ChatTongyi
from app.core.config import settings
from app.agent.prompts import SYSTEM_PROMPT
from app.tools.property_tool import property_create_tool, property_query_tool
from app.tools.pricing_tool import pricing_calculate_tool
from app.tools.feedback_tool import feedback_record_tool
from app.tools.excel_tool import excel_parse_tool


def get_tools():
    return [
        property_create_tool,
        property_query_tool,
        pricing_calculate_tool,
        feedback_record_tool,
        excel_parse_tool,
    ]


def create_betastay_agent(checkpointer=None):
    """创建BetaStay Agent实例"""
    model = ChatTongyi(
        model=settings.DASHSCOPE_MODEL,
        dashscope_api_key=settings.DASHSCOPE_API_KEY,
        temperature=0.1,
    )

    agent = create_agent(
        model=model,
        tools=get_tools(),
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )

    return agent
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_agent.py -v`
Expected: PASS (需要DASHSCOPE_API_KEY环境变量，测试环境可用mock)

注意：如果Dashscope API Key未配置，需要在test中mock ChatTongyi。更新conftest：

```python
# 在 backend/tests/conftest.py 中添加
import os
os.environ.setdefault("DASHSCOPE_API_KEY", "test-key-for-unit-tests")
```

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: create LangChain agent with tool bindings and system prompt"
```

---

## Task 8: Chat API with Session Persistence

**Files:**
- Create: `backend/app/api/chat.py`
- Create: `backend/app/services/chat_service.py`
- Create: `backend/app/services/conversation_service.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_chat_api.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_chat_api.py
import pytest


@pytest.mark.asyncio
async def test_create_conversation(client):
    response = await client.post("/api/v1/chat/conversations", json={"title": "定价咨询"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == "定价咨询"


@pytest.mark.asyncio
async def test_list_conversations(client):
    # Create two conversations
    await client.post("/api/v1/chat/conversations", json={"title": "会话1"})
    await client.post("/api/v1/chat/conversations", json={"title": "会话2"})

    response = await client.get("/api/v1/chat/conversations")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_send_message(client):
    # Create conversation
    conv_resp = await client.post("/api/v1/chat/conversations", json={"title": "测试"})
    conv_id = conv_resp.json()["id"]

    # Send message
    response = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "你好，帮我看看我的房源"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_get_conversation_history(client):
    conv_resp = await client.post("/api/v1/chat/conversations", json={"title": "历史测试"})
    conv_id = conv_resp.json()["id"]

    # Send a message
    await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "你好"},
    )

    # Get history
    response = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) >= 2  # user message + assistant reply
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_chat_api.py -v`
Expected: FAIL

**Step 3: Implement conversation service**

```python
# backend/app/services/conversation_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.conversation import Conversation, Message


async def create_conversation(db: AsyncSession, title: str | None = None) -> Conversation:
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


async def get_conversation(db: AsyncSession, conversation_id: int) -> Conversation | None:
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    return result.scalar_one_or_none()


async def save_message(db: AsyncSession, conversation_id: int, role: str, content: str, tool_calls: dict | None = None) -> Message:
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


async def get_messages(db: AsyncSession, conversation_id: int) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())
```

**Step 4: Implement chat service (wraps agent invocation)**

```python
# backend/app/services/chat_service.py
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
```

**Step 5: Create chat API**

```python
# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services import conversation_service, chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


class ConversationCreate(BaseModel):
    title: str | None = None


class ConversationResponse(BaseModel):
    id: int
    title: str | None
    status: str
    model_config = {"from_attributes": True}


class MessageSend(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: str
    model_config = {"from_attributes": True}


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(data: ConversationCreate, db: AsyncSession = Depends(get_db)):
    conv = await conversation_service.create_conversation(db, data.title)
    return conv


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(db: AsyncSession = Depends(get_db)):
    return await conversation_service.list_conversations(db)


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: int, data: MessageSend, db: AsyncSession = Depends(get_db)):
    conv = await conversation_service.get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return await chat_service.process_message(db, conversation_id, data.content)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: int, db: AsyncSession = Depends(get_db)):
    messages = await conversation_service.get_messages(db, conversation_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]
```

**Step 6: Register chat route**

```python
# backend/app/api/router.py (更新)
from fastapi import APIRouter
from app.api.property import router as property_router
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router

api_router = APIRouter()
api_router.include_router(property_router)
api_router.include_router(upload_router)
api_router.include_router(chat_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
```

**Step 7: Run tests**

Run: `cd backend && python -m pytest tests/test_chat_api.py -v`
Expected: PASS（Agent调用部分可能需要mock Dashscope）

**Step 8: Commit**

```bash
git add backend/
git commit -m "feat: add chat API with conversation persistence and agent integration"
```

---

## Task 9: Frontend uni-app Scaffolding

**Files:**
- 使用HBuilderX或CLI创建uni-app项目
- Create: `frontend/` 目录下完整的uni-app项目结构

**Step 1: Initialize uni-app project**

Run: `npx degit dcloudio/uni-preset-vue#vite-ts frontend`

或手动创建核心文件结构：

```
frontend/
├── src/
│   ├── pages/
│   │   ├── index/          # 首页/仪表盘
│   │   ├── chat/           # 对话页
│   │   ├── property/       # 房源管理
│   │   └── history/        # 历史记录
│   ├── components/
│   │   ├── ChatBubble.vue       # 消息气泡
│   │   ├── PriceCard.vue        # 价格建议卡片
│   │   └── ConfirmPanel.vue     # 确认面板
│   ├── stores/
│   │   ├── chat.ts              # 对话状态
│   │   └── property.ts          # 房源状态
│   ├── api/
│   │   ├── request.ts           # 请求封装
│   │   ├── chat.ts              # 对话API
│   │   └── property.ts          # 房源API
│   ├── App.vue
│   ├── main.ts
│   └── pages.json
├── package.json
└── vite.config.ts
```

**Step 2: Create pages.json**

```json
{
  "pages": [
    { "path": "pages/index/index", "style": { "navigationBarTitleText": "BetaStay" } },
    { "path": "pages/chat/index", "style": { "navigationBarTitleText": "智能助手" } },
    { "path": "pages/property/index", "style": { "navigationBarTitleText": "房源管理" } },
    { "path": "pages/history/index", "style": { "navigationBarTitleText": "定价历史" } }
  ],
  "tabBar": {
    "list": [
      { "pagePath": "pages/index/index", "text": "首页" },
      { "pagePath": "pages/chat/index", "text": "助手" },
      { "pagePath": "pages/property/index", "text": "房源" },
      { "pagePath": "pages/history/index", "text": "历史" }
    ]
  }
}
```

**Step 3: Create API request wrapper**

```typescript
// frontend/src/api/request.ts
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  data?: any
}

export async function request<T = any>(options: RequestOptions): Promise<T> {
  return new Promise((resolve, reject) => {
    uni.request({
      url: `${BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else {
          reject(new Error(`Request failed: ${res.statusCode}`))
        }
      },
      fail: (err) => reject(err),
    })
  })
}
```

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold frontend uni-app project structure"
```

---

## Task 10: Frontend Chat Page (MVP Core)

**Files:**
- Create: `frontend/src/pages/chat/index.vue`
- Create: `frontend/src/components/ChatBubble.vue`
- Create: `frontend/src/components/ConfirmPanel.vue`
- Create: `frontend/src/components/PriceCard.vue`
- Create: `frontend/src/api/chat.ts`
- Create: `frontend/src/stores/chat.ts`

**Step 1: Create chat API**

```typescript
// frontend/src/api/chat.ts
import { request } from './request'

export function createConversation(title?: string) {
  return request({ url: '/chat/conversations', method: 'POST', data: { title } })
}

export function listConversations() {
  return request({ url: '/chat/conversations' })
}

export function sendMessage(conversationId: number, content: string) {
  return request({
    url: `/chat/conversations/${conversationId}/messages`,
    method: 'POST',
    data: { content },
  })
}

export function getMessages(conversationId: number) {
  return request({ url: `/chat/conversations/${conversationId}/messages` })
}
```

**Step 2: Create chat store**

```typescript
// frontend/src/stores/chat.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as chatApi from '../api/chat'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<any[]>([])
  const currentConversationId = ref<number | null>(null)
  const messages = ref<any[]>([])
  const loading = ref(false)

  async function createConversation(title?: string) {
    const conv = await chatApi.createConversation(title)
    conversations.value.unshift(conv)
    currentConversationId.value = conv.id
    messages.value = []
    return conv
  }

  async function sendMessage(content: string) {
    if (!currentConversationId.value) {
      await createConversation('新对话')
    }
    messages.value.push({ role: 'user', content, created_at: new Date().toISOString() })
    loading.value = true
    try {
      const reply = await chatApi.sendMessage(currentConversationId.value!, content)
      messages.value.push(reply)
      return reply
    } finally {
      loading.value = false
    }
  }

  async function loadMessages(conversationId: number) {
    currentConversationId.value = conversationId
    messages.value = await chatApi.getMessages(conversationId)
  }

  return { conversations, currentConversationId, messages, loading, createConversation, sendMessage, loadMessages }
})
```

**Step 3: Create ChatBubble component**

```vue
<!-- frontend/src/components/ChatBubble.vue -->
<template>
  <view :class="['chat-bubble', message.role === 'user' ? 'bubble-right' : 'bubble-left']">
    <text class="bubble-content">{{ message.content }}</text>
    <text class="bubble-time">{{ formatTime(message.created_at) }}</text>
  </view>
</template>

<script setup lang="ts">
defineProps<{ message: { role: string; content: string; created_at: string } }>()

function formatTime(iso: string) {
  const d = new Date(iso)
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped>
.chat-bubble {
  max-width: 75%;
  padding: 20rpx 28rpx;
  border-radius: 20rpx;
  margin-bottom: 20rpx;
}
.bubble-left {
  align-self: flex-start;
  background-color: #f0f0f0;
}
.bubble-right {
  align-self: flex-end;
  background-color: #07c160;
  color: #fff;
}
.bubble-content {
  font-size: 28rpx;
  line-height: 1.6;
}
.bubble-time {
  font-size: 20rpx;
  opacity: 0.6;
  margin-top: 8rpx;
  display: block;
  text-align: right;
}
</style>
```

**Step 4: Create ConfirmPanel component**

```vue
<!-- frontend/src/components/ConfirmPanel.vue -->
<template>
  <view v-if="visible" class="confirm-overlay">
    <view class="confirm-panel">
      <text class="confirm-title">数据确认</text>
      <scroll-view scroll-y class="confirm-body">
        <view v-for="(value, key) in data" :key="key" class="confirm-row">
          <text class="confirm-label">{{ key }}</text>
          <text class="confirm-value">{{ value }}</text>
        </view>
      </scroll-view>
      <view class="confirm-actions">
        <button class="btn-cancel" @click="$emit('cancel')">取消</button>
        <button class="btn-confirm" @click="$emit('confirm')">确认入库</button>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{ visible: boolean; data: Record<string, any> }>()
defineEmits<{ confirm: []; cancel: [] }>()
</script>

<style scoped>
.confirm-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: flex-end;
  z-index: 999;
}
.confirm-panel {
  width: 100%;
  background: #fff;
  border-radius: 24rpx 24rpx 0 0;
  padding: 40rpx;
  max-height: 70vh;
}
.confirm-title {
  font-size: 32rpx;
  font-weight: bold;
  margin-bottom: 20rpx;
}
.confirm-body {
  max-height: 50vh;
}
.confirm-row {
  display: flex;
  justify-content: space-between;
  padding: 16rpx 0;
  border-bottom: 1rpx solid #eee;
}
.confirm-label { color: #666; font-size: 28rpx; }
.confirm-value { color: #333; font-size: 28rpx; }
.confirm-actions {
  display: flex;
  gap: 20rpx;
  margin-top: 30rpx;
}
.btn-cancel {
  flex: 1;
  background: #f5f5f5;
  color: #666;
}
.btn-confirm {
  flex: 1;
  background: #07c160;
  color: #fff;
}
</style>
```

**Step 5: Create PriceCard component**

```vue
<!-- frontend/src/components/PriceCard.vue -->
<template>
  <view class="price-card">
    <text class="card-title">定价建议</text>
    <view class="price-tiers">
      <view class="tier">
        <text class="tier-label">保守价</text>
        <text class="tier-price conservative">¥{{ pricing.conservative_price }}</text>
      </view>
      <view class="tier tier-main">
        <text class="tier-label">建议价</text>
        <text class="tier-price suggested">¥{{ pricing.suggested_price }}</text>
      </view>
      <view class="tier">
        <text class="tier-label">激进价</text>
        <text class="tier-price aggressive">¥{{ pricing.aggressive_price }}</text>
      </view>
    </view>
    <view class="card-actions">
      <button size="mini" @click="$emit('adopt', pricing.suggested_price)">采纳建议价</button>
      <button size="mini" @click="$emit('reject')">不合适</button>
      <button size="mini" @click="$emit('adjust')">手动调整</button>
    </view>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  pricing: {
    conservative_price: number
    suggested_price: number
    aggressive_price: number
  }
}>()
defineEmits<{ adopt: [price: number]; reject: []; adjust: [] }>()
</script>

<style scoped>
.price-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  box-shadow: 0 2rpx 12rpx rgba(0,0,0,0.08);
  margin: 16rpx 0;
}
.card-title {
  font-size: 28rpx;
  font-weight: bold;
  margin-bottom: 20rpx;
}
.price-tiers {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20rpx;
}
.tier { text-align: center; }
.tier-label { font-size: 24rpx; color: #999; display: block; }
.tier-price { font-size: 36rpx; font-weight: bold; display: block; margin-top: 8rpx; }
.conservative { color: #52c41a; }
.suggested { color: #1890ff; font-size: 44rpx; }
.aggressive { color: #ff4d4f; }
.tier-main { transform: scale(1.1); }
.card-actions {
  display: flex;
  gap: 16rpx;
  justify-content: center;
}
</style>
```

**Step 6: Create chat page**

```vue
<!-- frontend/src/pages/chat/index.vue -->
<template>
  <view class="chat-page">
    <scroll-view scroll-y class="message-list" :scroll-into-view="scrollTarget">
      <ChatBubble v-for="msg in chatStore.messages" :key="msg.id" :message="msg" />
      <view v-if="chatStore.loading" class="loading-tip">
        <text>AI正在思考...</text>
      </view>
      <view id="scroll-bottom" />
    </scroll-view>

    <view class="input-bar">
      <input
        v-model="inputText"
        class="chat-input"
        placeholder="输入消息..."
        :disabled="chatStore.loading"
        @confirm="handleSend"
      />
      <button class="send-btn" :disabled="!inputText.trim() || chatStore.loading" @click="handleSend">
        发送
      </button>
    </view>

    <ConfirmPanel
      :visible="showConfirm"
      :data="confirmData"
      @confirm="handleConfirm"
      @cancel="showConfirm = false"
    />
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '../../stores/chat'
import ChatBubble from '../../components/ChatBubble.vue'
import ConfirmPanel from '../../components/ConfirmPanel.vue'

const chatStore = useChatStore()
const inputText = ref('')
const scrollTarget = ref('scroll-bottom')
const showConfirm = ref(false)
const confirmData = ref<Record<string, any>>({})

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await chatStore.sendMessage(text)
  scrollTarget.value = 'scroll-bottom'
}

function handleConfirm() {
  showConfirm.value = false
  // TODO: 调用确认入库API
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.message-list {
  flex: 1;
  padding: 20rpx;
  display: flex;
  flex-direction: column;
}
.input-bar {
  display: flex;
  padding: 16rpx 20rpx;
  background: #fff;
  border-top: 1rpx solid #eee;
  gap: 16rpx;
}
.chat-input {
  flex: 1;
  height: 72rpx;
  background: #f5f5f5;
  border-radius: 36rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
}
.send-btn {
  background: #07c160;
  color: #fff;
  border-radius: 36rpx;
  font-size: 28rpx;
  padding: 0 32rpx;
  height: 72rpx;
  line-height: 72rpx;
}
.loading-tip {
  text-align: center;
  padding: 20rpx;
  color: #999;
  font-size: 24rpx;
}
</style>
```

**Step 7: Commit**

```bash
git add frontend/
git commit -m "feat: implement chat page with message bubbles and confirm panel"
```

---

## Task 11: End-to-End Integration Verification

**Files:**
- Create: `backend/tests/test_e2e_flow.py`

**Step 1: Write the end-to-end test**

```python
# backend/tests/test_e2e_flow.py
"""
端到端流程验证：房源录入 → 定价建议 → 反馈记录
注意：此测试需要Dashscope API Key，CI环境中可标记为skip
"""
import pytest


@pytest.mark.asyncio
async def test_minimal_loop(client):
    """测试最小闭环流程"""
    # Step 1: 录入房源
    property_data = {
        "name": "西湖畔民宿",
        "address": "杭州市西湖区北山路88号",
        "room_type": "整套",
        "area": 75.0,
        "facilities": {"wifi": True, "ac": True, "kitchen": True},
        "min_price": 300.0,
        "max_price": 800.0,
        "expected_return_rate": 0.12,
        "vacancy_tolerance": 0.3,
    }
    prop_resp = await client.post("/api/v1/property", json=property_data)
    assert prop_resp.status_code == 200
    property_id = prop_resp.json()["id"]

    # Step 2: 查询房源
    query_resp = await client.get(f"/api/v1/property/{property_id}")
    assert query_resp.status_code == 200
    assert query_resp.json()["name"] == "西湖畔民宿"

    # Step 3: 创建对话
    conv_resp = await client.post("/api/v1/chat/conversations", json={"title": "定价测试"})
    assert conv_resp.status_code == 200
    conv_id = conv_resp.json()["id"]

    # Step 4: 对话存在且可查
    convs_resp = await client.get("/api/v1/chat/conversations")
    assert convs_resp.status_code == 200
    assert len(convs_resp.json()) >= 1

    # Step 5: 验证定价引擎独立运行
    from app.engine.pricing_engine import PricingEngine
    from datetime import date
    engine = PricingEngine()
    pricing = engine.calculate(
        base_price=500.0,
        owner_preference={
            "min_price": 300.0,
            "max_price": 800.0,
            "expected_return_rate": 0.12,
            "vacancy_tolerance": 0.3,
        },
        property_info={"room_type": "整套", "area": 75.0},
        target_date=date(2026, 5, 1),
    )
    assert 300.0 <= pricing["conservative_price"]
    assert pricing["aggressive_price"] <= 800.0
    assert pricing["conservative_price"] <= pricing["suggested_price"] <= pricing["aggressive_price"]
```

**Step 2: Run the full test suite**

Run: `cd backend && python -m pytest tests/ -v --tb=short`
Expected: ALL PASS

**Step 3: Commit**

```bash
git add backend/
git commit -m "test: add end-to-end flow verification for MVP minimal loop"
```

---

## Summary

| Task | 内容 | 关键产出 |
|------|------|---------|
| 1 | Backend项目骨架 | FastAPI app + config + test框架 |
| 2 | 数据库模型 + 迁移 | 6张核心表 + Alembic |
| 3 | 房源CRUD API | property service + routes |
| 4 | Excel上传解析 | parser tool + upload API |
| 5 | 定价引擎 | 6因素加权 + 三档价格 + 边界约束 |
| 6 | LangChain工具 | 5个@tool定义 |
| 7 | Agent搭建 | create_agent + system prompt |
| 8 | 对话API + 持久化 | conversation/message CRUD + agent调用 |
| 9 | 前端骨架 | uni-app项目结构 + 路由 |
| 10 | 对话页面 | ChatBubble + PriceCard + ConfirmPanel |
| 11 | 端到端验证 | 最小闭环集成测试 |
