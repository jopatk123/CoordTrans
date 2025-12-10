import logging
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional
import pandas as pd
import io
from fastapi.responses import StreamingResponse
from .services import amap_service, AmapServiceError

router = APIRouter()
logger = logging.getLogger(__name__)

# 常量定义
MAX_BATCH_SIZE = 1000
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_ADDRESS_LENGTH = 200
MAX_CITY_LENGTH = 50

class GeoRequest(BaseModel):
    address: str
    city: Optional[str] = None

    @field_validator("address")
    @classmethod
    def address_must_not_be_blank(cls, value: str) -> str:
        if value is None:
            raise ValueError("address is required")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("address must not be empty")
        if len(cleaned) < 2:
            raise ValueError("address must be at least 2 characters")
        if len(cleaned) > MAX_ADDRESS_LENGTH:
            raise ValueError(f"address must not exceed {MAX_ADDRESS_LENGTH} characters")
        # 移除潜在的危险字符
        cleaned = re.sub(r'[<>"\';]', '', cleaned)
        return cleaned

    @field_validator("city")
    @classmethod
    def city_must_be_valid(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > MAX_CITY_LENGTH:
            raise ValueError(f"city must not exceed {MAX_CITY_LENGTH} characters")
        # 移除潜在的危险字符
        cleaned = re.sub(r'[<>"\';]', '', cleaned)
        return cleaned

class RegeoRequest(BaseModel):
    location: str  # lon,lat

    @field_validator("location")
    @classmethod
    def location_must_be_valid(cls, value: str) -> str:
        if value is None:
            raise ValueError("location is required")
        value = value.strip()
        if not value:
            raise ValueError("location must not be empty")
        
        parts = [part.strip() for part in value.split(",") if part.strip()]
        if len(parts) != 2:
            raise ValueError("location must be in 'longitude,latitude' format")
        
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError as exc:
            raise ValueError("longitude and latitude must be numbers") from exc
        
        # 验证经纬度范围
        if not (-180 <= lon <= 180):
            raise ValueError("longitude must be between -180 and 180")
        if not (-90 <= lat <= 90):
            raise ValueError("latitude must be between -90 and 90")
        
        return f"{lon},{lat}"

@router.post("/geo")
async def geocode(req: GeoRequest):
    try:
        result = await amap_service.geo_code(req.address, req.city)
    except AmapServiceError as exc:
        logger.warning("Amap geocode failed: %s", exc)
        raise HTTPException(status_code=502, detail="Geocoding provider unavailable") from exc
    if not result:
        return {"status": "failed", "msg": "Not found"}
    return {"status": "success", "data": result}

@router.post("/regeo")
async def regeocode(req: RegeoRequest):
    try:
        result = await amap_service.regeo_code(req.location, extensions="all")
    except AmapServiceError as exc:
        logger.warning("Amap regeo failed: %s", exc)
        raise HTTPException(status_code=502, detail="Geocoding provider unavailable") from exc
    if not result:
        return {"status": "failed", "msg": "Not found"}
    return {"status": "success", "data": result}

@router.post("/batch/file/geo")
async def batch_file_geo(file: UploadFile = File(...)):
    # 验证文件名
    if not file.filename:
        raise HTTPException(400, "文件名无效")
    
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in ['.csv', '.xls', '.xlsx']):
        raise HTTPException(400, "不支持的文件格式，请上传 CSV 或 Excel 文件")
    
    # 读取文件内容并检查大小
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "文件为空")
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大，最大支持 {MAX_FILE_SIZE // (1024*1024)}MB")
    
    try:
        if filename_lower.endswith('.csv'):
            # 尝试多种编码
            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(400, "无法解析文件编码，请使用 UTF-8 编码")
        else:  # Excel files
            df = pd.read_excel(io.BytesIO(contents))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(400, f"读取文件失败: {str(e)[:100]}")
    
    # 验证数据框
    if df.empty:
        raise HTTPException(400, "文件内容为空")
    if len(df.columns) == 0:
        raise HTTPException(400, "文件没有有效列")
    
    # Find address column
    target_col = None
    for col in df.columns:
        col_str = str(col).lower()
        if "address" in col_str or "地址" in col_str:
            target_col = col
            break
    if target_col is None:
        target_col = df.columns[0]  # Default to first column
        logger.info(f"No address column found, using first column: {target_col}")

    # 清理和过滤地址
    addresses = []
    for val in df[target_col].tolist():
        if pd.isna(val) or val is None:
            addresses.append('')
        else:
            addr = str(val).strip()[:MAX_ADDRESS_LENGTH]
            addresses.append(addr)
    
    # Limit batch size for safety
    if len(addresses) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"数据行数超出限制，最多支持 {MAX_BATCH_SIZE} 行")

    try:
        results = await amap_service.batch_geo_code(addresses)
    except AmapServiceError as exc:
        logger.warning("Amap batch geo failed: %s", exc)
        raise HTTPException(status_code=502, detail="Geocoding provider unavailable") from exc
    
    lons, lats, formatted_addresses, provinces, cities, districts = [], [], [], [], [], []
    
    for res in results:
        if res:
            loc = res.get('location', ',').split(',')
            lons.append(loc[0] if len(loc) > 0 else '')
            lats.append(loc[1] if len(loc) > 1 else '')
            formatted_addresses.append(res.get('formatted_address', ''))
            provinces.append(res.get('province', ''))
            cities.append(res.get('city', ''))
            districts.append(res.get('district', ''))
        else:
            lons.append('')
            lats.append('')
            formatted_addresses.append('')
            provinces.append('')
            cities.append('')
            districts.append('')
            
    df['api_longitude'] = lons
    df['api_latitude'] = lats
    df['api_formatted_address'] = formatted_addresses
    df['api_province'] = provinces
    df['api_city'] = cities
    df['api_district'] = districts
    
    output = io.BytesIO()
    # Default to Excel for output
    df.to_excel(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=processed_geocoding.xlsx"}
    )

