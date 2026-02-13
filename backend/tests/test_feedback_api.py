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
