from __future__ import annotations

from app.crop_runtime import readiness_cache


def test_technical_snapshot_is_cached_until_explicit_refresh(monkeypatch) -> None:
    calls = 0

    def build():
        nonlocal calls
        calls += 1
        return {"banana": calls}

    with monkeypatch.context() as scoped:
        scoped.setattr(readiness_cache, "_build_snapshot", build)
        readiness_cache.refresh_technical_readiness()
        assert readiness_cache.get_technical_readiness() == {"banana": 1}
        assert readiness_cache.get_technical_readiness() == {"banana": 1}
        assert calls == 1
        readiness_cache.refresh_technical_readiness()
        assert readiness_cache.get_technical_readiness() == {"banana": 2}
    readiness_cache.refresh_technical_readiness()
