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
