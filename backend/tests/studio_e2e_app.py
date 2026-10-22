"""Explicit test-only composition. Never imported by the production application."""
from app.main import app
from app.api.studio_preview import get_provider
from app.studio.ports import ProviderFailure
from studio_flow_provider import FlowProvider


class BrowserProvider(FlowProvider):
    async def complete(self, request):
        import asyncio
        await asyncio.sleep(0.15)
        if any('falha controlada' in doc['content'] for doc in request.material['source_documents']):
            raise ProviderFailure('unauthorized')
        return await super().complete(request)


app.dependency_overrides[get_provider] = BrowserProvider
