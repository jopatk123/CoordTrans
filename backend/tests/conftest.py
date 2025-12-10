import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_amap_key(monkeypatch):
    """模拟高德地图 API Key"""
    monkeypatch.setattr(settings, "AMAP_KEY", "test_key_12345")
    return "test_key_12345"
