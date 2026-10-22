"""Physical Studio retention without requiring a visitor to return to Studio."""
import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import logging
import sqlite3

from app.services.studio.runtime_repository import StudioRepository

log = logging.getLogger('matilda.studio')


async def cleanup():
    try:
        await StudioRepository().cleanup_expired(now=datetime.now(timezone.utc).isoformat())
    except sqlite3.Error:
        # A cleanup failure must not prevent the independent Forensics from starting.
        log.warning('studio_cleanup_failed code=storage_unavailable')


async def periodic_cleanup():
    while True:
        await asyncio.sleep(3600)
        await cleanup()


@asynccontextmanager
async def studio_lifespan(app):
    await cleanup()
    task = asyncio.create_task(periodic_cleanup())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
