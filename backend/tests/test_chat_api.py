import re

import pytest

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


@pytest.mark.asyncio
async def test_create_conversation(client):
    response = await client.post(
        "/api/v1/chat/conversations", json={"title": "定价咨询"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["id"], str)
    assert UUID_PATTERN.match(data["id"]), (
        f"id should be UUID format, got: {data['id']}"
    )
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

    # Send message — agent call may fail with test API key, but the endpoint
    # should still return 200 with an error-fallback reply
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
    conv_resp = await client.post(
        "/api/v1/chat/conversations", json={"title": "历史测试"}
    )
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


@pytest.mark.asyncio
async def test_delete_conversation(client):
    # Create a conversation
    conv_resp = await client.post(
        "/api/v1/chat/conversations", json={"title": "待删除会话"}
    )
    assert conv_resp.status_code == 200
    conv_id = conv_resp.json()["id"]

    # Delete it
    del_resp = await client.delete(f"/api/v1/chat/conversations/{conv_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Verify it's gone from the list
    list_resp = await client.get("/api/v1/chat/conversations")
    ids = [c["id"] for c in list_resp.json()]
    assert conv_id not in ids


@pytest.mark.asyncio
async def test_delete_conversation_not_found(client):
    resp = await client.delete(
        "/api/v1/chat/conversations/00000000-0000-0000-0000-000000000000"
    )
    assert resp.status_code == 404
