import asyncio
import httpx
from typing import List, Dict, Any

from .config import settings


class AmapServiceError(RuntimeError):
    """Raised when requests to the Amap API fail."""
    pass

AMAP_BASE_URL = "https://restapi.amap.com/v3"

class AmapService:
    def __init__(self):
        self.key = settings.AMAP_KEY

    async def _get(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        params["key"] = self.key
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            raise AmapServiceError(
                f"Amap responded with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise AmapServiceError("Unable to reach Amap geocoding service") from exc

    async def geo_code(self, address: str, city: str = None) -> Dict[str, Any]:
        """地址转经纬度"""
        url = f"{AMAP_BASE_URL}/geocode/geo"
        params = {"address": address}
        if city:
            params["city"] = city
        
        data = await self._get(url, params)
        if data.get("status") == "1" and data.get("geocodes"):
            return data["geocodes"][0]
        return None

    async def regeo_code(self, location: str, extensions: str = "base") -> Dict[str, Any]:
        """经纬度转地址 (逆地理编码)
        location: 经度,纬度 (例如: 116.481488,39.990464)
        extensions: base (基本) / all (详细，包含POI、道路等)
        """
        url = f"{AMAP_BASE_URL}/geocode/regeo"
        params = {
            "location": location,
            "extensions": extensions,
            "radius": 1000,
            "roadlevel": 0
        }
        
        data = await self._get(url, params)
        if data.get("status") == "1" and data.get("regeocode"):
            return data["regeocode"]
        return None

    async def batch_geo_code(self, addresses: List[str]) -> List[Dict[str, Any]]:
        """批量地址转经纬度 (并发请求)"""
        tasks = [self.geo_code(addr) for addr in addresses]
        return await asyncio.gather(*tasks)

    async def batch_regeo_code(self, locations: List[str]) -> List[Dict[str, Any]]:
        """批量经纬度转地址 (并发请求)"""
        tasks = [self.regeo_code(loc, extensions="all") for loc in locations]
        return await asyncio.gather(*tasks)

amap_service = AmapService()
