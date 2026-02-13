import pandas as pd
from io import BytesIO


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """清洗DataFrame：去空行、去重、去首尾空格、标准化列名"""
    # 去除全空行
    df = df.dropna(how="all")

    # 字符串列去首尾空格
    string_cols = df.select_dtypes(include=["object"]).columns
    for col in string_cols:
        df[col] = df[col].str.strip()

    # 去重
    df = df.drop_duplicates()

    # 重置索引
    df = df.reset_index(drop=True)

    return df


def _get_stats(df: pd.DataFrame) -> dict:
    """生成数据统计摘要"""
    stats = {
        "total_rows": len(df),
        "columns": list(df.columns),
        "null_counts": df.isnull().sum().to_dict(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }
    # 数值列统计
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for col in numeric_cols:
        stats[f"{col}_min"] = float(df[col].min()) if not df[col].isnull().all() else None
        stats[f"{col}_max"] = float(df[col].max()) if not df[col].isnull().all() else None
        stats[f"{col}_mean"] = float(df[col].mean()) if not df[col].isnull().all() else None
    return stats


def parse_excel(file_path: str, sheet_name: str | int | None = 0) -> dict:
    """解析Excel文件路径"""
    try:
        engine = "xlrd" if file_path.endswith(".xls") else "openpyxl"
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
        df = _clean_dataframe(df)
        return {
            "success": True,
            "total_rows": len(df),
            "stats": _get_stats(df),
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def parse_excel_bytes(content: bytes, filename: str, sheet_name: str | int | None = 0) -> dict:
    """解析Excel字节内容（用于文件上传场景）"""
    try:
        buffer = BytesIO(content)
        engine = "xlrd" if filename.endswith(".xls") else "openpyxl"
        df = pd.read_excel(buffer, sheet_name=sheet_name, engine=engine)
        df = _clean_dataframe(df)
        return {
            "success": True,
            "filename": filename,
            "total_rows": len(df),
            "stats": _get_stats(df),
            "data": df.fillna("").to_dict(orient="records"),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
