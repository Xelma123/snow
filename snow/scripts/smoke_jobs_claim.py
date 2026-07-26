"""Jobs claim_due sets running so double-claim is empty."""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.config import Settings  # noqa: E402
from app.storage import jobs as job_store  # noqa: E402
from app.storage.db import init_db  # noqa: E402


async def run() -> None:
    with tempfile.TemporaryDirectory() as td:
        settings = Settings(data_dir=td, snow_app_token="test-token-for-smoke")
        await init_db(settings)
        jid = await job_store.enqueue(
            settings,
            time.time() - 1,
            {"tool": "light_control", "args": {"action": "off"}, "label": "test"},
        )
        assert jid > 0
        first = await job_store.claim_due(settings)
        assert len(first) == 1 and first[0]["id"] == jid
        second = await job_store.claim_due(settings)
        assert second == []
        await job_store.mark_done(settings, jid, ok=True)
        print("OK jobs claim")


def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
