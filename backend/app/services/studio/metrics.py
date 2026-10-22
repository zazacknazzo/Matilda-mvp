"""Process-local, bounded aggregate counters; never retain prompts or identities."""
from collections import Counter
import logging

from app.studio.contracts import ERROR_HTTP_STATUS

log = logging.getLogger('matilda.studio.operations')


class StudioMetrics:
    def __init__(self):
        self.outcomes = Counter()
        self.errors = Counter()
        self.provider_attempts = 0
        self.input_tokens_counted = 0
        self.output_tokens_reported = 0
        self.duration_ms = 0
        self.maintenance_runs = 0
        self.maintenance_errors = 0
        self.expired_previews = 0

    def generation(self, outcome, elapsed, code=None):
        if outcome not in ('completed', 'replayed', 'failed', 'cancelled'):
            raise ValueError('Unknown operational outcome.')
        safe_code = code if code in ERROR_HTTP_STATUS else None
        self.outcomes[outcome] += 1
        if safe_code:
            self.errors[safe_code] += 1
        duration = max(0, round(elapsed * 1000))
        self.duration_ms += duration
        log.info('studio_generation outcome=%s code=%s duration_ms=%d', outcome, safe_code or 'none', duration)

    def attempt(self, tokens):
        self.provider_attempts += 1
        self.input_tokens_counted += tokens

    def output(self, tokens):
        if tokens is not None:
            self.output_tokens_reported += tokens

    def maintenance(self, removed=None):
        self.maintenance_runs += 1
        if removed is None:
            self.maintenance_errors += 1
        else:
            self.expired_previews += removed

    def snapshot(self):
        return {
            'generation_outcomes': dict(self.outcomes),
            'generation_errors': dict(self.errors),
            'provider_attempts': self.provider_attempts,
            'input_tokens_counted': self.input_tokens_counted,
            'output_tokens_reported': self.output_tokens_reported,
            'generation_duration_ms': self.duration_ms,
            'maintenance_runs': self.maintenance_runs,
            'maintenance_errors': self.maintenance_errors,
            'expired_previews': self.expired_previews,
        }
