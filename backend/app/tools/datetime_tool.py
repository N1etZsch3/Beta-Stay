from datetime import datetime, date
from langchain_core.tools import tool


@tool
def get_current_time() -> dict:
    """获取当前日期和时间信息，包括星期几、是否周末等。当需要知道"今天"、"明天"、"当前时间"时调用此工具。"""
    now = datetime.now()
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    return {
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": weekday_names[now.weekday()],
        "is_weekend": now.weekday() >= 5,
    }


get_current_time_tool = get_current_time
