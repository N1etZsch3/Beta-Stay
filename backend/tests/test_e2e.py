"""端到端集成测试：覆盖 房源录入 → 查询 → 定价计算 → 会话 + 消息 的完整链路"""
import pytest
from datetime import date


@pytest.mark.asyncio
async def test_e2e_property_create_and_query(client):
    """E2E: 创建房源 → 查询房源"""
    # 1. 创建房源
    payload = {
        "name": "西湖别院",
        "address": "杭州市西湖区龙井路88号",
        "room_type": "整套",
        "area": 120.0,
        "facilities": {"wifi": True, "ac": True, "parking": True, "kitchen": True},
        "description": "紧邻西湖的独栋别院",
        "min_price": 500.0,
        "max_price": 1500.0,
        "expected_return_rate": 0.2,
        "vacancy_tolerance": 0.3,
    }
    create_resp = await client.post("/api/v1/property", json=payload)
    assert create_resp.status_code == 200
    property_data = create_resp.json()
    property_id = property_data["id"]
    assert property_data["name"] == "西湖别院"
    assert property_data["facilities"]["kitchen"] is True

    # 2. 查询房源
    get_resp = await client.get(f"/api/v1/property/{property_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["address"] == "杭州市西湖区龙井路88号"

    # 3. 列表查询
    list_resp = await client.get("/api/v1/property")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


def test_e2e_pricing_engine_calculation():
    """E2E: 定价引擎计算 - 含边界约束验证"""
    from app.engine.pricing_engine import PricingEngine

    engine = PricingEngine()

    # 节假日定价 (劳动节)
    holiday_result = engine.calculate(
        base_price=600.0,
        owner_preference={
            "min_price": 400.0,
            "max_price": 1200.0,
            "expected_return_rate": 0.2,
            "vacancy_tolerance": 0.3,
        },
        property_info={"room_type": "整套", "area": 120.0},
        target_date=date(2026, 5, 1),
    )
    assert holiday_result["conservative_price"] >= 400.0
    assert holiday_result["aggressive_price"] <= 1200.0
    assert holiday_result["conservative_price"] <= holiday_result["suggested_price"]
    assert holiday_result["suggested_price"] <= holiday_result["aggressive_price"]

    # 普通工作日定价
    weekday_result = engine.calculate(
        base_price=600.0,
        owner_preference={
            "min_price": 400.0,
            "max_price": 1200.0,
            "expected_return_rate": 0.2,
            "vacancy_tolerance": 0.3,
        },
        property_info={"room_type": "整套", "area": 120.0},
        target_date=date(2026, 5, 11),  # 周一
    )

    # 节假日价格应高于工作日
    assert holiday_result["suggested_price"] > weekday_result["suggested_price"]


@pytest.mark.asyncio
async def test_e2e_conversation_flow(client):
    """E2E: 创建会话 → 发送消息 → 获取历史"""
    # 1. 创建会话
    conv_resp = await client.post(
        "/api/v1/chat/conversations",
        json={"title": "E2E测试会话"},
    )
    assert conv_resp.status_code == 200
    conv_id = conv_resp.json()["id"]

    # 2. 发送消息
    msg_resp = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": "帮我查看所有房源"},
    )
    assert msg_resp.status_code == 200
    reply = msg_resp.json()
    assert reply["role"] == "assistant"
    assert len(reply["content"]) > 0

    # 3. 获取历史
    history_resp = await client.get(f"/api/v1/chat/conversations/{conv_id}/messages")
    assert history_resp.status_code == 200
    messages = history_resp.json()
    assert len(messages) >= 2  # user + assistant

    # 4. 验证会话列表
    list_resp = await client.get("/api/v1/chat/conversations")
    assert list_resp.status_code == 200
    convs = list_resp.json()
    assert any(c["id"] == conv_id for c in convs)


@pytest.mark.asyncio
async def test_e2e_full_pipeline(client):
    """E2E: 完整流水线 房源录入 → 定价 → 会话反馈"""
    # 1. 创建房源
    prop_resp = await client.post("/api/v1/property", json={
        "name": "E2E全链路测试房源",
        "address": "杭州市滨江区",
        "room_type": "单间",
        "area": 35.0,
        "min_price": 150.0,
        "max_price": 500.0,
    })
    assert prop_resp.status_code == 200
    property_id = prop_resp.json()["id"]

    # 2. 查询确认
    query_resp = await client.get(f"/api/v1/property/{property_id}")
    assert query_resp.status_code == 200
    assert query_resp.json()["name"] == "E2E全链路测试房源"

    # 3. 本地定价计算
    from app.engine.pricing_engine import PricingEngine
    engine = PricingEngine()
    pricing = engine.calculate(
        base_price=250.0,
        owner_preference={"min_price": 150.0, "max_price": 500.0},
        property_info={"room_type": "单间", "area": 35.0},
        target_date=date(2026, 6, 15),
    )
    assert pricing["conservative_price"] >= 150.0
    assert pricing["aggressive_price"] <= 500.0

    # 4. 在会话中讨论定价
    conv_resp = await client.post("/api/v1/chat/conversations", json={"title": "定价讨论"})
    conv_id = conv_resp.json()["id"]
    msg_resp = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        json={"content": f"帮我看看房源{property_id}明天的定价建议"},
    )
    assert msg_resp.status_code == 200
    assert msg_resp.json()["role"] == "assistant"

    # 5. 健康检查
    health_resp = await client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"
