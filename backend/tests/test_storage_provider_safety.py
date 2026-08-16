import uuid

import pytest
from app.modules.disease import storage as storage_module
from app.modules.disease.controlled_test_reports import persist_controlled_test_report
from app.modules.disease.storage import (
    MockStorage,
    StorageUnavailableError,
    UnavailableStorage,
    get_default_storage,
)
from app.modules.growth.service import GrowthService
from app.modules.nutrient.service import NutrientService


@pytest.mark.parametrize("environment", ["production", "kvk_field_test", "internal_testing"])
def test_missing_r2_credentials_fail_closed_in_release_environments(
    monkeypatch: pytest.MonkeyPatch, environment: str
) -> None:
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("AGROWAI_ENABLE_TEST_MOCKS", "true")

    selected = get_default_storage()

    assert isinstance(selected, UnavailableStorage)
    assert not isinstance(selected, MockStorage)


def test_mock_storage_requires_explicit_test_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AGROWAI_ENABLE_TEST_MOCKS", "true")

    assert isinstance(get_default_storage(), MockStorage)


@pytest.mark.asyncio
async def test_unavailable_storage_never_returns_an_object_url() -> None:
    with pytest.raises(StorageUnavailableError) as raised:
        await UnavailableStorage().put(
            key="nutrient/user/farm/image.jpg",
            data=b"image",
            content_type="image/jpeg",
        )

    assert raised.value.error_code == "storage_provider_unavailable"


@pytest.mark.asyncio
async def test_explicit_mock_storage_remains_injectable_for_tests() -> None:
    url = await MockStorage().put(
        key="tests/image.jpg", data=b"image", content_type="image/jpeg"
    )

    assert url == "https://r2.mock.local/tests/image.jpg"


def test_growth_and_nutrient_default_consumers_receive_fail_closed_storage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("APP_ENV", "production")

    assert isinstance(GrowthService(object()).storage, UnavailableStorage)
    assert isinstance(NutrientService(object()).storage, UnavailableStorage)


@pytest.mark.asyncio
async def test_controlled_disease_report_does_not_persist_mock_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(StorageUnavailableError):
        await persist_controlled_test_report(
            object(),
            user_id=uuid.uuid4(),
            farm_id=None,
            image=b"image",
            content_type="image/jpeg",
            capture_method="camera",
            crop="paddy",
            disease=None,
            confidence=None,
            model_used="controlled",
            test_mode={"active": True},
            outcome="blocked",
        )
