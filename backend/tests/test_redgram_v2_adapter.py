import pytest
from app.api.errors import register_exception_handlers
from app.redgram_v2.api_router import router
from app.redgram_v2.runtime import RedgramRuntime
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_superseded_redgram_v2_adapter_remains_fail_closed() -> None:
    runtime = RedgramRuntime()
    with pytest.raises(RuntimeError):
        runtime.load()


def test_general_farmer_cannot_reach_internal_redgram_endpoint() -> None:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    response = TestClient(app).post(
        "/disease/redgram/predict",
        files={"image": ("leaf.jpg", b"not-an-image", "image/jpeg")},
    )
    assert response.status_code in {401, 403}
