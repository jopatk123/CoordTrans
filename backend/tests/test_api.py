import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import io


def test_health_check(client):
    """测试健康检查接口"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_geocode_success(client, mock_amap_key):
    """测试地址转经纬度成功的情况"""
    mock_result = {
        "location": "116.481488,39.990464",
        "formatted_address": "北京市朝阳区阜通东大街6号",
        "province": "北京市",
        "city": "北京市",
        "district": "朝阳区"
    }
    
    with patch("app.services.amap_service.geo_code", new_callable=AsyncMock) as mock_geo:
        mock_geo.return_value = mock_result
        
        response = client.post("/api/geo", json={
            "address": "北京市朝阳区阜通东大街6号"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "location" in data["data"]


@pytest.mark.asyncio
async def test_geocode_not_found(client, mock_amap_key):
    """测试地址转经纬度找不到的情况"""
    with patch("app.services.amap_service.geo_code", new_callable=AsyncMock) as mock_geo:
        mock_geo.return_value = None
        
        response = client.post("/api/geo", json={
            "address": "不存在的地址123456"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"


@pytest.mark.asyncio
async def test_regeocode_success(client, mock_amap_key):
    """测试经纬度转地址成功的情况"""
    mock_result = {
        "formatted_address": "北京市朝阳区阜通东大街6号",
        "addressComponent": {
            "province": "北京市",
            "city": "北京市",
            "district": "朝阳区",
            "township": "望京街道"
        }
    }
    
    with patch("app.services.amap_service.regeo_code", new_callable=AsyncMock) as mock_regeo:
        mock_regeo.return_value = mock_result
        
        response = client.post("/api/regeo", json={
            "location": "116.481488,39.990464"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "formatted_address" in data["data"]


def test_geocode_missing_address(client):
    """测试缺少必要参数的情况"""
    response = client.post("/api/geo", json={})
    assert response.status_code == 422  # Validation error


def test_geocode_blank_address(client):
    """测试空白地址参数"""
    response = client.post("/api/geo", json={"address": "   "})
    assert response.status_code == 422


def test_regeocode_invalid_location_format(client):
    """测试非法经纬度格式"""
    response = client.post("/api/regeo", json={"location": "abc"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_file_geo_excel(client, mock_amap_key):
    """测试批量文件地址转经纬度（Excel格式）"""
    import pandas as pd
    
    # 创建测试数据
    df = pd.DataFrame({
        "地址": ["北京市朝阳区", "上海市浦东新区"]
    })
    
    # 转换为Excel字节流
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    
    mock_results = [
        {
            "location": "116.443108,39.921489",
            "formatted_address": "北京市朝阳区",
            "province": "北京市",
            "city": "北京市",
            "district": "朝阳区"
        },
        {
            "location": "121.544379,31.221517",
            "formatted_address": "上海市浦东新区",
            "province": "上海市",
            "city": "上海市",
            "district": "浦东新区"
        }
    ]
    
    with patch("app.services.amap_service.batch_geo_code", new_callable=AsyncMock) as mock_batch:
        mock_batch.return_value = mock_results
        
        response = client.post(
            "/api/batch/file/geo",
            files={"file": ("test.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


    @pytest.mark.asyncio
    async def test_batch_file_regeo_excel(client, mock_amap_key):
        """测试批量文件经纬度转地址（Excel格式）"""
        import pandas as pd

        df = pd.DataFrame({
            "经度": [116.481488, 121.544379],
            "纬度": [39.990464, 31.221517]
        })

        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)

        mock_results = [
            {
                "formatted_address": "北京市朝阳区阜通东大街6号",
                "addressComponent": {"township": "望京街道"}
            },
            {
                "formatted_address": "上海市浦东新区",
                "addressComponent": {"township": "花木街道"}
            }
        ]

        with patch("app.services.amap_service.batch_regeo_code", new_callable=AsyncMock) as mock_batch:
            mock_batch.return_value = mock_results

            response = client.post(
                "/api/batch/file/regeo",
                files={"file": ("regeo.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )

            assert response.status_code == 200
            assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_batch_file_unsupported_format(client):
    """测试上传不支持的文件格式"""
    buffer = io.BytesIO(b"some text content")
    
    response = client.post(
        "/api/batch/file/geo",
        files={"file": ("test.txt", buffer, "text/plain")}
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_batch_file_size_limit(client, mock_amap_key):
    """测试批量处理数量限制"""
    import pandas as pd
    
    # 创建超过1000条的数据
    df = pd.DataFrame({
        "地址": [f"地址{i}" for i in range(1001)]
    })
    
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    
    response = client.post(
        "/api/batch/file/geo",
        files={"file": ("test.xlsx", buffer, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    
    assert response.status_code == 400
