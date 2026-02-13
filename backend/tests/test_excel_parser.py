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
