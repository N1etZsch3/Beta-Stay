from langchain_core.tools import tool
from datetime import date
from app.tools.context import get_db_session
from app.services.pricing_service import calculate_and_save


@tool
async def pricing_calculate(
    property_id: int,
    target_date: str,
    base_price: float | None = None,
) -> dict:
    """计算指定房源在目标日期的建议定价。返回保守价、建议价、激进价三档价格以及计算依据明细。target_date格式为YYYY-MM-DD。"""
    db = get_db_session()

    try:
        target = date.fromisoformat(target_date)
    except ValueError:
        return {"success": False, "error": f"日期格式错误: {target_date}，请使用YYYY-MM-DD格式"}

    record = await calculate_and_save(db, property_id, target, base_price)
    if not record:
        return {"success": False, "error": f"未找到ID为{property_id}的房源"}

    return {
        "success": True,
        "pricing_record_id": record.id,
        "property_id": record.property_id,
        "target_date": record.target_date.isoformat(),
        "conservative_price": float(record.conservative_price),
        "suggested_price": float(record.suggested_price),
        "aggressive_price": float(record.aggressive_price),
        "calculation_details": record.calculation_details,
    }


pricing_calculate_tool = pricing_calculate
