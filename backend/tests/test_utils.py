import io

import pandas as pd
import pytest
from fastapi import UploadFile

from app.utils import read_upload_file, create_excel_response, _sanitize_cell


@pytest.mark.asyncio
async def test_read_upload_file_uses_xlrd_for_xls(monkeypatch):
    captured = {}
    expected_df = pd.DataFrame({"地址": ["北京市朝阳区"]})

    def fake_read_excel(*args, **kwargs):
        captured["engine"] = kwargs.get("engine")
        return expected_df

    monkeypatch.setattr("app.utils.pd.read_excel", fake_read_excel)

    upload = UploadFile(filename="sample.xls", file=io.BytesIO(b"fake-binary"))
    df, contents = await read_upload_file(upload)

    assert captured["engine"] == "xlrd"
    assert df.equals(expected_df)
    assert contents == b"fake-binary"


class TestSanitizeCell:
    """测试公式注入转义函数 _sanitize_cell"""

    @pytest.mark.parametrize("value", [
        "=SUM(A1:A10)",
        "+cmd",
        "-1+1",
        "@attacker.com",
        "\t=formula",
        "\r=formula",
    ])
    def test_formula_prefixes_are_escaped(self, value):
        result = _sanitize_cell(value)
        assert result.startswith("'"), f"Expected escape for: {value!r}"
        assert result[1:] == value

    def test_normal_string_unchanged(self):
        assert _sanitize_cell("北京市朝阳区") == "北京市朝阳区"

    def test_non_string_unchanged(self):
        assert _sanitize_cell(12345) == 12345
        assert _sanitize_cell(None) is None
        assert _sanitize_cell(3.14) == 3.14

    def test_empty_string_unchanged(self):
        assert _sanitize_cell("") == ""


@pytest.mark.asyncio
async def test_create_excel_response_sanitizes_formulas():
    """Excel 导出函数应当对公式注入内容进行转义"""
    df = pd.DataFrame({
        "地址": ["=HYPERLINK(\"http://evil.com\",\"click\")", "正常地址"],
        "结果": ["+cmd", "116.48,39.99"],
    })
    response = create_excel_response(df, "test.xlsx")
    # 读回写出的 Excel，验证公式被转义
    chunks = [chunk async for chunk in response.body_iterator]
    content = b"".join(chunks)
    result_df = pd.read_excel(io.BytesIO(content))
    assert result_df["地址"][0].startswith("'")
    assert result_df["结果"][0].startswith("'")