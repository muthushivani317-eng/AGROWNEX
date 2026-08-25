from __future__ import annotations

import uuid

import pytest
from app import worker
from app.modules.satellite import jobs


@pytest.mark.asyncio
async def test_satellite_render_job_deserializes_uuid(monkeypatch):
    session_id = uuid.uuid4()
    user_id = uuid.uuid4()
    received = []

    async def fake_render(received_session_id, received_user_id, *, raise_on_error):
        received.append((received_session_id, received_user_id, raise_on_error))

    monkeypatch.setattr(worker, "_render_satellite_images", fake_render)

    result = await worker.render_satellite_images_job({}, str(session_id), str(user_id))

    assert received == [(session_id, user_id, True)]
    assert result == {"session_id": str(session_id), "rendered": True}


def test_worker_registers_satellite_render_job():
    assert worker.render_satellite_images_job in worker.WorkerSettings.functions


@pytest.mark.asyncio
async def test_repair_jobs_dedupe_within_window_and_allow_next_window(monkeypatch):
    job_ids = []

    class FakeRedis:
        async def enqueue_job(self, *_args, **kwargs):
            job_ids.append(kwargs["_job_id"])
            return object()

        async def close(self):
            return None

    async def fake_pool(_settings):
        return FakeRedis()

    monkeypatch.setattr(jobs, "create_pool", fake_pool)
    session_id = uuid.uuid4()
    user_id = uuid.uuid4()
    monkeypatch.setattr(jobs.time, "time", lambda: 120.0)
    await jobs.enqueue_satellite_image_render(session_id, user_id, force=True)
    await jobs.enqueue_satellite_image_render(session_id, user_id, force=True)
    monkeypatch.setattr(jobs.time, "time", lambda: 180.0)
    await jobs.enqueue_satellite_image_render(session_id, user_id, force=True)

    assert job_ids[0] == job_ids[1]
    assert job_ids[2] != job_ids[1]
