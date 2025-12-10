import pytest
from unittest.mock import AsyncMock, patch
from app.services import AmapService


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
    import httpx
    
    with patch.object(amap_service, "_get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("API Error")
        
        with pytest.raises(httpx.HTTPError):
            await amap_service.geo_code("测试地址")
