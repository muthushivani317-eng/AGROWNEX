from app.modules.soil.provider import (
    MockSoilProvider,
    UnavailableSoilProvider,
    get_default_provider,
)


def test_production_without_real_provider_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SOIL_PROVIDER", raising=False)

    assert isinstance(get_default_provider(), UnavailableSoilProvider)


def test_mock_provider_requires_explicit_development_configuration(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("SOIL_PROVIDER", "mock")

    assert isinstance(get_default_provider(), MockSoilProvider)


def test_unknown_configured_provider_fails_closed(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SOIL_PROVIDER", "not-a-real-adapter")

    assert isinstance(get_default_provider(), UnavailableSoilProvider)
