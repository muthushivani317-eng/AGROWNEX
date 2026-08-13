from __future__ import annotations

import hashlib
import io
import uuid
from unittest.mock import AsyncMock

import httpx
import numpy as np
import pytest
from app.api.errors import register_exception_handlers
from app.core.config import settings
from app.core.database import get_session
from app.modules.auth.constants import RoleName, UserStatus
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User
from app.modules.auth.rbac_models import Role, UserRole
from app.modules.disease_comparison.models import DiseaseModelComparison
from app.modules.disease_comparison.provider import ProviderResult
from app.modules.disease_comparison.router import router
from app.modules.disease_comparison.schemas import OpenAISecondOpinion
from fastapi import FastAPI
from PIL import Image
from sqlalchemy import select


def image_bytes() -> bytes:
    y, x = np.mgrid[:160, :160]
    textured = (128 + 30 * np.sin(x / 5) + 20 * np.cos(y / 7)).astype(np.uint8)
    rgb = np.stack([textured, textured, textured], axis=2)
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, "PNG")
    return output.getvalue()


async def user_with_role(db_session, role_name: str) -> User:
    user = User(firebase_uid=f"guided-{uuid.uuid4()}", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    role = (
        await db_session.execute(select(Role).where(Role.role_name == role_name))
    ).scalar_one()
    db_session.add(UserRole(user_id=user.id, role_id=role.id))
    await db_session.flush()
    return user


def app_for(db_session, user: User) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)

    async def session_override():
        yield db_session

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_current_user] = lambda: user
    return app


@pytest.mark.asyncio
async def test_general_farmer_cannot_call_guided_evaluation(db_session, monkeypatch):
    monkeypatch.setattr(settings, "openai_disease_comparison_enabled", True)
    user = await user_with_role(db_session, RoleName.FARMER.value)
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease-comparisons-controlled/guided-evaluation",
            files={"images": ("leaf.png", image_bytes(), "image/png")},
            data={"views": "affected_leaf", "crop": "banana"},
        )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_controlled_user_gets_sanitized_agreement_decision(db_session, monkeypatch):
    monkeypatch.setattr(settings, "openai_disease_comparison_enabled", True)
    monkeypatch.setattr(settings, "openai_disease_comparison_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_disease_comparison_model", "test-model")
    user = await user_with_role(db_session, RoleName.KVK_REVIEWER.value)
    payload = image_bytes()
    db_session.add(
        DiseaseModelComparison(
            user_id=user.id,
            image_sha256=hashlib.sha256(payload).hexdigest(),
            crop="banana",
            local_model="banana-v3",
            local_status="accepted",
            local_label="sigatoka_leaf_spot",
            local_confidence=0.9,
            provider_model="test-model",
            provider_status="completed",
        )
    )
    await db_session.flush()
    opinion = OpenAISecondOpinion(
        crop_assessment="consistent",
        assessment_status="possible",
        image_usable=True,
        outcome_category="known_disease",
        known_class_match="high",
        possible_disease_label="sigatoka_leaf_spot",
        differential_diagnoses=[],
        observed_symptoms=["dark lesions"],
        evidence_supporting=["lesion pattern"],
        evidence_missing=[],
        additional_photo_required=False,
        requested_photo_view=None,
        expert_review_required=False,
    )
    monkeypatch.setattr(
        "app.modules.disease_comparison.router.OpenAIDiseaseComparisonProvider.compare_images",
        AsyncMock(
            return_value=ProviderResult(
                opinion=opinion,
                model="test-model",
                latency_ms=5,
                input_tokens=10,
                output_tokens=5,
            )
        ),
    )
    transport = httpx.ASGITransport(app=app_for(db_session, user))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/disease-comparisons-controlled/guided-evaluation",
            files={"images": ("leaf.png", payload, "image/png")},
            data={"views": "affected_leaf", "crop": "banana"},
        )
    assert response.status_code == 200, response.text
    decision = response.json()["data"]
    assert decision["status"] == "strong_agreement"
    assert "observed_symptoms" not in decision
    assert "confidence" not in decision
