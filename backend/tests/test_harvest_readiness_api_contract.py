from app.api.v1.router import api_router
from fastapi import FastAPI


def test_harvest_readiness_routes_are_registered() -> None:
    app = FastAPI()
    app.include_router(api_router)
    paths = app.openapi()["paths"]

    assert "post" in paths["/harvest-readiness/evaluate"]
    assert "get" in paths["/harvest-readiness/current"]
    assert "get" in paths["/harvest-readiness/{readiness_id}/history"]
    assert "post" in paths["/harvest-readiness/confirm"]
