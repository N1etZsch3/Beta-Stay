from langchain_core.tools import tool


@tool
def property_create(
    name: str,
    address: str,
    room_type: str,
    area: float,
    facilities: dict | None = None,
    description: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    expected_return_rate: float | None = None,
    vacancy_tolerance: float | None = None,
) -> dict:
    """录入新的民宿房源信息。需要提供房源名称、地址、房型、面积等基础信息，以及房东偏好（最低价、最高价、期望收益率、空置容忍度）。返回的数据需要用户确认后才会入库。"""
    return {
        "action": "create_property",
        "pending_confirmation": True,
        "data": {
            "name": name,
            "address": address,
            "room_type": room_type,
            "area": area,
            "facilities": facilities or {},
            "description": description,
            "min_price": min_price,
            "max_price": max_price,
            "expected_return_rate": expected_return_rate,
            "vacancy_tolerance": vacancy_tolerance,
        },
    }


property_create_tool = property_create


@tool
def property_query(property_id: int | None = None) -> dict:
    """查询已有的民宿房源信息。可以传入property_id查询指定房源，不传则返回所有房源列表。"""
    return {
        "action": "query_property",
        "property_id": property_id,
    }


property_query_tool = property_query
