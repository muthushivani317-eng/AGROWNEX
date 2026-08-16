"""Export consented, officer-reviewed Redgram records; never triggers training."""
from __future__ import annotations

import asyncio
import json

from app.core.database import SessionLocal
from app.modules.disease.review import export_reviewed_redgram


async def main() -> None:
    async with SessionLocal() as session:
        print(json.dumps(await export_reviewed_redgram(session), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
