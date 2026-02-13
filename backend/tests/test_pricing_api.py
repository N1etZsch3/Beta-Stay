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
