import asyncio
import httpx
from typing import List, Dict, Any, Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)


class AmapServiceError(RuntimeError):
    """Raised when requests to the Amap API fail."""
    pass


AMAP_BASE_URL = "https://restapi.amap.com/v3"
REQUEST_TIMEOUT = 10.0  # 单个请求超时时间（秒）
BATCH_CONCURRENCY = 10  # 批量请求并发数
RETRY_TIMES = 2  # 重试次数


class AmapService:
    def __init__(self):
        self.key = settings.AMAP_KEY
        self._semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def _get(self, url: str, params: Dict[str, Any], retry: int = RETRY_TIMES) -> Dict[str, Any]:
        params["key"] = self.key
        last_error = None
        
        for attempt in range(retry + 1):
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    response = await client.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    # 检查高德 API 返回的状态
                    if data.get("status") == "0":
                        error_info = data.get("info", "Unknown error")
                        logger.warning(f"Amap API error: {error_info}")
                        # 如果是 key 相关错误，不重试
                        if "KEY" in error_info.upper() or "key" in error_info:
                            raise AmapServiceError(f"API key error: {error_info}")
                    
                    return data
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(f"Request timeout (attempt {attempt + 1}/{retry + 1}): {url}")
                if attempt < retry:
                    await asyncio.sleep(0.5 * (attempt + 1))  # 递增延迟
            except httpx.HTTPStatusError as exc:
                raise AmapServiceError(
                    f"Amap responded with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(f"HTTP error (attempt {attempt + 1}/{retry + 1}): {exc}")
                if attempt < retry:
                    await asyncio.sleep(0.5 * (attempt + 1))
        
        raise AmapServiceError(f"Unable to reach Amap service after {retry + 1} attempts") from last_error

    async def geo_code(self, address: str, city: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """地址转经纬度"""
        if not address or not address.strip():
            return None
        
        url = f"{AMAP_BASE_URL}/geocode/geo"
        params = {"address": address.strip()}
        if city and city.strip():
            params["city"] = city.strip()
        
        try:
            data = await self._get(url, params)
            if data.get("status") == "1" and data.get("geocodes"):
                geocodes = data["geocodes"]
                if isinstance(geocodes, list) and len(geocodes) > 0:
                    return geocodes[0]
        except AmapServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in geo_code: {e}")
        return None

    async def regeo_code(self, location: str, extensions: str = "base") -> Optional[Dict[str, Any]]:
        """经纬度转地址 (逆地理编码)
        location: 经度,纬度 (例如: 116.481488,39.990464)
        extensions: base (基本) / all (详细，包含POI、道路等)
        """
        if not location or not location.strip():
            return None
        
        url = f"{AMAP_BASE_URL}/geocode/regeo"
        params = {
            "location": location.strip(),
            "extensions": extensions,
            "radius": 1000,
            "roadlevel": 0
        }
        
        try:
            data = await self._get(url, params)
            if data.get("status") == "1" and data.get("regeocode"):
                return data["regeocode"]
        except AmapServiceError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in regeo_code: {e}")
        return None

    async def _safe_geo_code(self, address: str) -> Optional[Dict[str, Any]]:
        """带限流的安全地理编码"""
        async with self._semaphore:
            try:
                return await self.geo_code(address)
            except AmapServiceError as e:
                logger.warning(f"Geo code failed for '{address[:50]}...': {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for '{address[:50]}...': {e}")
                return None

    async def _safe_regeo_code(self, location: str) -> Optional[Dict[str, Any]]:
        """带限流的安全逆地理编码"""
        async with self._semaphore:
            try:
                if not location:
                    return None
                return await self.regeo_code(location, extensions="all")
            except AmapServiceError as e:
                logger.warning(f"Regeo code failed for '{location}': {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for '{location}': {e}")
                return None

    async def batch_geo_code(self, addresses: List[str]) -> List[Optional[Dict[str, Any]]]:
        """批量地址转经纬度 (并发请求，带限流)"""
        if not addresses:
            return []
        
        tasks = [self._safe_geo_code(addr) for addr in addresses]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Batch geo exception: {r}")
                processed.append(None)
            else:
                processed.append(r)
        return processed

    async def batch_regeo_code(self, locations: List[str]) -> List[Optional[Dict[str, Any]]]:
        """批量经纬度转地址 (并发请求，带限流)"""
        if not locations:
            return []
        
        tasks = [self._safe_regeo_code(loc) for loc in locations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常结果
        processed = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Batch regeo exception: {r}")
                processed.append(None)
            else:
                processed.append(r)
        return processed

amap_service = AmapService()
