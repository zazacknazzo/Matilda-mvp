"""Compose T12 maintenance over the real T10 repository, without provider IO."""
from contextlib import asynccontextmanager

from app.services.studio.metrics import StudioMetrics
from app.services.studio.operations import studio_maintenance_lifespan
from app.services.studio.runtime_repository import StudioRepository


@asynccontextmanager
async def studio_lifespan(app):
    metrics = StudioMetrics()
    app.state.studio_metrics = metrics
    maintenance = studio_maintenance_lifespan(StudioRepository(), metrics=metrics)
    async with maintenance(app):
        yield
