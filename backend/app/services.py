import asyncio
import time
import httpx
from typing import List, Dict, Any, Optional
import logging

from .config import settings

logger = logging.getLogger(__name__)


class AmapServiceError(RuntimeError):
    """Raised when requests to the Amap API fail."""

    pass


class AmapRateLimitError(AmapServiceError):
    """Raised when the Amap API rate limit is hit and retries are exhausted."""

    pass


# 高德 API 速率限制相关的 infocode
_RATE_LIMIT_INFOCODES = frozenset({"10003", "10004"})


def _is_rate_limit_error(data: Dict[str, Any]) -> bool:
    """判断高德 API 响应是否为速率限制错误"""
    if data.get("status") != "0":
        return False
    infocode = str(data.get("infocode", ""))
    if infocode in _RATE_LIMIT_INFOCODES:
        return True
    info = data.get("info", "").upper()
    return "LIMIT" in info or "EXCEEDED" in info or "OVER_LIMIT" in info


class _TokenBucket:
    """令牌桶：以固定速率补充令牌，用于控制 API 请求速率。"""

    def __init__(self, rate: float):
        """
        Args:
            rate: 每秒补充的令牌数（即每秒允许的最大请求数）
        """
        self._rate = rate
        self._interval = 1.0 / rate
        self._lock = asyncio.Lock()
        self._last_time: float = 0.0

    async def acquire(self) -> None:
        """等待直到可以发出下一个请求。"""
        async with self._lock:
            now = time.monotonic()
            wait = self._interval - (now - self._last_time)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_time = time.monotonic()


class AmapService:
    """高德地图 API 服务封装"""

    def __init__(self):
        self.key = settings.AMAP_KEY
        self.base_url = settings.AMAP_BASE_URL
        self.timeout = settings.REQUEST_TIMEOUT
        self.retry_times = settings.RETRY_TIMES
        self.rate_limit_retry_times = settings.RATE_LIMIT_RETRY_TIMES
        self.rate_limit_base_delay = settings.RATE_LIMIT_BASE_DELAY
        self._semaphore = asyncio.Semaphore(settings.BATCH_CONCURRENCY)
        self._token_bucket = _TokenBucket(settings.REQUESTS_PER_SECOND)
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """懒初始化并复用 httpx.AsyncClient，避免批量请求时频繁建连。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """释放底层 HTTP 连接，应在应用关闭时调用。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _get(
        self, url: str, params: Dict[str, Any], retry: Optional[int] = None
    ) -> Dict[str, Any]:
        """发送 GET 请求到高德 API，支持重试及速率限制指数退避"""
        if retry is None:
            retry = self.retry_times
        params["key"] = self.key
        last_error = None
        regular_attempts = 0
        rate_limit_attempts = 0

        while regular_attempts <= retry:
            try:
                await self._token_bucket.acquire()
                client = await self._get_client()
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                # 检测速率限制
                if _is_rate_limit_error(data):
                    rate_limit_attempts += 1
                    infocode = data.get("infocode", "")
                    info = data.get("info", "")
                    if rate_limit_attempts > self.rate_limit_retry_times:
                        raise AmapRateLimitError(
                            f"API rate limit exceeded after {rate_limit_attempts} retries "
                            f"(infocode={infocode}, info={info})"
                        )
                    delay = self.rate_limit_base_delay * (
                        2 ** (rate_limit_attempts - 1)
                    )
                    logger.warning(
                        f"Rate limit hit (infocode={infocode}), "
                        f"retry {rate_limit_attempts}/{self.rate_limit_retry_times} "
                        f"after {delay:.1f}s delay: {url}"
                    )
                    await asyncio.sleep(delay)
                    continue

                # 检查其他高德 API 业务错误
                if data.get("status") == "0":
                    error_info = data.get("info", "Unknown error")
                    infocode = data.get("infocode", "")
                    logger.warning(
                        f"Amap API error: infocode={infocode}, info={error_info}"
                    )
                    # KEY 相关错误不重试
                    if "KEY" in error_info.upper() or infocode in ("10001", "10002"):
                        raise AmapServiceError(f"API key error: {error_info}")

                return data

            except AmapRateLimitError:
                raise
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    # HTTP 层速率限制
                    rate_limit_attempts += 1
                    if rate_limit_attempts > self.rate_limit_retry_times:
                        raise AmapRateLimitError(
                            f"HTTP 429 rate limit after {rate_limit_attempts} retries"
                        ) from exc
                    delay = self.rate_limit_base_delay * (
                        2 ** (rate_limit_attempts - 1)
                    )
                    logger.warning(
                        f"HTTP 429 rate limit, retry "
                        f"{rate_limit_attempts}/{self.rate_limit_retry_times} "
                        f"after {delay:.1f}s: {url}"
                    )
                    await asyncio.sleep(delay)
                    continue
                raise AmapServiceError(
                    f"Amap responded with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.TimeoutException as exc:
                last_error = exc
                logger.warning(
                    f"Request timeout (attempt {regular_attempts + 1}/{retry + 1}): {url}"
                )
                regular_attempts += 1
                if regular_attempts <= retry:
                    await asyncio.sleep(0.5 * regular_attempts)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    f"HTTP error (attempt {regular_attempts + 1}/{retry + 1}): {exc}"
                )
                regular_attempts += 1
                if regular_attempts <= retry:
                    await asyncio.sleep(0.5 * regular_attempts)

        raise AmapServiceError(
            f"Unable to reach Amap service after {retry + 1} attempts"
        ) from last_error

    async def geo_code(
        self, address: str, city: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        地址转经纬度 (地理编码)

        Args:
            address: 详细地址
            city: 城市名称（可选，用于提高精度）

        Returns:
            包含经纬度信息的字典，未找到返回 None
        """
        if not address or not address.strip():
            return None

        url = f"{self.base_url}/geocode/geo"
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

    async def regeo_code(
        self, location: str, extensions: str = "base"
    ) -> Optional[Dict[str, Any]]:
        """
        经纬度转地址 (逆地理编码)

        Args:
            location: 经度,纬度 (例如: 116.481488,39.990464)
            extensions: base (基本) / all (详细，包含POI、道路等)

        Returns:
            包含地址信息的字典，未找到返回 None
        """
        if not location or not location.strip():
            return None

        url = f"{self.base_url}/geocode/regeo"
        params = {
            "location": location.strip(),
            "extensions": extensions,
            "radius": 1000,
            "roadlevel": 0,
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
            except AmapRateLimitError as e:
                logger.error(f"Rate limit exhausted for '{address[:50]}': {e}")
                return None
            except AmapServiceError as e:
                logger.warning(f"Geo code failed for '{address[:50]}': {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for '{address[:50]}': {e}")
                return None

    async def _safe_regeo_code(self, location: str) -> Optional[Dict[str, Any]]:
        """带限流的安全逆地理编码"""
        async with self._semaphore:
            try:
                if not location:
                    return None
                return await self.regeo_code(location, extensions="all")
            except AmapRateLimitError as e:
                logger.error(f"Rate limit exhausted for '{location}': {e}")
                return None
            except AmapServiceError as e:
                logger.warning(f"Regeo code failed for '{location}': {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error for '{location}': {e}")
                return None

    async def batch_geo_code(
        self, addresses: List[str]
    ) -> List[Optional[Dict[str, Any]]]:
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

    async def batch_regeo_code(
        self, locations: List[str]
    ) -> List[Optional[Dict[str, Any]]]:
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
