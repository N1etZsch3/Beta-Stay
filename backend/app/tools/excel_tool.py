import os
from langchain_core.tools import tool
from app.tools.excel_parser import parse_excel


@tool
async def excel_parse(file_path: str) -> dict:
    """解析用户上传的Excel表格文件。file_path是上传文件的服务器端路径。系统会自动完成数据清洗（去空行、去重、去首尾空格）和统计分析。"""
    if not os.path.exists(file_path):
        return {"success": False, "error": f"文件不存在: {file_path}"}

    result = parse_excel(file_path)
    if not result["success"]:
        return result

    # 如果数据量太大，只返回摘要和前10条
    data = result.get("data", [])
    preview = data[:10] if len(data) > 10 else data

    return {
        "success": True,
        "total_rows": result["total_rows"],
        "stats": result["stats"],
        "preview": preview,
        "full_data_rows": len(data),
    }


excel_parse_tool = excel_parse
