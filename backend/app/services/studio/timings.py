"""Bounded stage measurements: no prompts, responses, keys or teacher text."""
from contextlib import contextmanager
import json
import logging
from time import monotonic

log = logging.getLogger('matilda.studio.timings')


@contextmanager
def measure(stage):
    if stage not in {'scientific_retrieval', 'context', 'token_count', 'structured_generation', 'validation', 'persistence'}:
        raise ValueError('Unknown stage.')
    started, status = monotonic(), 'failed'
    try:
        yield
        status = 'ok'
    finally:
        log.info('studio_stage %s', json.dumps({
            'stage': stage, 'duration_ms': round((monotonic() - started) * 1000, 3), 'status': status,
        }))
