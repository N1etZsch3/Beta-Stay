from langchain_core.tools import tool


@tool
def feedback_record(
    pricing_record_id: int,
    feedback_type: str,
    actual_price: float | None = None,
    note: str | None = None,
) -> dict:
    """记录房东对定价建议的反馈。feedback_type为adopted(采纳)、rejected(拒绝)或adjusted(调整)。如果是调整，需要提供actual_price。返回的数据需要用户确认后才会入库。"""
    return {
        "action": "record_feedback",
        "pending_confirmation": True,
        "data": {
            "pricing_record_id": pricing_record_id,
            "feedback_type": feedback_type,
            "actual_price": actual_price,
            "note": note,
        },
    }


feedback_record_tool = feedback_record
