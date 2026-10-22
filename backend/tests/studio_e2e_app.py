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
        result = await super().complete(request)
        if request.stage == 'lesson' and any('T13-multiple' in doc['content'] for doc in request.material['source_documents']):
            import json
            from app.studio.ports import ProviderResult
            value = json.loads(result.content)
            for identifier in list(request.material['authorized_evidence'])[1:]:
                claim = {'type': 'evidence_claim', 'evidence_id': identifier}
                value['sections'][0]['explanation_blocks'].append(claim)
                value['slides'][0]['content_blocks'].append(claim)
            return ProviderResult(json.dumps(value).encode(), result.metadata)
        return result


# Only external HTTP is substituted: the production NVIDIA adapter runs in E2E.
import os
from nvidia_transport import controlled_nvidia
os.environ['NVIDIA_API_KEY'] = 'e2e-controlled-key'
app.dependency_overrides[get_provider] = lambda: controlled_nvidia(BrowserProvider())
