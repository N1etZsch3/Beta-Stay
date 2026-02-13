from langchain_core.tools import tool


@tool
async def feedback_record(
    pricing_record_id: int,
    feedback_type: str,
    actual_price: float | None = None,
    note: str | None = None,
) -> dict:
    """记录房东对定价建议的反馈。feedback_type为adopted(采纳)、rejected(拒绝)或adjusted(调整)。如果是调整，需要提供actual_price。返回的数据需要用户确认后才会入库。"""
    # 验证
    valid_types = {"adopted", "rejected", "adjusted"}
    if feedback_type not in valid_types:
        return {"success": False, "error": f"feedback_type必须是 {valid_types} 之一"}
    if feedback_type == "adjusted" and actual_price is None:
        return {"success": False, "error": "调整反馈需要提供actual_price"}

    data = {
        "pricing_record_id": pricing_record_id,
        "feedback_type": feedback_type,
        "actual_price": actual_price,
        "note": note,
    }

    type_labels = {"adopted": "采纳建议价", "rejected": "拒绝建议", "adjusted": "手动调整"}
    return {
        "action": "record_feedback",
        "pending_confirmation": True,
        "data": data,
        "display": {
            "title": "定价反馈",
            "items": {
                "定价记录ID": str(pricing_record_id),
                "反馈类型": type_labels.get(feedback_type, feedback_type),
                "实际价格": f"¥{actual_price}" if actual_price else "—",
                "备注": note or "无",
            },
        },
    }


feedback_record_tool = feedback_record
