import io

import pandas as pd
import pytest
from fastapi import UploadFile

from app.utils import read_upload_file


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