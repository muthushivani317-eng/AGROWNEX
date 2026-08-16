from app.api.v1.router import api_router


def test_action_verification_routes_are_registered() -> None:
    routes = {(method, route.path) for route in api_router.routes for method in route.methods}
    assert ("GET", "/action-verification/actions") in routes
    assert ("POST", "/action-verification/actions") in routes
    assert ("GET", "/action-verification/actions/{action_id}") in routes
    assert ("POST", "/action-verification/actions/{action_id}/responses") in routes
    assert ("GET", "/action-verification/actions/{action_id}/history") in routes
