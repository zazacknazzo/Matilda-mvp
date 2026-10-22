"""Opt-in maintenance over M0 ports. No T05/T10 imports or production wiring."""
import asyncio
from collections.abc import Callable
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
import logging
import math

from app.studio.ports import POLICY, StudioRepository
from .metrics import StudioMetrics

log = logging.getLogger('matilda.studio.operations')


def studio_maintenance_lifespan(
    repository: StudioRepository, *,
    now: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat(),
    interval_seconds: float = POLICY.recovery_grace_seconds,
    metrics: StudioMetrics | None = None,
):
    """Compose in the host lifespan; sweep immediately, then every 15 seconds.

    cleanup_expired owns atomic recovery at each operation's deadline + grace.
    Storage failure never prevents the independent Forensics host from starting.
    """
    if not math.isfinite(interval_seconds) or interval_seconds <= 0:
        raise ValueError('Maintenance interval must be finite and positive.')
    metrics = metrics if metrics is not None else StudioMetrics()

    async def sweep():
        try:
            removed = await repository.cleanup_expired(now=now())
            metrics.maintenance(removed)
        except Exception:
            metrics.maintenance()
            # Do not include exception text, SQL, material or credentials.
            log.warning('studio_maintenance_failed code=storage_unavailable')

    async def periodic():
        while True:
            await asyncio.sleep(interval_seconds)
            await sweep()

    @asynccontextmanager
    async def lifespan(app):
        await sweep()
        task = asyncio.create_task(periodic())
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return lifespan
