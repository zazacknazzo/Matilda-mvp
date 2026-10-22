"""Explicit test-only composition. Never imported by the production application."""
from app.main import app
from app.api.studio_preview import get_provider
from app.studio.ports import ProviderFailure
from studio_flow_provider import FlowProvider


class BrowserProvider(FlowProvider):
    failed_once = set()

    async def complete(self, request):
        import asyncio
        await asyncio.sleep(0.15)
        if request.stage == 'preview' and any('T13-preview-race' in doc['content'] for doc in request.material['source_documents']):
            await asyncio.sleep(1)
        if request.stage == 'lesson':
            documents = request.material['source_documents']
            if any('T13-reconnect' in doc['content'] for doc in documents):
                await asyncio.sleep(1)
            if any('falha única' in doc['content'] for doc in documents):
                key = documents[0]['id']
                if key not in self.failed_once:
                    self.failed_once.add(key)
                    raise ProviderFailure('unauthorized')
        if any('falha controlada' in doc['content'] for doc in request.material['source_documents']):
            raise ProviderFailure('unauthorized')
        return await super().complete(request)


app.dependency_overrides[get_provider] = BrowserProvider
