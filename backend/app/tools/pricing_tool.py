from langchain_core.tools import tool


@tool
def pricing_calculate(
    property_id: int,
    target_date: str,
    base_price: float | None = None,
) -> dict:
    """计算指定房源在目标日期的建议定价。返回保守价、建议价、激进价三档价格以及计算依据明细。target_date格式为YYYY-MM-DD。"""
    return {
        "action": "calculate_pricing",
        "property_id": property_id,
        "target_date": target_date,
        "base_price": base_price,
    }


pricing_calculate_tool = pricing_calculate
