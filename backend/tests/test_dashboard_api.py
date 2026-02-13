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
