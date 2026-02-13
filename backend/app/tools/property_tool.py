from langchain_core.tools import tool
from app.tools.context import get_db_session
from sqlalchemy import select
from app.models.property import Property


@tool
async def property_query(property_id: int | None = None) -> dict:
    """查询已有的民宿房源信息。可以传入property_id查询指定房源，不传则返回所有房源列表。"""
    db = get_db_session()

    if property_id:
        result = await db.execute(select(Property).where(Property.id == property_id))
        prop = result.scalar_one_or_none()
        if not prop:
            return {"success": False, "error": f"未找到ID为{property_id}的房源"}
        return {
            "success": True,
            "property": {
                "id": prop.id,
                "name": prop.name,
                "address": prop.address,
                "room_type": prop.room_type,
                "area": float(prop.area),
                "facilities": prop.facilities or {},
                "description": prop.description,
                "min_price": float(prop.min_price) if prop.min_price else None,
                "max_price": float(prop.max_price) if prop.max_price else None,
                "expected_return_rate": float(prop.expected_return_rate) if prop.expected_return_rate else None,
                "vacancy_tolerance": float(prop.vacancy_tolerance) if prop.vacancy_tolerance else None,
            },
        }
    else:
        result = await db.execute(select(Property).order_by(Property.created_at.desc()))
        props = result.scalars().all()
        return {
            "success": True,
            "total": len(list(props)),
            "properties": [
                {
                    "id": p.id,
                    "name": p.name,
                    "address": p.address,
                    "room_type": p.room_type,
                    "area": float(p.area),
                    "min_price": float(p.min_price) if p.min_price else None,
                    "max_price": float(p.max_price) if p.max_price else None,
                }
                for p in props
            ],
        }


property_query_tool = property_query


@tool
async def property_create(
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
