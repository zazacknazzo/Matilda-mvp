"""Strict NVIDIA JSON decoding with diagnostics that contain no source text."""
import json


class InvalidJSON(ValueError):
    def __init__(self, code, **metrics):
        super().__init__(code)
        self.code, self.metrics = code, metrics


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidJSON('json_duplicate_key')
        result[key] = value
    return result


def _nonfinite_constant(_):
    raise InvalidJSON('json_nonfinite_constant')


def _integer(value):
    # Preserve Python's integer digit limit; never include the number in an error.
    try:
        return int(value)
    except ValueError:
        raise InvalidJSON('json_integer_too_large') from None


def decode_object(content: str | bytes) -> dict:
    try:
        value = json.loads(content, object_pairs_hook=_unique_keys,
                           parse_constant=_nonfinite_constant, parse_int=_integer)
    except json.JSONDecodeError as failure:
        raise InvalidJSON('json_syntax_invalid', error_position=failure.pos,
                          error_line=failure.lineno, error_column=failure.colno) from None
    except UnicodeDecodeError:
        raise InvalidJSON('json_unicode_invalid') from None
    except RecursionError:
        raise InvalidJSON('json_nesting_too_deep') from None
    if not isinstance(value, dict):
        raise InvalidJSON('json_root_not_object')
    return value
