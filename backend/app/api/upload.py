from fastapi import APIRouter, UploadFile, File, HTTPException
from app.tools.excel_parser import parse_excel_bytes

router = APIRouter(prefix="/upload", tags=["upload"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls"}


@router.post("/excel")
async def upload_excel(file: UploadFile = File(...)):
    """上传并解析Excel文件，返回结构化数据（待确认）"""
    filename = file.filename or ""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"仅支持 {', '.join(ALLOWED_EXTENSIONS)} 格式")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件过大，最大支持10MB")

    result = parse_excel_bytes(content, filename)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=f"解析失败: {result['error']}")

    # 标记为待确认，前端需展示确认弹窗
    result["pending_confirmation"] = True
    return result