@router.post("/batch/file/regeo")
async def batch_file_regeo(file: UploadFile = File(...)):
    # 验证文件名
    if not file.filename:
        raise HTTPException(400, "文件名无效")
    
    filename_lower = file.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in ['.csv', '.xls', '.xlsx']):
        raise HTTPException(400, "不支持的文件格式，请上传 CSV 或 Excel 文件")
    
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(400, "文件为空")
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"文件过大，最大支持 {MAX_FILE_SIZE // (1024*1024)}MB")
    
    try:
        if filename_lower.endswith('.csv'):
            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin1']:
                try:
                    df = pd.read_csv(io.BytesIO(contents), encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise HTTPException(400, "无法解析文件编码，请使用 UTF-8 编码")
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(400, f"读取文件失败: {str(e)[:100]}")
    
    if df.empty:
        raise HTTPException(400, "文件内容为空")

    # Find lat/lon columns
    lat_col, lon_col = None, None
    for col in df.columns:
        c = str(col).lower()
        if "lat" in c or "纬度" in c:
            lat_col = col
        if "lon" in c or "lng" in c or "经度" in c:
            lon_col = col
    
    if not lat_col or not lon_col:
        # Try first two columns
        if len(df.columns) >= 2:
            lon_col, lat_col = df.columns[0], df.columns[1]
            logger.info(f"No lat/lon columns found, using first two columns: {lon_col}, {lat_col}")
        else:
            raise HTTPException(400, "无法识别经纬度列，请确保文件包含'经度'和'纬度'列")

    locations = []
    invalid_count = 0
    for idx, row in df.iterrows():
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
        raise HTTPException(400, "所有经纬度数据无效，请检查文件格式")

    if len(locations) > MAX_BATCH_SIZE:
        raise HTTPException(400, f"数据行数超出限制，最多支持 {MAX_BATCH_SIZE} 行")

    try:
        results = await amap_service.batch_regeo_code(locations)
    except AmapServiceError as exc:
        logger.warning("Amap batch regeo failed: %s", exc)
        raise HTTPException(status_code=502, detail="Geocoding provider unavailable") from exc
    
    addrs = []
    townships = []
    
    for res in results:
        if res:
            addrs.append(res.get('formatted_address', ''))
            addr_comp = res.get('addressComponent', {})
            townships.append(addr_comp.get('township', ''))
        else:
            addrs.append('')
            townships.append('')
            
    df['api_address'] = addrs
    df['api_township'] = townships
    
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        output, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=processed_regeocoding.xlsx"}
    )
