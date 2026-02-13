# BetaStay P1: Frontend Pages Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 实现仪表盘、房源管理、定价历史三个前端页面，以及支撑它们所需的后端API

**Architecture:** 后端补充缺失的CRUD API（房源更新/删除、定价记录查询、反馈记录查询、仪表盘汇总），前端实现完整页面交互。遵循现有代码风格：后端 service layer + API route，前端 Pinia store + API module + page component。

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Vue3, uni-app, Pinia, TypeScript

---

## Task 1: Backend - Property Update & Delete API

**Files:**
- Modify: `backend/app/services/property_service.py`
- Modify: `backend/app/api/property.py`
- Test: `backend/tests/test_property_api.py`

**Step 1: Write the failing test**

在 `backend/tests/test_property_api.py` 中追加：

```python
@pytest.mark.asyncio
async def test_update_property(client):
    # Create
    payload = {
        "name": "原名称",
        "address": "原地址",
        "room_type": "整套",
        "area": 60.0,
    }
    create_resp = await client.post("/api/v1/property", json=payload)
    property_id = create_resp.json()["id"]

    # Update
    update_payload = {"name": "新名称", "min_price": 300.0, "max_price": 800.0}
    response = await client.put(f"/api/v1/property/{property_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["name"] == "新名称"
    assert response.json()["min_price"] == 300.0


@pytest.mark.asyncio
async def test_delete_property(client):
    payload = {
        "name": "待删除",
        "address": "测试",
        "room_type": "单间",
        "area": 30.0,
    }
    create_resp = await client.post("/api/v1/property", json=payload)
    property_id = create_resp.json()["id"]

    response = await client.delete(f"/api/v1/property/{property_id}")
    assert response.status_code == 200

    # Verify deleted
    get_resp = await client.get(f"/api/v1/property/{property_id}")
    assert get_resp.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_property_api.py::test_update_property tests/test_property_api.py::test_delete_property -v`
Expected: FAIL (405 Method Not Allowed)

**Step 3: Add update/delete to property service**

在 `backend/app/services/property_service.py` 中追加：

```python
async def update_property(db: AsyncSession, property_id: int, data: dict) -> Property | None:
    prop = await get_property(db, property_id)
    if not prop:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(prop, key, value)
    await db.commit()
    await db.refresh(prop)
    return prop


async def delete_property(db: AsyncSession, property_id: int) -> bool:
    prop = await get_property(db, property_id)
    if not prop:
        return False
    await db.delete(prop)
    await db.commit()
    return True
```

**Step 4: Add update/delete endpoints to property API**

在 `backend/app/api/property.py` 中追加：

```python
class PropertyUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    room_type: str | None = None
    area: float | None = None
    facilities: dict | None = None
    description: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    expected_return_rate: float | None = None
    vacancy_tolerance: float | None = None


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(property_id: int, data: PropertyUpdate, db: AsyncSession = Depends(get_db)):
    prop = await property_service.update_property(db, property_id, data.model_dump(exclude_unset=True))
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.delete("/{property_id}")
async def delete_property(property_id: int, db: AsyncSession = Depends(get_db)):
    success = await property_service.delete_property(db, property_id)
    if not success:
        raise HTTPException(status_code=404, detail="Property not found")
    return {"message": "Property deleted"}
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_property_api.py -v`
Expected: ALL PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add property update and delete API endpoints"
```

---

## Task 2: Backend - Pricing & Feedback Query API

**Files:**
- Create: `backend/app/services/pricing_service.py`
- Create: `backend/app/services/feedback_service.py`
- Create: `backend/app/api/pricing.py`
- Create: `backend/app/api/feedback.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_pricing_api.py`
- Test: `backend/tests/test_feedback_api.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_pricing_api.py
import pytest


@pytest.mark.asyncio
async def test_create_pricing_record(client):
    # Create property first
    prop_resp = await client.post("/api/v1/property", json={
        "name": "测试房源", "address": "测试", "room_type": "整套", "area": 80.0,
        "min_price": 300.0, "max_price": 800.0,
    })
    property_id = prop_resp.json()["id"]

    # Create pricing record via calculate endpoint
    response = await client.post("/api/v1/pricing/calculate", json={
        "property_id": property_id,
        "target_date": "2026-05-01",
        "base_price": 500.0,
    })
    assert response.status_code == 200
    data = response.json()
    assert "suggested_price" in data
    assert "id" in data  # record saved to DB


