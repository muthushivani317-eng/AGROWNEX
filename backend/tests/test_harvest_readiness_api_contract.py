from app.api.v1.router import api_router


def test_harvest_readiness_routes_are_registered() -> None:
    routes = {(method, route.path) for route in api_router.routes for method in route.methods}
    assert ("POST", "/harvest-readiness/evaluate") in routes
    assert ("GET", "/harvest-readiness/current") in routes
    assert ("GET", "/harvest-readiness/{readiness_id}/history") in routes
    assert ("POST", "/harvest-readiness/confirm") in routes
