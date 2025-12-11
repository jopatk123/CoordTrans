"""通用工具函数模块 - 提取重复代码"""
import io
import logging
from typing import Tuple, List, Optional, Any
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import pandas as pd

from .config import settings

logger = logging.getLogger(__name__)

# 支持的文件扩展名
ALLOWED_EXTENSIONS = ['.csv', '.xls', '.xlsx']
# 支持的编码列表
SUPPORTED_ENCODINGS = ['utf-8', 'gbk', 'gb2312', 'latin1']


async def read_upload_file(file: UploadFile) -> Tuple[pd.DataFrame, bytes]:
    """
    读取上传的文件并返回 DataFrame
    
    Args:
        file: 上传的文件对象
        
    Returns:
        Tuple[DataFrame, bytes]: 解析后的 DataFrame 和原始内容
        
    Raises:
        HTTPException: 文件验证或解析失败时抛出
    """
    # 验证文件名
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名无效")
    
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400, 
            detail="不支持的文件格式，请上传 CSV 或 Excel 文件"
        )
    
    # 读取文件内容并检查大小
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(contents) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"文件过大，最大支持 {settings.MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # 解析文件
    try:
        if filename_lower.endswith('.csv'):
            df = _read_csv_with_encoding(contents)
        else:  # Excel files
            df = pd.read_excel(io.BytesIO(contents))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"读取文件失败: {str(e)[:100]}"
        )
    
    # 验证数据框
    if df.empty:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(df.columns) == 0:
        raise HTTPException(status_code=400, detail="文件没有有效列")
    
    return df, contents


def _read_csv_with_encoding(contents: bytes) -> pd.DataFrame:
    """
    尝试多种编码读取 CSV 文件
    
    Args:
        contents: 文件内容字节
        
    Returns:
        DataFrame: 解析后的数据框
        
    Raises:
        HTTPException: 所有编码都失败时抛出
    """
    for encoding in SUPPORTED_ENCODINGS:
        try:
            return pd.read_csv(io.BytesIO(contents), encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(
        status_code=400, 
        detail="无法解析文件编码，请使用 UTF-8 编码"
    )


def find_address_column(df: pd.DataFrame) -> str:
    """
    在 DataFrame 中查找地址列
    
    Args:
        df: 数据框
        
    Returns:
        str: 地址列名
    """
    for col in df.columns:
        col_str = str(col).lower()
        if "address" in col_str or "地址" in col_str:
            return col
    # 默认使用第一列
    logger.info(f"No address column found, using first column: {df.columns[0]}")
    return df.columns[0]


def find_location_columns(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """
    在 DataFrame 中查找经纬度列
    
    Args:
        df: 数据框
        
    Returns:
        Tuple[Optional[str], Optional[str]]: (经度列名, 纬度列名)
        
    Raises:
        HTTPException: 无法识别列时抛出
    """
    lat_col, lon_col = None, None
    
    for col in df.columns:
        c = str(col).lower()
        if "lat" in c or "纬度" in c:
            lat_col = col
        if "lon" in c or "lng" in c or "经度" in c:
            lon_col = col
    
    if not lat_col or not lon_col:
        # 尝试使用前两列
        if len(df.columns) >= 2:
            lon_col, lat_col = df.columns[0], df.columns[1]
            logger.info(
                f"No lat/lon columns found, using first two columns: {lon_col}, {lat_col}"
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail="无法识别经纬度列，请确保文件包含'经度'和'纬度'列"
            )
    
    return lon_col, lat_col


def extract_addresses(
    df: pd.DataFrame, 
    column: str, 
    max_length: int
) -> List[str]:
    """
    从 DataFrame 中提取并清理地址列表
    
    Args:
        df: 数据框
        column: 地址列名
        max_length: 地址最大长度
        
    Returns:
        List[str]: 清理后的地址列表
    """
    addresses = []
    for val in df[column].tolist():
        if pd.isna(val) or val is None:
            addresses.append('')
        else:
            addr = str(val).strip()[:max_length]
            addresses.append(addr)
    return addresses


def extract_locations(
    df: pd.DataFrame, 
    lon_col: str, 
    lat_col: str
) -> Tuple[List[str], int]:
    """
    从 DataFrame 中提取并验证经纬度列表
    
    Args:
        df: 数据框
        lon_col: 经度列名
        lat_col: 纬度列名
        
    Returns:
        Tuple[List[str], int]: (经纬度字符串列表, 无效数据计数)
        
    Raises:
        HTTPException: 所有数据都无效时抛出
    """
    locations = []
    invalid_count = 0
    
    for _, row in df.iterrows():
        try:
            lon_val = row[lon_col]
            lat_val = row[lat_col]
            
            # 处理空值
            if pd.isna(lon_val) or pd.isna(lat_val):
                locations.append('')
                invalid_count += 1
                continue
            
            lon = float(lon_val)
            lat = float(lat_val)
            
            # 验证范围
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                locations.append('')
                invalid_count += 1
                continue
                
            locations.append(f"{lon},{lat}")
        except (ValueError, TypeError):
            locations.append('')
            invalid_count += 1
    
    if invalid_count > 0:
        logger.warning(f"Found {invalid_count} invalid location entries")
    
    if all(loc == '' for loc in locations):
        raise HTTPException(
            status_code=400, 
            detail="所有经纬度数据无效，请检查文件格式"
        )
    
    return locations, invalid_count


def create_excel_response(
    df: pd.DataFrame, 
    filename: str
) -> StreamingResponse:
    """
    创建 Excel 文件下载响应
    
    Args:
        df: 数据框
        filename: 下载文件名
        
    Returns:
        StreamingResponse: 文件流响应
    """
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


def process_geo_results(results: List[Optional[dict]]) -> dict:
    """
    处理地理编码结果，提取所需字段
    
    Args:
        results: API 返回的结果列表
        
    Returns:
        dict: 包含各字段列表的字典
    """
    data = {
        'longitude': [],
        'latitude': [],
        'formatted_address': [],
        'province': [],
        'city': [],
        'district': []
    }
    
    for res in results:
        if res:
            loc = res.get('location', ',').split(',')
            data['longitude'].append(loc[0] if len(loc) > 0 else '')
            data['latitude'].append(loc[1] if len(loc) > 1 else '')
            data['formatted_address'].append(res.get('formatted_address', ''))
            data['province'].append(res.get('province', ''))
            data['city'].append(res.get('city', ''))
            data['district'].append(res.get('district', ''))
        else:
            for key in data:
                data[key].append('')
    
    return data


def process_regeo_results(results: List[Optional[dict]]) -> dict:
    """
    处理逆地理编码结果，提取所需字段
    
    Args:
        results: API 返回的结果列表
        
    Returns:
        dict: 包含各字段列表的字典
    """
    data = {
        'address': [],
        'township': []
    }
    
    for res in results:
        if res:
            data['address'].append(res.get('formatted_address', ''))
            addr_comp = res.get('addressComponent', {})
            data['township'].append(addr_comp.get('township', ''))
        else:
            data['address'].append('')
            data['township'].append('')
    
    return data
