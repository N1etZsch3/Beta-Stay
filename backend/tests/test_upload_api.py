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