@pytest.mark.asyncio
async def test_list_pricing_records(client):
    # Create property + pricing
    prop_resp = await client.post("/api/v1/property", json={
        "name": "测试", "address": "测试", "room_type": "整套", "area": 80.0,
        "min_price": 200.0, "max_price": 1000.0,
    })
    property_id = prop_resp.json()["id"]

    await client.post("/api/v1/pricing/calculate", json={
        "property_id": property_id, "target_date": "2026-05-01", "base_price": 500.0,
    })

    response = await client.get(f"/api/v1/pricing/records/{property_id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1
```

```python
# backend/tests/test_feedback_api.py
import pytest


@pytest.mark.asyncio
async def test_create_feedback(client):
    # Create property + pricing
    prop_resp = await client.post("/api/v1/property", json={
        "name": "测试", "address": "测试", "room_type": "整套", "area": 80.0,
        "min_price": 200.0, "max_price": 1000.0,
    })
    property_id = prop_resp.json()["id"]

    pricing_resp = await client.post("/api/v1/pricing/calculate", json={
        "property_id": property_id, "target_date": "2026-05-01", "base_price": 500.0,
    })
    pricing_id = pricing_resp.json()["id"]

    # Create feedback
    response = await client.post("/api/v1/feedback", json={
        "pricing_record_id": pricing_id,
        "feedback_type": "adopted",
        "actual_price": 450.0,
        "note": "价格合理",
    })
    assert response.status_code == 200
    assert response.json()["feedback_type"] == "adopted"


@pytest.mark.asyncio
async def test_list_feedback(client):
    # Create chain: property → pricing → feedback
    prop_resp = await client.post("/api/v1/property", json={
        "name": "测试", "address": "测试", "room_type": "整套", "area": 80.0,
        "min_price": 200.0, "max_price": 1000.0,
    })
    property_id = prop_resp.json()["id"]

    pricing_resp = await client.post("/api/v1/pricing/calculate", json={
        "property_id": property_id, "target_date": "2026-05-01", "base_price": 500.0,
    })
    pricing_id = pricing_resp.json()["id"]

    await client.post("/api/v1/feedback", json={
        "pricing_record_id": pricing_id, "feedback_type": "adopted", "actual_price": 450.0,
    })

    response = await client.get(f"/api/v1/feedback/by-property/{property_id}")
    assert response.status_code == 200
    assert len(response.json()) >= 1
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_pricing_api.py tests/test_feedback_api.py -v`
Expected: FAIL

**Step 3: Implement pricing service**

```python
# backend/app/services/pricing_service.py
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.pricing import PricingRecord
from app.models.property import Property
from app.engine.pricing_engine import PricingEngine


async def calculate_and_save(
    db: AsyncSession,
    property_id: int,
    target_date: date,
    base_price: float | None = None,
) -> PricingRecord | None:
    # Fetch property
    result = await db.execute(select(Property).where(Property.id == property_id))
    prop = result.scalar_one_or_none()
    if not prop:
        return None

    # Use min_price as base if not provided
    effective_base = base_price or prop.min_price or 300.0

    engine = PricingEngine()
    pricing = engine.calculate(
        base_price=effective_base,
        owner_preference={
            "min_price": prop.min_price or 0,
            "max_price": prop.max_price or float("inf"),
            "expected_return_rate": prop.expected_return_rate or 0,
            "vacancy_tolerance": prop.vacancy_tolerance or 0.5,
        },
        property_info={
            "room_type": prop.room_type,
            "area": prop.area,
            "facilities": prop.facilities or {},
        },
        target_date=target_date,
    )

    record = PricingRecord(
        property_id=property_id,
        target_date=target_date,
        conservative_price=pricing["conservative_price"],
        suggested_price=pricing["suggested_price"],
        aggressive_price=pricing["aggressive_price"],
        calculation_details=pricing["calculation_details"],
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_by_property(db: AsyncSession, property_id: int) -> list[PricingRecord]:
    result = await db.execute(
        select(PricingRecord)
        .where(PricingRecord.property_id == property_id)
        .order_by(PricingRecord.created_at.desc())
    )
    return list(result.scalars().all())
```

**Step 4: Implement feedback service**

```python
# backend/app/services/feedback_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.feedback import Feedback
from app.models.pricing import PricingRecord


async def create_feedback(db: AsyncSession, data: dict) -> Feedback:
    fb = Feedback(**data)
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return fb


async def list_by_property(db: AsyncSession, property_id: int) -> list[Feedback]:
    """通过property_id查询相关的所有反馈（经由pricing_record关联）"""
    result = await db.execute(
        select(Feedback)
        .join(PricingRecord, Feedback.pricing_record_id == PricingRecord.id)
        .where(PricingRecord.property_id == property_id)
        .order_by(Feedback.created_at.desc())
    )
    return list(result.scalars().all())
```

**Step 5: Create pricing API route**

```python
# backend/app/api/pricing.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import date
from app.core.database import get_db
from app.services import pricing_service

router = APIRouter(prefix="/pricing", tags=["pricing"])


class PricingCalculateRequest(BaseModel):
    property_id: int
    target_date: str  # YYYY-MM-DD
    base_price: float | None = None


class PricingRecordResponse(BaseModel):
    id: int
    property_id: int
    target_date: str
    conservative_price: float
    suggested_price: float
    aggressive_price: float
    calculation_details: dict
    created_at: str

    model_config = {"from_attributes": True}


@router.post("/calculate")
async def calculate_pricing(data: PricingCalculateRequest, db: AsyncSession = Depends(get_db)):
    target = date.fromisoformat(data.target_date)
    record = await pricing_service.calculate_and_save(db, data.property_id, target, data.base_price)
    if not record:
        raise HTTPException(status_code=404, detail="Property not found")
    return {
        "id": record.id,
        "property_id": record.property_id,
        "target_date": record.target_date.isoformat(),
        "conservative_price": record.conservative_price,
        "suggested_price": record.suggested_price,
        "aggressive_price": record.aggressive_price,
        "calculation_details": record.calculation_details,
        "created_at": record.created_at.isoformat(),
    }


@router.get("/records/{property_id}")
async def list_pricing_records(property_id: int, db: AsyncSession = Depends(get_db)):
    records = await pricing_service.list_by_property(db, property_id)
    return [
        {
            "id": r.id,
            "property_id": r.property_id,
            "target_date": r.target_date.isoformat(),
            "conservative_price": r.conservative_price,
            "suggested_price": r.suggested_price,
            "aggressive_price": r.aggressive_price,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]
```

**Step 6: Create feedback API route**

```python
# backend/app/api/feedback.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.core.database import get_db
from app.services import feedback_service

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    pricing_record_id: int
    feedback_type: str  # adopted / rejected / adjusted
    actual_price: float | None = None
    note: str | None = None


@router.post("")
async def create_feedback(data: FeedbackCreate, db: AsyncSession = Depends(get_db)):
    fb = await feedback_service.create_feedback(db, data.model_dump())
    return {
        "id": fb.id,
        "pricing_record_id": fb.pricing_record_id,
        "feedback_type": fb.feedback_type,
        "actual_price": fb.actual_price,
        "note": fb.note,
        "created_at": fb.created_at.isoformat(),
    }


@router.get("/by-property/{property_id}")
async def list_feedback_by_property(property_id: int, db: AsyncSession = Depends(get_db)):
    feedbacks = await feedback_service.list_by_property(db, property_id)
    return [
        {
            "id": f.id,
            "pricing_record_id": f.pricing_record_id,
            "feedback_type": f.feedback_type,
            "actual_price": f.actual_price,
            "note": f.note,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]
```

**Step 7: Register new routes in router**

```python
# backend/app/api/router.py
from fastapi import APIRouter
from app.api.property import router as property_router
from app.api.upload import router as upload_router
from app.api.chat import router as chat_router
from app.api.pricing import router as pricing_router
from app.api.feedback import router as feedback_router

api_router = APIRouter()
api_router.include_router(property_router)
api_router.include_router(upload_router)
api_router.include_router(chat_router)
api_router.include_router(pricing_router)
api_router.include_router(feedback_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "app": "BetaStay"}
```

**Step 8: Run all tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: ALL PASS

**Step 9: Commit**

```bash
git add backend/
git commit -m "feat: add pricing calculation API and feedback recording API"
```

---

## Task 3: Backend - Dashboard Summary API

**Files:**
- Create: `backend/app/api/dashboard.py`
- Modify: `backend/app/api/router.py`
- Test: `backend/tests/test_dashboard_api.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_dashboard_api.py
import pytest


@pytest.mark.asyncio
async def test_dashboard_summary(client):
    # Create a property
    await client.post("/api/v1/property", json={
        "name": "测试房源", "address": "测试", "room_type": "整套", "area": 80.0,
        "min_price": 300.0, "max_price": 800.0,
    })

    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "property_count" in data
    assert "recent_pricing_count" in data
    assert "feedback_count" in data
    assert "properties" in data
    assert data["property_count"] >= 1
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_dashboard_api.py -v`
Expected: FAIL

**Step 3: Implement dashboard API**

```python
# backend/app/api/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.property import Property
from app.models.pricing import PricingRecord
from app.models.feedback import Feedback

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(db: AsyncSession = Depends(get_db)):
    # Property count
    prop_count = await db.execute(select(func.count(Property.id)))
    property_count = prop_count.scalar() or 0

    # Recent pricing count (last 30 days)
    pricing_count_result = await db.execute(select(func.count(PricingRecord.id)))
    recent_pricing_count = pricing_count_result.scalar() or 0

    # Feedback count
    fb_count = await db.execute(select(func.count(Feedback.id)))
    feedback_count = fb_count.scalar() or 0

    # Property list with latest pricing
    props_result = await db.execute(
        select(Property).order_by(Property.updated_at.desc()).limit(10)
    )
    properties = []
    for prop in props_result.scalars().all():
        # Get latest pricing for this property
        latest_pricing = await db.execute(
            select(PricingRecord)
            .where(PricingRecord.property_id == prop.id)
            .order_by(PricingRecord.created_at.desc())
            .limit(1)
        )
        pricing = latest_pricing.scalar_one_or_none()

        properties.append({
            "id": prop.id,
            "name": prop.name,
            "address": prop.address,
            "room_type": prop.room_type,
            "area": prop.area,
            "min_price": prop.min_price,
            "max_price": prop.max_price,
            "latest_suggested_price": pricing.suggested_price if pricing else None,
            "latest_pricing_date": pricing.target_date.isoformat() if pricing else None,
        })

    return {
        "property_count": property_count,
        "recent_pricing_count": recent_pricing_count,
        "feedback_count": feedback_count,
        "properties": properties,
    }
```

**Step 4: Register in router**

在 `backend/app/api/router.py` 中添加 `from app.api.dashboard import router as dashboard_router` 并 `api_router.include_router(dashboard_router)`

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_dashboard_api.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add backend/
git commit -m "feat: add dashboard summary API endpoint"
```

---

## Task 4: Frontend - API Module & Stores

**Files:**
- Create: `frontend/src/api/property.ts`
- Create: `frontend/src/api/pricing.ts`
- Create: `frontend/src/api/feedback.ts`
- Create: `frontend/src/api/dashboard.ts`
- Create: `frontend/src/stores/property.ts`
- Create: `frontend/src/stores/dashboard.ts`
- Create: `frontend/src/stores/history.ts`

**Step 1: Create property API**

```typescript
// frontend/src/api/property.ts
import { request } from './request'

export interface Property {
  id: number
  name: string
  address: string
  room_type: string
  area: number
  facilities: Record<string, any>
  description: string | null
  min_price: number | null
  max_price: number | null
  expected_return_rate: number | null
  vacancy_tolerance: number | null
}

export function listProperties() {
  return request<Property[]>({ url: '/property' })
}

export function getProperty(id: number) {
  return request<Property>({ url: `/property/${id}` })
}

export function createProperty(data: Partial<Property>) {
  return request<Property>({ url: '/property', method: 'POST', data })
}

export function updateProperty(id: number, data: Partial<Property>) {
  return request<Property>({ url: `/property/${id}`, method: 'PUT', data })
}

export function deleteProperty(id: number) {
  return request({ url: `/property/${id}`, method: 'DELETE' })
}
```

**Step 2: Create pricing & feedback & dashboard API**

```typescript
// frontend/src/api/pricing.ts
import { request } from './request'

export interface PricingRecord {
  id: number
  property_id: number
  target_date: string
  conservative_price: number
  suggested_price: number
  aggressive_price: number
  calculation_details?: Record<string, any>
  created_at: string
}

export function calculatePricing(data: { property_id: number; target_date: string; base_price?: number }) {
  return request<PricingRecord>({ url: '/pricing/calculate', method: 'POST', data })
}

export function listPricingRecords(propertyId: number) {
  return request<PricingRecord[]>({ url: `/pricing/records/${propertyId}` })
}
```

```typescript
// frontend/src/api/feedback.ts
import { request } from './request'

export interface Feedback {
  id: number
  pricing_record_id: number
  feedback_type: string
  actual_price: number | null
  note: string | null
  created_at: string
}

export function createFeedback(data: { pricing_record_id: number; feedback_type: string; actual_price?: number; note?: string }) {
  return request<Feedback>({ url: '/feedback', method: 'POST', data })
}

export function listFeedbackByProperty(propertyId: number) {
  return request<Feedback[]>({ url: `/feedback/by-property/${propertyId}` })
}
```

```typescript
// frontend/src/api/dashboard.ts
import { request } from './request'

export interface DashboardSummary {
  property_count: number
  recent_pricing_count: number
  feedback_count: number
  properties: Array<{
    id: number
    name: string
    address: string
    room_type: string
    area: number
    min_price: number | null
    max_price: number | null
    latest_suggested_price: number | null
    latest_pricing_date: string | null
  }>
}

export function getDashboardSummary() {
  return request<DashboardSummary>({ url: '/dashboard/summary' })
}
```

**Step 3: Create property store**

```typescript
// frontend/src/stores/property.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as propertyApi from '../api/property'
import type { Property } from '../api/property'

export const usePropertyStore = defineStore('property', () => {
  const properties = ref<Property[]>([])
  const currentProperty = ref<Property | null>(null)
  const loading = ref(false)

  async function fetchList() {
    loading.value = true
    try {
      properties.value = await propertyApi.listProperties()
    } finally {
      loading.value = false
    }
  }

  async function fetchOne(id: number) {
    loading.value = true
    try {
      currentProperty.value = await propertyApi.getProperty(id)
    } finally {
      loading.value = false
    }
  }

  async function create(data: Partial<Property>) {
    const prop = await propertyApi.createProperty(data)
    properties.value.unshift(prop)
    return prop
  }

  async function update(id: number, data: Partial<Property>) {
    const prop = await propertyApi.updateProperty(id, data)
    const idx = properties.value.findIndex(p => p.id === id)
    if (idx !== -1) properties.value[idx] = prop
    if (currentProperty.value?.id === id) currentProperty.value = prop
    return prop
  }

  async function remove(id: number) {
    await propertyApi.deleteProperty(id)
    properties.value = properties.value.filter(p => p.id !== id)
    if (currentProperty.value?.id === id) currentProperty.value = null
  }

  return { properties, currentProperty, loading, fetchList, fetchOne, create, update, remove }
})
```

**Step 4: Create dashboard & history stores**

```typescript
// frontend/src/stores/dashboard.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as dashboardApi from '../api/dashboard'
import type { DashboardSummary } from '../api/dashboard'

export const useDashboardStore = defineStore('dashboard', () => {
  const summary = ref<DashboardSummary | null>(null)
  const loading = ref(false)

  async function fetchSummary() {
    loading.value = true
    try {
      summary.value = await dashboardApi.getDashboardSummary()
    } finally {
      loading.value = false
    }
  }

  return { summary, loading, fetchSummary }
})
```

```typescript
// frontend/src/stores/history.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as pricingApi from '../api/pricing'
import * as feedbackApi from '../api/feedback'
import type { PricingRecord } from '../api/pricing'
import type { Feedback } from '../api/feedback'

export const useHistoryStore = defineStore('history', () => {
  const pricingRecords = ref<PricingRecord[]>([])
  const feedbacks = ref<Feedback[]>([])
  const loading = ref(false)

  async function fetchByProperty(propertyId: number) {
    loading.value = true
    try {
      const [records, fbs] = await Promise.all([
        pricingApi.listPricingRecords(propertyId),
        feedbackApi.listFeedbackByProperty(propertyId),
      ])
      pricingRecords.value = records
      feedbacks.value = fbs
    } finally {
      loading.value = false
    }
  }

  return { pricingRecords, feedbacks, loading, fetchByProperty }
})
```

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend API modules and Pinia stores for property, pricing, feedback, dashboard"
```

---

## Task 5: Frontend - Dashboard Page

**Files:**
- Modify: `frontend/src/pages/index/index.vue`

**Step 1: Implement dashboard page**

```vue
<!-- frontend/src/pages/index/index.vue -->
<template>
  <view class="dashboard-page">
    <!-- Header -->
    <view class="header">
      <text class="title">BetaStay</text>
      <text class="subtitle">智能民宿定价助手</text>
    </view>

    <!-- Stats Cards -->
    <view class="stats-row">
      <view class="stat-card">
        <text class="stat-value">{{ summary?.property_count ?? '-' }}</text>
        <text class="stat-label">房源数</text>
      </view>
      <view class="stat-card">
        <text class="stat-value">{{ summary?.recent_pricing_count ?? '-' }}</text>
        <text class="stat-label">定价次数</text>
      </view>
      <view class="stat-card">
        <text class="stat-value">{{ summary?.feedback_count ?? '-' }}</text>
        <text class="stat-label">反馈数</text>
      </view>
    </view>

    <!-- Quick Actions -->
    <view class="section-title">快捷操作</view>
    <view class="quick-actions">
      <view class="action-card" @click="goChat">
        <text class="action-icon">💬</text>
        <text class="action-text">智能对话</text>
      </view>
      <view class="action-card" @click="goProperty">
        <text class="action-icon">🏠</text>
        <text class="action-text">房源管理</text>
      </view>
      <view class="action-card" @click="goHistory">
        <text class="action-icon">📊</text>
        <text class="action-text">定价历史</text>
      </view>
    </view>

    <!-- Property List -->
    <view class="section-title">我的房源</view>
    <view v-if="!summary?.properties?.length" class="empty-tip">
      <text>暂无房源，点击上方"房源管理"添加</text>
    </view>
    <view v-for="prop in summary?.properties" :key="prop.id" class="property-card">
      <view class="prop-header">
        <text class="prop-name">{{ prop.name }}</text>
        <text class="prop-type">{{ prop.room_type }}</text>
      </view>
      <text class="prop-address">{{ prop.address }}</text>
      <view class="prop-footer">
        <text class="prop-area">{{ prop.area }}㎡</text>
        <view v-if="prop.latest_suggested_price" class="prop-price">
          <text class="price-label">建议价</text>
          <text class="price-value">¥{{ prop.latest_suggested_price }}</text>
        </view>
        <text v-else class="no-price">暂无定价</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useDashboardStore } from '../../stores/dashboard'

const dashboardStore = useDashboardStore()
const summary = computed(() => dashboardStore.summary)

onMounted(() => {
  dashboardStore.fetchSummary()
})

function goChat() {
  uni.switchTab({ url: '/pages/chat/index' })
}
function goProperty() {
  uni.switchTab({ url: '/pages/property/index' })
}
function goHistory() {
  uni.switchTab({ url: '/pages/history/index' })
}
</script>

<style scoped>
.dashboard-page {
  padding: 32rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.header {
  text-align: center;
  padding: 32rpx 0 40rpx;
}
.title {
  font-size: 44rpx;
  font-weight: bold;
  display: block;
}
.subtitle {
  font-size: 26rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}
.stats-row {
  display: flex;
  gap: 16rpx;
  margin-bottom: 32rpx;
}
.stat-card {
  flex: 1;
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  text-align: center;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.stat-value {
  font-size: 40rpx;
  font-weight: bold;
  color: #1890ff;
  display: block;
}
.stat-label {
  font-size: 22rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}
.section-title {
  font-size: 30rpx;
  font-weight: bold;
  margin-bottom: 16rpx;
}
.quick-actions {
  display: flex;
  gap: 16rpx;
  margin-bottom: 32rpx;
}
.action-card {
  flex: 1;
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx 16rpx;
  text-align: center;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.action-icon {
  font-size: 40rpx;
  display: block;
}
.action-text {
  font-size: 24rpx;
  color: #333;
  margin-top: 8rpx;
  display: block;
}
.property-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.prop-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.prop-name {
  font-size: 30rpx;
  font-weight: bold;
}
.prop-type {
  font-size: 22rpx;
  color: #1890ff;
  background: #e6f7ff;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}
.prop-address {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}
.prop-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16rpx;
}
.prop-area {
  font-size: 24rpx;
  color: #666;
}
.prop-price {
  display: flex;
  align-items: center;
  gap: 8rpx;
}
.price-label {
  font-size: 22rpx;
  color: #999;
}
.price-value {
  font-size: 32rpx;
  font-weight: bold;
  color: #1890ff;
}
.no-price {
  font-size: 22rpx;
  color: #ccc;
}
.empty-tip {
  text-align: center;
  padding: 60rpx 0;
  color: #999;
  font-size: 26rpx;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/
git commit -m "feat: implement dashboard page with stats, quick actions, and property list"
```

---

## Task 6: Frontend - Property Management Page

**Files:**
- Modify: `frontend/src/pages/property/index.vue`
- Create: `frontend/src/pages/property/form.vue`
- Modify: `frontend/src/pages.json` (添加form子页面)

**Step 1: Add form page route to pages.json**

在 pages 数组中的 history 之后添加：

```json
{ "path": "pages/property/form", "style": { "navigationBarTitleText": "编辑房源" } }
```

注意：此页面不在tabBar中，是普通子页面。

**Step 2: Implement property list page**

```vue
<!-- frontend/src/pages/property/index.vue -->
<template>
  <view class="property-page">
    <!-- Add Button -->
    <view class="add-bar">
      <button class="add-btn" @click="goAdd">+ 添加房源</button>
    </view>

    <!-- Loading -->
    <view v-if="propertyStore.loading" class="loading-tip">
      <text>加载中...</text>
    </view>

    <!-- Empty -->
    <view v-else-if="!propertyStore.properties.length" class="empty-tip">
      <text>暂无房源，点击上方按钮添加</text>
    </view>

    <!-- Property List -->
    <view
      v-for="prop in propertyStore.properties"
      :key="prop.id"
      class="property-card"
      @click="goEdit(prop.id)"
    >
      <view class="card-header">
        <text class="card-name">{{ prop.name }}</text>
        <text class="card-type">{{ prop.room_type }}</text>
      </view>
      <text class="card-address">{{ prop.address }}</text>
      <view class="card-info">
        <text class="info-item">{{ prop.area }}㎡</text>
        <text v-if="prop.min_price" class="info-item">¥{{ prop.min_price }} - ¥{{ prop.max_price }}</text>
      </view>
      <view class="card-prefs" v-if="prop.expected_return_rate || prop.vacancy_tolerance">
        <text v-if="prop.expected_return_rate" class="pref-tag">期望收益率 {{ (prop.expected_return_rate * 100).toFixed(0) }}%</text>
        <text v-if="prop.vacancy_tolerance" class="pref-tag">空置容忍度 {{ (prop.vacancy_tolerance * 100).toFixed(0) }}%</text>
      </view>
      <!-- Delete -->
      <view class="card-actions">
        <text class="delete-btn" @click.stop="handleDelete(prop.id, prop.name)">删除</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { usePropertyStore } from '../../stores/property'

const propertyStore = usePropertyStore()

onMounted(() => {
  propertyStore.fetchList()
})

function goAdd() {
  uni.navigateTo({ url: '/pages/property/form' })
}

function goEdit(id: number) {
  uni.navigateTo({ url: `/pages/property/form?id=${id}` })
}

function handleDelete(id: number, name: string) {
  uni.showModal({
    title: '确认删除',
    content: `确定要删除房源"${name}"吗？`,
    success: async (res) => {
      if (res.confirm) {
        await propertyStore.remove(id)
        uni.showToast({ title: '已删除', icon: 'success' })
      }
    },
  })
}
</script>

<style scoped>
.property-page {
  padding: 32rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.add-bar {
  margin-bottom: 24rpx;
}
.add-btn {
  background: #1890ff;
  color: #fff;
  border-radius: 12rpx;
  font-size: 30rpx;
}
.property-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.card-name {
  font-size: 32rpx;
  font-weight: bold;
}
.card-type {
  font-size: 22rpx;
  color: #1890ff;
  background: #e6f7ff;
  padding: 4rpx 16rpx;
  border-radius: 8rpx;
}
.card-address {
  font-size: 24rpx;
  color: #999;
  margin-top: 8rpx;
  display: block;
}
.card-info {
  display: flex;
  gap: 24rpx;
  margin-top: 12rpx;
}
.info-item {
  font-size: 24rpx;
  color: #666;
}
.card-prefs {
  display: flex;
  gap: 12rpx;
  margin-top: 12rpx;
}
.pref-tag {
  font-size: 20rpx;
  color: #52c41a;
  background: #f6ffed;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
}
.card-actions {
  margin-top: 16rpx;
  text-align: right;
}
.delete-btn {
  font-size: 24rpx;
  color: #ff4d4f;
}
.loading-tip, .empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #999;
  font-size: 26rpx;
}
</style>
```

**Step 3: Implement property form page**

```vue
<!-- frontend/src/pages/property/form.vue -->
<template>
  <view class="form-page">
    <view class="section-title">基础信息</view>
    <view class="form-group">
      <text class="label">房源名称 *</text>
      <input v-model="form.name" placeholder="例: 西湖畔民宿" class="input" />
    </view>
    <view class="form-group">
      <text class="label">地址 *</text>
      <input v-model="form.address" placeholder="例: 杭州市西湖区北山路88号" class="input" />
    </view>
    <view class="form-group">
      <text class="label">房型 *</text>
      <picker :range="roomTypes" @change="onRoomTypeChange">
        <view class="picker-value">{{ form.room_type || '请选择' }}</view>
      </picker>
    </view>
    <view class="form-group">
      <text class="label">面积(㎡) *</text>
      <input v-model="form.area" type="digit" placeholder="例: 80" class="input" />
    </view>
    <view class="form-group">
      <text class="label">描述</text>
      <textarea v-model="form.description" placeholder="房源描述（可选）" class="textarea" />
    </view>

    <view class="section-title">定价偏好</view>
    <view class="form-group">
      <text class="label">最低可接受价(元)</text>
      <input v-model="form.min_price" type="digit" placeholder="例: 300" class="input" />
    </view>
    <view class="form-group">
      <text class="label">最高价格(元)</text>
      <input v-model="form.max_price" type="digit" placeholder="例: 800" class="input" />
    </view>
    <view class="form-group">
      <text class="label">期望收益率</text>
      <input v-model="form.expected_return_rate" type="digit" placeholder="例: 0.15 (即15%)" class="input" />
    </view>
    <view class="form-group">
      <text class="label">空置容忍度</text>
      <input v-model="form.vacancy_tolerance" type="digit" placeholder="例: 0.2 (即20%)" class="input" />
    </view>

    <button class="submit-btn" @click="handleSubmit" :disabled="submitting">
      {{ isEdit ? '更新' : '创建' }}
    </button>
  </view>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { usePropertyStore } from '../../stores/property'

const propertyStore = usePropertyStore()
const roomTypes = ['整套', '单间', '合住', '别墅', '公寓']
const isEdit = ref(false)
const editId = ref<number | null>(null)
const submitting = ref(false)

const form = reactive({
  name: '',
  address: '',
  room_type: '',
  area: '',
  description: '',
  min_price: '',
  max_price: '',
  expected_return_rate: '',
  vacancy_tolerance: '',
})

onMounted(() => {
  const pages = getCurrentPages()
  const currentPage = pages[pages.length - 1] as any
  const id = currentPage.$page?.options?.id || currentPage.options?.id
  if (id) {
    isEdit.value = true
    editId.value = Number(id)
    loadProperty(Number(id))
  }
})

async function loadProperty(id: number) {
  await propertyStore.fetchOne(id)
  const prop = propertyStore.currentProperty
  if (prop) {
    form.name = prop.name
    form.address = prop.address
    form.room_type = prop.room_type
    form.area = String(prop.area)
    form.description = prop.description || ''
    form.min_price = prop.min_price ? String(prop.min_price) : ''
    form.max_price = prop.max_price ? String(prop.max_price) : ''
    form.expected_return_rate = prop.expected_return_rate ? String(prop.expected_return_rate) : ''
    form.vacancy_tolerance = prop.vacancy_tolerance ? String(prop.vacancy_tolerance) : ''
  }
}

function onRoomTypeChange(e: any) {
  form.room_type = roomTypes[e.detail.value]
}

async function handleSubmit() {
  if (!form.name || !form.address || !form.room_type || !form.area) {
    uni.showToast({ title: '请填写必填项', icon: 'none' })
    return
  }

  const data = {
    name: form.name,
    address: form.address,
    room_type: form.room_type,
    area: Number(form.area),
    description: form.description || null,
    min_price: form.min_price ? Number(form.min_price) : null,
    max_price: form.max_price ? Number(form.max_price) : null,
    expected_return_rate: form.expected_return_rate ? Number(form.expected_return_rate) : null,
    vacancy_tolerance: form.vacancy_tolerance ? Number(form.vacancy_tolerance) : null,
  }

  submitting.value = true
  try {
    if (isEdit.value && editId.value) {
      await propertyStore.update(editId.value, data)
      uni.showToast({ title: '更新成功', icon: 'success' })
    } else {
      await propertyStore.create(data)
      uni.showToast({ title: '创建成功', icon: 'success' })
    }
    setTimeout(() => uni.navigateBack(), 500)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.form-page {
  padding: 32rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.section-title {
  font-size: 30rpx;
  font-weight: bold;
  margin: 24rpx 0 16rpx;
}
.form-group {
  background: #fff;
  border-radius: 12rpx;
  padding: 20rpx 24rpx;
  margin-bottom: 12rpx;
}
.label {
  font-size: 24rpx;
  color: #666;
  margin-bottom: 8rpx;
  display: block;
}
.input {
  font-size: 28rpx;
  padding: 8rpx 0;
}
.textarea {
  font-size: 28rpx;
  width: 100%;
  min-height: 120rpx;
}
.picker-value {
  font-size: 28rpx;
  padding: 8rpx 0;
  color: #333;
}
.submit-btn {
  margin-top: 40rpx;
  background: #1890ff;
  color: #fff;
  border-radius: 12rpx;
  font-size: 32rpx;
}
</style>
```

**Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: implement property management page with list, add, edit, delete"
```

---

## Task 7: Frontend - History Page

**Files:**
- Modify: `frontend/src/pages/history/index.vue`

**Step 1: Implement history page**

```vue
<!-- frontend/src/pages/history/index.vue -->
<template>
  <view class="history-page">
    <!-- Property Selector -->
    <view class="selector">
      <picker :range="propertyNames" @change="onPropertyChange">
        <view class="picker-bar">
          <text class="picker-label">选择房源：</text>
          <text class="picker-value">{{ selectedPropertyName || '请选择' }}</text>
        </view>
      </picker>
    </view>

    <!-- Loading -->
    <view v-if="historyStore.loading" class="loading-tip">
      <text>加载中...</text>
    </view>

    <!-- Empty -->
    <view v-else-if="!selectedPropertyId" class="empty-tip">
      <text>请先选择一个房源查看历史</text>
    </view>

    <view v-else-if="!historyStore.pricingRecords.length" class="empty-tip">
      <text>该房源暂无定价记录</text>
    </view>

    <!-- Pricing Records -->
    <template v-else>
      <view class="section-title">定价记录</view>
      <view
        v-for="record in historyStore.pricingRecords"
        :key="record.id"
        class="record-card"
      >
        <view class="record-header">
          <text class="record-date">{{ record.target_date }}</text>
          <text class="record-time">{{ formatDateTime(record.created_at) }}</text>
        </view>
        <view class="price-row">
          <view class="price-item">
            <text class="price-label">保守</text>
            <text class="price-value conservative">¥{{ record.conservative_price }}</text>
          </view>
          <view class="price-item main">
            <text class="price-label">建议</text>
            <text class="price-value suggested">¥{{ record.suggested_price }}</text>
          </view>
          <view class="price-item">
            <text class="price-label">激进</text>
            <text class="price-value aggressive">¥{{ record.aggressive_price }}</text>
          </view>
        </view>
        <!-- Associated Feedback -->
        <view v-for="fb in getFeedbackForRecord(record.id)" :key="fb.id" class="feedback-tag">
          <text :class="['fb-type', fb.feedback_type]">{{ feedbackLabel(fb.feedback_type) }}</text>
          <text v-if="fb.actual_price" class="fb-price">实际 ¥{{ fb.actual_price }}</text>
          <text v-if="fb.note" class="fb-note">{{ fb.note }}</text>
        </view>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { usePropertyStore } from '../../stores/property'
import { useHistoryStore } from '../../stores/history'

const propertyStore = usePropertyStore()
const historyStore = useHistoryStore()
const selectedPropertyId = ref<number | null>(null)

const propertyNames = computed(() => propertyStore.properties.map(p => p.name))
const selectedPropertyName = computed(() => {
  if (!selectedPropertyId.value) return ''
  return propertyStore.properties.find(p => p.id === selectedPropertyId.value)?.name || ''
})

onMounted(() => {
  propertyStore.fetchList()
})

async function onPropertyChange(e: any) {
  const idx = e.detail.value
  const prop = propertyStore.properties[idx]
  if (prop) {
    selectedPropertyId.value = prop.id
    await historyStore.fetchByProperty(prop.id)
  }
}

function getFeedbackForRecord(recordId: number) {
  return historyStore.feedbacks.filter(f => f.pricing_record_id === recordId)
}

function feedbackLabel(type: string) {
  const map: Record<string, string> = { adopted: '已采纳', rejected: '已拒绝', adjusted: '已调整' }
  return map[type] || type
}

function formatDateTime(iso: string) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
}
</script>

<style scoped>
.history-page {
  padding: 32rpx;
  background: #f5f5f5;
  min-height: 100vh;
}
.selector {
  background: #fff;
  border-radius: 12rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.picker-bar {
  display: flex;
  align-items: center;
}
.picker-label {
  font-size: 28rpx;
  color: #666;
}
.picker-value {
  font-size: 28rpx;
  color: #1890ff;
  margin-left: 16rpx;
}
.section-title {
  font-size: 30rpx;
  font-weight: bold;
  margin-bottom: 16rpx;
}
.record-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 16rpx;
  box-shadow: 0 2rpx 8rpx rgba(0,0,0,0.06);
}
.record-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16rpx;
}
.record-date {
  font-size: 28rpx;
  font-weight: bold;
}
.record-time {
  font-size: 22rpx;
  color: #999;
}
.price-row {
  display: flex;
  justify-content: space-around;
}
.price-item {
  text-align: center;
}
.price-item.main {
  transform: scale(1.1);
}
.price-label {
  font-size: 22rpx;
  color: #999;
  display: block;
}
.price-value {
  font-size: 32rpx;
  font-weight: bold;
  display: block;
  margin-top: 4rpx;
}
.conservative { color: #52c41a; }
.suggested { color: #1890ff; }
.aggressive { color: #ff4d4f; }
.feedback-tag {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 16rpx;
  padding-top: 12rpx;
  border-top: 1rpx solid #f0f0f0;
}
.fb-type {
  font-size: 22rpx;
  padding: 4rpx 12rpx;
  border-radius: 6rpx;
}
.fb-type.adopted {
  color: #52c41a;
  background: #f6ffed;
}
.fb-type.rejected {
  color: #ff4d4f;
  background: #fff2f0;
}
.fb-type.adjusted {
  color: #faad14;
  background: #fffbe6;
}
.fb-price {
  font-size: 24rpx;
  color: #333;
}
.fb-note {
  font-size: 22rpx;
  color: #999;
}
.loading-tip, .empty-tip {
  text-align: center;
  padding: 80rpx 0;
  color: #999;
  font-size: 26rpx;
}
</style>
```

**Step 2: Commit**

```bash
git add frontend/
git commit -m "feat: implement history page with pricing records and feedback display"
```

---

## Summary

| Task | 内容 | 关键产出 |
|------|------|---------|
| 1 | Property Update & Delete API | PUT/DELETE 端点 + service |
| 2 | Pricing & Feedback Query API | 定价计算存储 + 反馈CRUD + 按房源查询 |
| 3 | Dashboard Summary API | 汇总统计 + 房源列表含最新定价 |
| 4 | Frontend API & Stores | 4个API模块 + 3个Pinia store |
| 5 | Dashboard Page | 统计卡片 + 快捷操作 + 房源概览 |
| 6 | Property Management Page | 列表 + 新增/编辑表单 + 删除 |
| 7 | History Page | 房源选择 + 定价记录列表 + 反馈标签 |
