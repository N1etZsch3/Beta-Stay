from langchain_core.tools import tool
from sqlalchemy import select

from app.models.property import Property
from app.tools.context import get_db_session

# 表单字段定义 — 由 _invoke_agent_stream 在检测到 __FORM_RENDERED__ 后发送给前端
PROPERTY_FORM_DEFINITION = {
    "form_type": "property_create",
    "fields": [
        {"key": "name", "label": "房源名称", "type": "text", "required": True, "placeholder": "例: 西湖畔民宿"},
        {"key": "address", "label": "地址", "type": "text", "required": True, "placeholder": "例: 杭州市西湖区北山街道"},
        {"key": "room_type", "label": "房型", "type": "picker", "required": True, "options": ["整套", "单间", "合住", "别墅", "公寓"]},
        {"key": "area", "label": "面积(㎡)", "type": "number", "required": True, "placeholder": "例: 80"},
        {"key": "description", "label": "描述", "type": "textarea", "required": False, "placeholder": "描述一下你的房源特色..."},
        {"key": "min_price", "label": "最低可接受价(元)", "type": "number", "required": False, "placeholder": "例: 200"},
        {"key": "max_price", "label": "最高价格(元)", "type": "number", "required": False, "placeholder": "例: 800"},
        {"key": "expected_return_rate", "label": "期望收益率", "type": "number", "required": False, "placeholder": "例: 0.08"},
        {"key": "vacancy_tolerance", "label": "空置容忍度", "type": "number", "required": False, "placeholder": "例: 0.2"},
    ],
}


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
                "expected_return_rate": float(prop.expected_return_rate)
                if prop.expected_return_rate
                else None,
                "vacancy_tolerance": float(prop.vacancy_tolerance)
                if prop.vacancy_tolerance
                else None,
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
    """录入新的民宿房源信息。向用户收集信息时，请用（必填）和（选填）标注字段，不要使用 * 号标记。
    必填字段：name（房源名称）、address（地址）、room_type（房型）、area（面积）。
    选填字段：facilities（设施）、description（描述）、min_price（最低价）、max_price（最高价）、expected_return_rate（期望收益率）、vacancy_tolerance（空置容忍度）。
    返回的数据需要用户确认后才会入库。"""
    # 基础验证
    if area <= 0:
        return {"success": False, "error": "面积必须大于0"}
    if min_price is not None and max_price is not None and min_price > max_price:
        return {"success": False, "error": "最低价不能大于最高价"}

    data = {
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
    }

    return {
        "action": "create_property",
        "pending_confirmation": True,
        "data": data,
        "display": {
            "title": "新建房源",
            "items": {
                "名称": name,
                "地址": address,
                "房型": room_type,
                "面积": f"{area}㎡",
                "最低价": f"¥{min_price}" if min_price else "未设置",
                "最高价": f"¥{max_price}" if max_price else "未设置",
            },
        },
    }


property_create_tool = property_create


@tool
async def show_property_form() -> str:
    """当用户想要录入新房源时，调用此工具展示房源录入表单。用户将在前端界面中填写房源信息。

    重要规则：
    - 调用此工具后，你必须立即停止，不要再调用任何其他工具
    - 不要调用 property_query 或 property_create
    - 只需输出一句简短的引导语，例如"请在下方表单中填写房源信息"
    - 然后等待用户提交表单数据（以 [房源表单提交] 开头的消息）
    """
    return "__FORM_RENDERED__"


show_property_form_tool = show_property_form
