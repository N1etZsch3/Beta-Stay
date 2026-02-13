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
