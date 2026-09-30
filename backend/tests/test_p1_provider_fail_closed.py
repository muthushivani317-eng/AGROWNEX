import pytest
from app.modules.ai import provider as ai
from app.modules.ai.exceptions import AIUnavailableError
from app.modules.experts import provider as experts
from app.modules.market import provider as market
from app.modules.market.exceptions import MarketDataUnavailableError
from app.modules.produce import provider as produce
from app.modules.schemes import provider as schemes
from app.modules.schemes.exceptions import SchemeDataUnavailableError


@pytest.mark.parametrize(
    ("module", "credential_name", "unavailable_type", "mock_type"),
    [
        (ai, "GEMINI_API_KEY", "UnavailableAIProvider", ai.MockAIProvider),
        (market, "DATA_GOV_API_KEY", "UnavailableMarketProvider", market.MockMarketProvider),
        # schemes is deliberately absent here (2026-08 pre-release audit
        # follow-up): unlike the others, it has no external credential to be
        # "unconfigured" -- its production default is now the hand-curated,
        # individually-sourced CuratedSchemeProvider (app/modules/schemes/
        # curated_data.py), not a credential-gated live API. Its own
        # fail-closed contract (stale curated data -> UnavailableSchemeProvider)
        # is covered below by test_schemes_fails_closed_when_curated_data_stale,
        # and in full by tests/test_schemes_curated_provider.py.
        (produce, None, "UnavailableProduceProvider", produce.MockProduceProvider),
        (experts, None, "UnavailableExpertProvider", experts.MockExpertProvider),
    ],
)
def test_unconfigured_default_provider_fails_closed(
    monkeypatch, module, credential_name, unavailable_type, mock_type
):
    if credential_name:
        monkeypatch.setattr(module, credential_name, "")
    if module is market:
        # Agmarknet 2.0 needs no credential; "unconfigured" means it is off too.
        monkeypatch.setattr(market, "AGMARKNET_V2_ENABLED", False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)

    selected = module.get_default_provider()

    assert type(selected).__name__ == unavailable_type
    assert not isinstance(selected, mock_type)


def test_market_without_data_gov_key_uses_agmarknet_v2_not_mock(monkeypatch):
    monkeypatch.setattr(market, "DATA_GOV_API_KEY", "")
    monkeypatch.setattr(market, "AGMARKNET_V2_ENABLED", True)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)

    selected = market.get_default_provider()

    assert type(selected).__name__ == "AgmarknetV2Provider"


def test_schemes_default_provider_is_curated_not_unavailable(monkeypatch):
    """schemes' production default ships real, sourced content -- it should
    NOT fail closed just because no credential is set (it never had one)."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)

    selected = schemes.get_default_provider()

    assert type(selected).__name__ == "CuratedSchemeProvider"
    assert not isinstance(selected, schemes.MockSchemeProvider)


def test_schemes_fails_closed_when_curated_data_stale(monkeypatch):
    """schemes' actual fail-closed trigger: nobody re-verified curated_data.py
    against its official sources within the staleness window."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AGROWAI_ENABLE_TEST_MOCKS", raising=False)
    monkeypatch.setattr(schemes, "is_curated_data_stale", lambda: True)

    selected = schemes.get_default_provider()

    assert type(selected).__name__ == "UnavailableSchemeProvider"


@pytest.mark.parametrize("module", [ai, market, schemes, produce, experts])
def test_kvk_field_test_never_enables_mock_from_environment(monkeypatch, module):
    for credential_name in ("GEMINI_API_KEY", "DATA_GOV_API_KEY"):
        if hasattr(module, credential_name):
            monkeypatch.setattr(module, credential_name, "")
    monkeypatch.setenv("APP_ENV", "kvk_field_test")
    monkeypatch.setenv("AGROWAI_ENABLE_TEST_MOCKS", "true")

    assert not type(module.get_default_provider()).__name__.startswith("Mock")


@pytest.mark.parametrize("module", [ai, market, schemes, produce, experts])
def test_explicit_test_mock_remains_available(monkeypatch, module):
    for credential_name in ("GEMINI_API_KEY", "DATA_GOV_API_KEY"):
        if hasattr(module, credential_name):
            monkeypatch.setattr(module, credential_name, "")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AGROWAI_ENABLE_TEST_MOCKS", "true")

    assert type(module.get_default_provider()).__name__.startswith("Mock")


@pytest.mark.asyncio
async def test_unavailable_providers_emit_no_farmer_facts_or_fake_acknowledgements():
    with pytest.raises(AIUnavailableError):
        await ai.UnavailableAIProvider().generate(system="", history=[], message="help")
    with pytest.raises(MarketDataUnavailableError):
        await market.UnavailableMarketProvider().fetch_prices(market.PriceQuery())
    with pytest.raises(SchemeDataUnavailableError):
        await schemes.UnavailableSchemeProvider().fetch_schemes()

    offer = produce.OfferRef(id="1", crop_name="Paddy", quantity=1, unit="kg")
    assert await produce.UnavailableProduceProvider().submit(offer) is None
    assert await produce.UnavailableProduceProvider().buyer_interest(offer) == []
    assert await experts.UnavailableExpertProvider().fetch_experts() == []
