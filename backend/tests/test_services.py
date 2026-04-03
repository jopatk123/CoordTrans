import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import httpx
import time
from app.services import AmapService, AmapServiceError, AmapRateLimitError, _is_rate_limit_error, _TokenBucket


@pytest.fixture
def amap_service():
    """创建 AmapService 实例"""
    service = AmapService()
    service.key = "test_key_12345"
    return service


@pytest.mark.asyncio
async def test_geo_code_success(amap_service):
    """测试地址转经纬度成功"""
    mock_response = {
        "status": "1",
        "geocodes": [
            {
                "location": "116.481488,39.990464",
                "formatted_address": "北京市朝阳区阜通东大街6号",
                "province": "北京市",
                "city": "北京市",
                "district": "朝阳区"
            }
        ]
    }
    
    with patch.object(amap_service, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await amap_service.geo_code("北京市朝阳区阜通东大街6号")
        
        assert result is not None
        assert result["location"] == "116.481488,39.990464"
        assert "formatted_address" in result
        mock_get.assert_called_once()


@pytest.mark.asyncio
async def test_geo_code_not_found(amap_service):
    """测试地址转经纬度找不到结果"""
    mock_response = {
        "status": "1",
        "geocodes": []
    }
    
    with patch.object(amap_service, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await amap_service.geo_code("不存在的地址")
        
        assert result is None


@pytest.mark.asyncio
async def test_regeo_code_success(amap_service):
    """测试经纬度转地址成功"""
    mock_response = {
        "status": "1",
        "regeocode": {
            "formatted_address": "北京市朝阳区阜通东大街6号",
            "addressComponent": {
                "province": "北京市",
                "city": "北京市",
                "district": "朝阳区",
                "township": "望京街道"
            }
        }
    }
    
    with patch.object(amap_service, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await amap_service.regeo_code("116.481488,39.990464")
        
        assert result is not None
        assert result["formatted_address"] == "北京市朝阳区阜通东大街6号"
        assert "addressComponent" in result


@pytest.mark.asyncio
async def test_regeo_code_with_extensions(amap_service):
    """测试带扩展参数的经纬度转地址"""
    mock_response = {
        "status": "1",
        "regeocode": {
            "formatted_address": "北京市朝阳区阜通东大街6号",
            "addressComponent": {
                "township": "望京街道"
            },
            "pois": []
        }
    }
    
    with patch.object(amap_service, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response
        
        result = await amap_service.regeo_code("116.481488,39.990464", extensions="all")
        
        assert result is not None
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        params = call_args[0][1]
        assert params["extensions"] == "all"


@pytest.mark.asyncio
async def test_batch_geo_code(amap_service):
    """测试批量地址转经纬度"""
    addresses = ["北京市朝阳区", "上海市浦东新区", "广州市天河区"]
    
    mock_results = [
        {"location": "116.443108,39.921489", "formatted_address": "北京市朝阳区"},
        {"location": "121.544379,31.221517", "formatted_address": "上海市浦东新区"},
        {"location": "113.324520,23.155950", "formatted_address": "广州市天河区"}
    ]
    
    with patch.object(amap_service, "geo_code", new_callable=AsyncMock) as mock_geo:
        mock_geo.side_effect = mock_results
        
        results = await amap_service.batch_geo_code(addresses)
        
        assert len(results) == 3
        assert results[0]["location"] == "116.443108,39.921489"
        assert mock_geo.call_count == 3


@pytest.mark.asyncio
async def test_batch_regeo_code(amap_service):
    """测试批量经纬度转地址"""
    locations = ["116.481488,39.990464", "121.544379,31.221517"]
    
    mock_results = [
        {"formatted_address": "北京市朝阳区阜通东大街6号"},
        {"formatted_address": "上海市浦东新区"}
    ]
    
    with patch.object(amap_service, "regeo_code", new_callable=AsyncMock) as mock_regeo:
        mock_regeo.side_effect = mock_results
        
        results = await amap_service.batch_regeo_code(locations)
        
        assert len(results) == 2
        assert results[0]["formatted_address"] == "北京市朝阳区阜通东大街6号"
        assert mock_regeo.call_count == 2


@pytest.mark.asyncio
async def test_api_error_handling(amap_service):
    """测试API错误处理"""
    with patch.object(amap_service, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = AmapServiceError("API Error")
        
        with pytest.raises(AmapServiceError):
            await amap_service.geo_code("测试地址")


# ========== 速率限制相关测试 ==========

def test_is_rate_limit_error_infocode_10003():
    """infocode 10003 应识别为速率限制"""
    data = {"status": "0", "infocode": "10003", "info": "DAILY_QUERY_OVER_LIMIT"}
    assert _is_rate_limit_error(data) is True


def test_is_rate_limit_error_infocode_10004():
    """infocode 10004 应识别为速率限制"""
    data = {"status": "0", "infocode": "10004", "info": "CUQPS_HAS_EXCEEDED_THE_LIMIT"}
    assert _is_rate_limit_error(data) is True


def test_is_rate_limit_error_info_keyword():
    """info 字段含 LIMIT 关键字应识别为速率限制"""
    data = {"status": "0", "infocode": "99999", "info": "OVER_LIMIT"}
    assert _is_rate_limit_error(data) is True


def test_is_rate_limit_error_not_a_rate_limit():
    """KEY 错误不是速率限制"""
    data = {"status": "0", "infocode": "10001", "info": "INVALID_USER_KEY"}
    assert _is_rate_limit_error(data) is False


def test_is_rate_limit_error_success_response():
    """成功响应不是速率限制"""
    data = {"status": "1", "infocode": "10000", "info": "OK"}
    assert _is_rate_limit_error(data) is False


@pytest.mark.asyncio
async def test_get_retries_on_rate_limit(amap_service):
    """触发速率限制时应进行指数退避重试，最终成功"""
    amap_service.rate_limit_retry_times = 2
    amap_service.rate_limit_base_delay = 0.01  # 测试中缩短延迟

    rate_limit_response = {"status": "0", "infocode": "10004", "info": "CUQPS_HAS_EXCEEDED_THE_LIMIT"}
    success_response = {"status": "1", "geocodes": [{"location": "116.48,39.99"}]}

    call_count = 0

    async def fake_get(url, params=None, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if call_count < 3:
            resp.json = MagicMock(return_value=rate_limit_response)
        else:
            resp.json = MagicMock(return_value=success_response)
        return resp

    mock_client = AsyncMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await amap_service._get(f"{amap_service.base_url}/geocode/geo", {"address": "test"})
    assert data["status"] == "1"
    assert call_count == 3


@pytest.mark.asyncio
async def test_get_raises_rate_limit_error_when_exhausted(amap_service):
    """速率限制重试次数耗尽后应抛出 AmapRateLimitError"""
    amap_service.rate_limit_retry_times = 2
    amap_service.rate_limit_base_delay = 0.01

    rate_limit_response = {"status": "0", "infocode": "10004", "info": "CUQPS_HAS_EXCEEDED_THE_LIMIT"}

    async def fake_get(url, params=None, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=rate_limit_response)
        return resp

    mock_client = AsyncMock()
    mock_client.get = fake_get
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(AmapRateLimitError):
            await amap_service._get(f"{amap_service.base_url}/geocode/geo", {"address": "test"})


@pytest.mark.asyncio
async def test_safe_geo_code_handles_rate_limit_error(amap_service):
    """_safe_geo_code 在速率限制耗尽后应返回 None 而不是抛出异常"""
    with patch.object(amap_service, "geo_code", new_callable=AsyncMock) as mock_geo:
        mock_geo.side_effect = AmapRateLimitError("rate limit exhausted")
        result = await amap_service._safe_geo_code("测试地址")
    assert result is None


@pytest.mark.asyncio
async def test_safe_regeo_code_handles_rate_limit_error(amap_service):
    """_safe_regeo_code 在速率限制耗尽后应返回 None 而不是抛出异常"""
    with patch.object(amap_service, "regeo_code", new_callable=AsyncMock) as mock_regeo:
        mock_regeo.side_effect = AmapRateLimitError("rate limit exhausted")
        result = await amap_service._safe_regeo_code("116.48,39.99")
    assert result is None


# ========== 令牌桶速率限制测试 ==========

@pytest.mark.asyncio
async def test_token_bucket_rate():
    """令牌桶应以不低于设定间隔发放令牌"""
    bucket = _TokenBucket(rate=10.0)  # 10/s => 间隔 0.1s
    n = 4
    timestamps = []
    for _ in range(n):
        await bucket.acquire()
        timestamps.append(time.monotonic())

    # 相邻两次调用间隔应 >= 0.1s（允许 10ms 误差）
    for i in range(1, n):
        interval = timestamps[i] - timestamps[i - 1]
        assert interval >= 0.09, f"间隔过短: {interval:.4f}s"


@pytest.mark.asyncio
async def test_token_bucket_concurrent_serialized():
    """并发 acquire 应被串行化，总耗时约等于 (n-1) * interval"""
    rate = 20.0  # 20/s => 间隔 0.05s
    n = 5
    bucket = _TokenBucket(rate=rate)
    start = time.monotonic()
    await asyncio.gather(*[bucket.acquire() for _ in range(n)])
    elapsed = time.monotonic() - start
    expected_min = (n - 1) / rate
    assert elapsed >= expected_min * 0.8, f"耗时 {elapsed:.3f}s 远小于预期 {expected_min:.3f}s"


@pytest.mark.asyncio
async def test_amap_service_uses_token_bucket(amap_service):
    """AmapService 应持有令牌桶实例"""
    assert hasattr(amap_service, "_token_bucket")
    assert isinstance(amap_service._token_bucket, _TokenBucket)
