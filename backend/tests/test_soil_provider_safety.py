from app.modules.soil.provider import (
    MockSoilProvider,
    SoilGridsProvider,
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


def test_soilgrids_is_opt_in_only_never_default(monkeypatch) -> None:
    """SoilGrids needs no credentials, so a missing SOIL_PROVIDER must still
    fail closed in production -- it only activates on an explicit choice."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SOIL_PROVIDER", raising=False)

    assert isinstance(get_default_provider(), UnavailableSoilProvider)


def test_soilgrids_explicit_configuration_selects_the_real_adapter(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SOIL_PROVIDER", "soilgrids")

    assert isinstance(get_default_provider(), SoilGridsProvider)
