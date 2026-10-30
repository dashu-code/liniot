"""测试公共夹具。"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from liniot.config import Config
from liniot.main import create_app


@pytest.fixture()
def core(tmp_path):
    """构建使用临时数据库的完整应用，返回 FastAPI 实例。

    内部组件通过 app.state.liniot 暴露，便于在测试中直接断言。
    """
    config = Config(db_path=tmp_path / "test.db", web_dir=tmp_path / "no-web")
    app = create_app(config)
    return app


@pytest.fixture()
def client(core):
    with TestClient(core) as test_client:
        yield test_client
