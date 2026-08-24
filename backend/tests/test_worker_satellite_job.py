from __future__ import annotations

import uuid

import pytest
from app import worker


@pytest.mark.asyncio
async def test_satellite_render_job_deserializes_uuid(monkeypatch):
    session_id = uuid.uuid4()
    user_id = uuid.uuid4()
    received = []

    async def fake_render(received_session_id, received_user_id, *, raise_on_error):
        received.append((received_session_id, received_user_id, raise_on_error))

    monkeypatch.setattr(worker, "_render_satellite_images", fake_render)

    result = await worker.render_satellite_images_job(
        {}, str(session_id), str(user_id)
    )

    assert received == [(session_id, user_id, True)]
    assert result == {"session_id": str(session_id), "rendered": True}


def test_worker_registers_satellite_render_job():
    assert worker.render_satellite_images_job in worker.WorkerSettings.functions
