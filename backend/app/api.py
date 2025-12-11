"""API 路由定义模块"""
import logging
import re
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional

from .config import settings
from .services import amap_service, AmapServiceError
from .errors import ApiResponse
from .utils import (
    read_upload_file,
    find_address_column,
    find_location_columns,
    extract_addresses,
    extract_locations,
    create_excel_response,
    process_geo_results,
    process_regeo_results,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ========== 请求模型定义 ==========

class GeoRequest(BaseModel):
    """地址转经纬度请求模型"""
    address: str = Field(
        ..., 
        min_length=2,
        max_length=settings.MAX_ADDRESS_LENGTH,
        description="详细地址",
        json_schema_extra={"example": "北京市朝阳区阜通东大街6号"}
    )
    city: Optional[str] = Field(
        default=None,
        max_length=settings.MAX_CITY_LENGTH,
        description="城市名称（可选，用于提高精度）",
        json_schema_extra={"example": "北京"}
    )

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: str) -> str:
        if value is None:
            raise ValueError("address is required")
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("address must not be empty")
        if len(cleaned) < 2:
            raise ValueError("address must be at least 2 characters")
        if len(cleaned) > settings.MAX_ADDRESS_LENGTH:
            raise ValueError(f"address must not exceed {settings.MAX_ADDRESS_LENGTH} characters")
        # 移除潜在的危险字符
        cleaned = re.sub(r'[<>"\';]', '', cleaned)
        return cleaned

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > settings.MAX_CITY_LENGTH:
            raise ValueError(f"city must not exceed {settings.MAX_CITY_LENGTH} characters")
        # 移除潜在的危险字符
        cleaned = re.sub(r'[<>"\';]', '', cleaned)
        return cleaned


class RegeoRequest(BaseModel):
    """经纬度转地址请求模型"""
    location: str = Field(
        ..., 
        description="经纬度坐标，格式: 经度,纬度",
        json_schema_extra={"example": "116.481488,39.990464"}
    )

    @field_validator("location")
    @classmethod
    def validate_location(cls, value: str) -> str:
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


# ========== 单条查询接口 ==========

@router.post(
    "/geo",
    tags=["geocoding"],
    summary="地址转经纬度",
    description="输入详细地址，返回经纬度坐标及详细地址信息"
)
async def geocode(req: GeoRequest):
    """
    地址转经纬度 (Geocoding)
    
    - **address**: 详细地址，如 "北京市朝阳区阜通东大街6号"
    - **city**: 城市名称（可选），提供后可提高精度
    
    返回包含经纬度、省市区等详细信息的结果。
    """
    try:
        result = await amap_service.geo_code(req.address, req.city)
    except AmapServiceError as exc:
        logger.warning("Amap geocode failed: %s", exc)
        raise HTTPException(status_code=502, detail="地图服务暂时不可用") from exc
    
    if not result:
        return ApiResponse.not_found("未找到该地址对应的坐标")
    return ApiResponse.success(data=result)


@router.post(
    "/regeo",
    tags=["geocoding"],
    summary="经纬度转地址",
    description="输入经纬度坐标，返回详细地址信息"
)
async def regeocode(req: RegeoRequest):
    """
    经纬度转地址 (Reverse Geocoding)
    
    - **location**: 经纬度坐标，格式为 "经度,纬度"，如 "116.481488,39.990464"
    
    返回包含详细地址、行政区划、街道等信息的结果。
    """
    try:
        result = await amap_service.regeo_code(req.location, extensions="all")
    except AmapServiceError as exc:
        logger.warning("Amap regeo failed: %s", exc)
        raise HTTPException(status_code=502, detail="地图服务暂时不可用") from exc
    
    if not result:
        return ApiResponse.not_found("未找到该坐标对应的地址")
    return ApiResponse.success(data=result)


# ========== 批量处理接口 ==========

@router.post(
    "/batch/file/geo",
    tags=["batch"],
    summary="批量地址转经纬度",
    description="上传包含地址列的 Excel/CSV 文件，批量转换为经纬度"
)
async def batch_file_geo(
    file: UploadFile = File(..., description="Excel 或 CSV 文件，需包含地址列")
):
    """
    批量地址转经纬度
    
    上传 Excel (.xlsx, .xls) 或 CSV 文件，系统会自动识别包含"地址"或"address"的列。
    如未找到，默认使用第一列作为地址列。
    
    **文件要求:**
    - 支持格式: .xlsx, .xls, .csv
    - 最大文件大小: 10MB
    - 最大行数: 1000 行
    
    **返回:**
    处理后的 Excel 文件，包含原始数据及新增的经纬度、省市区等列。
    """
    # 读取并验证文件
    df, _ = await read_upload_file(file)
    
    # 查找地址列
    target_col = find_address_column(df)
    
    # 提取地址列表
    addresses = extract_addresses(df, target_col, settings.MAX_ADDRESS_LENGTH)
    
    # 验证批量大小
    if len(addresses) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"数据行数超出限制，最多支持 {settings.MAX_BATCH_SIZE} 行"
        )

    # 调用批量转换服务
    try:
        results = await amap_service.batch_geo_code(addresses)
    except AmapServiceError as exc:
        logger.warning("Amap batch geo failed: %s", exc)
        raise HTTPException(status_code=502, detail="地图服务暂时不可用") from exc
    
    # 处理结果并添加到 DataFrame
    geo_data = process_geo_results(results)
    df['api_longitude'] = geo_data['longitude']
    df['api_latitude'] = geo_data['latitude']
    df['api_formatted_address'] = geo_data['formatted_address']
    df['api_province'] = geo_data['province']
    df['api_city'] = geo_data['city']
    df['api_district'] = geo_data['district']
    
    # 返回 Excel 文件
    return create_excel_response(df, "processed_geocoding.xlsx")


@router.post(
    "/batch/file/regeo",
    tags=["batch"],
    summary="批量经纬度转地址",
    description="上传包含经纬度列的 Excel/CSV 文件，批量转换为地址"
)
async def batch_file_regeo(
    file: UploadFile = File(..., description="Excel 或 CSV 文件，需包含经度和纬度列")
):
    """
    批量经纬度转地址
    
    上传 Excel (.xlsx, .xls) 或 CSV 文件，系统会自动识别经度和纬度列。
    支持的列名: 经度/lon/lng, 纬度/lat
    如未找到，默认使用前两列。
    
    **文件要求:**
    - 支持格式: .xlsx, .xls, .csv
    - 最大文件大小: 10MB
    - 最大行数: 1000 行
    
    **返回:**
    处理后的 Excel 文件，包含原始数据及新增的地址、街道等列。
    """
    # 读取并验证文件
    df, _ = await read_upload_file(file)
    
    # 查找经纬度列
    lon_col, lat_col = find_location_columns(df)
    
    # 提取经纬度列表
    locations, invalid_count = extract_locations(df, lon_col, lat_col)
    
    # 验证批量大小
    if len(locations) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"数据行数超出限制，最多支持 {settings.MAX_BATCH_SIZE} 行"
        )

    # 调用批量转换服务
    try:
        results = await amap_service.batch_regeo_code(locations)
    except AmapServiceError as exc:
        logger.warning("Amap batch regeo failed: %s", exc)
        raise HTTPException(status_code=502, detail="地图服务暂时不可用") from exc
    
    # 处理结果并添加到 DataFrame
    regeo_data = process_regeo_results(results)
    df['api_address'] = regeo_data['address']
    df['api_township'] = regeo_data['township']
    
    # 返回 Excel 文件
    return create_excel_response(df, "processed_regeocoding.xlsx")
