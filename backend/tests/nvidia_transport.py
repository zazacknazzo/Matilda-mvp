"""Test-only hosted HTTP boundary; production NVIDIA adapter and validators run."""
import json
from types import SimpleNamespace

import httpx

from app.integrations.nvidia_client import NVIDIAProvider
from app.studio.ports import ProviderFailure


def controlled_nvidia(external):
    async def upstream(http):
        body = json.loads(http.content)
        stage = 'preview' if body['response_format']['json_schema']['name'] == 'PreviewPlan' else 'lesson'
        request = SimpleNamespace(stage=stage, material=json.loads(body['messages'][1]['content']),
                                  prompt_version=f'studio-{stage}-v1')
        try:
            result = await external.complete(request)
        except ProviderFailure as error:
            statuses = {'unauthorized': 401, 'rate_limited': 429, 'unavailable': 503}
            if error.reason in statuses:
                return httpx.Response(statuses[error.reason], json={'error': 'controlled'})
            if error.reason == 'timeout':
                raise httpx.ReadTimeout('controlled')
            return httpx.Response(200, json={'choices': [{'finish_reason': 'length' if error.reason == 'truncated' else 'content_filter'}]})
        return httpx.Response(200, json={
            'model': 'controlled', 'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': result.content.decode()}}],
            'usage': {'prompt_tokens': 900, 'completion_tokens': 1200},
        })
    return NVIDIAProvider(transport=httpx.MockTransport(upstream))
