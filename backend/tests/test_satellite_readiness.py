from app.modules.satellite.readiness import satellite_readiness


def test_satellite_readiness_reports_components_without_secret_values(monkeypatch) -> None:
    values = {
        "COPERNICUS_CLIENT_ID": "client-id-sensitive",
        "COPERNICUS_CLIENT_SECRET": "client-secret-sensitive",
        "R2_ACCOUNT_ID": "account-sensitive",
        "R2_ACCESS_KEY_ID": "access-sensitive",
        "R2_SECRET_ACCESS_KEY": "storage-secret-sensitive",
        "R2_PUBLIC_BASE_URL": "https://images.example.test",
        "REDIS_URL": "redis://queue.internal:6379/0",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    result = satellite_readiness()

    assert result == {
        "provider_configured": True,
        "storage_configured": True,
        "public_delivery_configured": True,
        "queue_configured": True,
        "ready_for_image_generation": True,
        "missing_components": [],
    }
    rendered = repr(result)
    assert not any(secret in rendered for secret in values.values())


def test_satellite_readiness_fails_closed_with_actionable_component_names(monkeypatch) -> None:
    for key in (
        "COPERNICUS_CLIENT_ID", "COPERNICUS_CLIENT_SECRET", "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_PUBLIC_BASE_URL", "REDIS_URL",
    ):
        monkeypatch.delenv(key, raising=False)

    result = satellite_readiness()

    assert result["ready_for_image_generation"] is False
    assert result["missing_components"] == ["provider", "storage", "public_delivery", "queue"]
