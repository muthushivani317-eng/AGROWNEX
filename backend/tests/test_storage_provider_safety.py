import uuid

import httpx
import pytest
from app.modules.disease import storage as storage_module
from app.modules.disease.controlled_test_reports import persist_controlled_test_report
from app.modules.disease.storage import (
    MockStorage,
    R2Client,
    StorageError,
    StorageUnavailableError,
    UnavailableStorage,
    get_default_storage,
    get_private_storage,
)
from app.modules.growth.service import GrowthService
from app.modules.nutrient.service import NutrientService


@pytest.mark.parametrize("bucket", ["", "public-photos"])
def test_private_storage_rejects_missing_or_public_bucket(monkeypatch, bucket):
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "account")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "access")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(storage_module, "R2_BUCKET", "public-photos")
    monkeypatch.setattr(storage_module, "R2_PRIVATE_BUCKET", bucket)
    monkeypatch.setenv("APP_ENV", "production")
    assert isinstance(get_private_storage(), UnavailableStorage)


def test_private_storage_does_not_use_public_domain(monkeypatch):
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "account")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "access")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(storage_module, "R2_BUCKET", "public-photos")
    monkeypatch.setattr(storage_module, "R2_PRIVATE_BUCKET", "private-evidence")
    selected = get_private_storage()
    assert isinstance(selected, R2Client)
    assert selected.bucket == "private-evidence"
    assert selected.public_base_url == ""
    assert selected.require_public_read is False


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


def test_r2_credentials_without_public_base_url_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(storage_module, "R2_ACCOUNT_ID", "account")
    monkeypatch.setattr(storage_module, "R2_ACCESS_KEY_ID", "access")
    monkeypatch.setattr(storage_module, "R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setattr(storage_module, "R2_PUBLIC_BASE_URL", "")
    monkeypatch.setenv("APP_ENV", "production")

    assert isinstance(get_default_storage(), UnavailableStorage)


def test_r2_client_normalizes_public_base_url() -> None:
    client = R2Client(
        account_id="account",
        access_key="access",
        secret_key="secret",
        bucket="agrowai",
        public_base_url="https://public.example/",
    )

    assert client.bucket == "agrowai"
    assert client.public_base_url == "https://public.example"


@pytest.mark.asyncio
async def test_r2_upload_rejects_an_unreachable_public_url(monkeypatch) -> None:
    class FakeHttpClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def put(self, url, **_kwargs):
            return httpx.Response(200, request=httpx.Request("PUT", url))

        async def get(self, url, **_kwargs):
            return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(storage_module.httpx, "AsyncClient", lambda **_kwargs: FakeHttpClient())
    client = R2Client(
        account_id="account",
        access_key="access",
        secret_key="secret",
        bucket="agrowai",
        public_base_url="https://public.example",
    )

    with pytest.raises(StorageError):
        await client.put(
            key="satellite/session/scene/ndvi.png", data=b"png", content_type="image/png"
        )


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
    url = await MockStorage().put(key="tests/image.jpg", data=b"image", content_type="image/jpeg")

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
