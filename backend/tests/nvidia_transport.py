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
        content = compact_payload(json.loads(result.content)) if stage == 'lesson' else json.loads(result.content)
        return httpx.Response(200, json={
            'model': 'controlled', 'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': json.dumps(content)}}],
            'usage': {'prompt_tokens': 900, 'completion_tokens': 1200},
        })
    return NVIDIAProvider(transport=httpx.MockTransport(upstream))


def compact_payload(full):
    """Test provider speaks NVIDIA authoring format; never used in production."""
    return {**{k: full[k] for k in ('prior_knowledge', 'materials', 'limitations')}, 'sections': [
        {**{k: section[k] for k in ('title', 'objective_indexes')}, 'time_weight': section['duration_minutes'],
         'slides': [authored_slide(slide)
                    for slide in full['slides'] if slide['key'] in section['slide_keys']],
         'activities': [{k: value for k, value in activity.items() if k not in ('key', 'section_key')}
                        for activity in full['activities'] if activity['key'] in section['activity_keys']]}
        for section in full['sections']]}


def authored_slide(slide):
    """Explicit test-double translation of existing public gold fixtures."""
    blocks = slide['content_blocks']
    texts = [b['text'] for b in blocks if b['type'] == 'text']
    content = {'layout': slide['layout']}
    if slide['layout'] == 'TITLE':
        if texts:
            content['introduction'] = '\n'.join(texts)
    elif slide['layout'] == 'CONCEPT':
        bullets = [item for b in blocks if b['type'] == 'bullets' for item in b['items']]
        content['text'] = '\n'.join(texts or bullets)
        if texts:
            content['bullets'] = bullets
    elif slide['layout'] == 'PROCESS':
        content['steps'] = [item for b in blocks if b['type'] == 'steps' for item in b['items']]
    elif slide['layout'] == 'QUESTION':
        content['question'] = next(b['text'] for b in blocks if b['type'] == 'question')
    elif slide['layout'] == 'SUMMARY':
        content['synthesis'] = '\n'.join(texts or [item for b in blocks if b['type'] == 'bullets' for item in b['items']])
    evidence = [b['evidence_id'] for b in blocks if b['type'] == 'evidence_claim']
    if slide['layout'] == 'SCIENTIST_SPOTLIGHT':
        content['evidence_id'] = evidence.pop(0)
    return {**{k: slide[k] for k in ('title', 'speaker_notes')}, 'subtitle': slide.get('subtitle'),
            'content': content, 'evidence_ids': evidence}
