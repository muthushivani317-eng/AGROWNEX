from app.core.exceptions import UnauthorizedError
from app.core.logging import _drop_expected_client_errors


def test_expected_4xx_is_dropped_real_errors_kept():
    event = {"x": 1}
    exc = UnauthorizedError("nope")
    assert _drop_expected_client_errors(event, {"exc_info": (type(exc), exc, None)}) is None
    boom = RuntimeError("bug")
    assert _drop_expected_client_errors(event, {"exc_info": (type(boom), boom, None)}) == event
    assert _drop_expected_client_errors(event, {}) == event
