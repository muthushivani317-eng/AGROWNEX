"""Deploy-time loader for cited organic catalogue manifests.

Rows are deliberately loaded as ``sourced_public_reference`` and cannot reach
production plan engines until an authorized content reviewer promotes them.
"""

from __future__ import annotations

import asyncio

from app.core.database import SessionLocal
from app.modules.organic.ingestion import seed_public_source_pack


async def main() -> None:
    async with SessionLocal() as session:
        created = await seed_public_source_pack(session)
        await session.commit()
        print(f"Loaded {len(created)} organic public-reference catalogue version(s).")


if __name__ == "__main__":
    asyncio.run(main())
