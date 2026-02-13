from langchain_core.tools import tool


@tool
def excel_parse(file_key: str) -> dict:
    """解析用户上传的Excel表格文件。file_key是上传文件后返回的临时文件标识。系统会自动完成数据清洗（去空行、去重、去首尾空格）和统计分析。返回的数据需要用户确认后才会入库。"""
    return {
        "action": "parse_excel",
        "file_key": file_key,
        "pending_confirmation": True,
    }


excel_parse_tool = excel_parse
