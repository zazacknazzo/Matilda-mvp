import re
import unicodedata
from app.schemas import Concept
from .storage import load_json

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))

def contains(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(normalized(phrase)) + r'(?!\w)', normalized(text)))


def editorial_alias_spans(text, aliases):
    """Yield original character spans for deterministic editorial alias matches."""
    content = normalized(text)
    offsets = [index for index, char in enumerate(text) for _ in normalized(char)]
    seen = set()
    for alias in aliases:
        for match in re.finditer(r'(?<!\w)' + re.escape(normalized(alias)) + r'(?!\w)', content):
            start, end = offsets[match.start()], offsets[match.end() - 1] + 1
            while end < len(text) and unicodedata.combining(text[end]):
                end += 1
            if (start, end) not in seen:
                seen.add((start, end))
                yield start, end


def editorial_alias_quote(text, aliases):
    """Keep the same first editorial match, copied literally from the document."""
    span = next(editorial_alias_spans(text, aliases), None)
    return text[span[0]:span[1]] if span is not None else None


def extract_concepts(raw, abstract):
    sources = {'título': raw.get('title') or raw.get('display_name') or '', 'resumo': abstract or ''}
    sources['tópicos OpenAlex'] = ' '.join(x.get('display_name', '') for x in raw.get('topics') or [])
    sources['palavras-chave OpenAlex'] = ' '.join(x.get('display_name', '') for x in raw.get('keywords') or [])
    result = []
    for entry in load_json('concepts.json'):
        provenance = [label for label, text in sources.items() if any(contains(text, alias) for alias in entry['aliases'])]
        if provenance:
            result.append(Concept(**entry, provenance=provenance))
    # Dynamic topics expand beyond the small editorial vocabulary.
    for topic in (raw.get('topics') or [])[:3]:
        if re.fullmatch(r'https://openalex.org/T\d+', topic.get('id', '')) and topic.get('display_name') and isinstance(topic.get('score'), (int, float)) and topic['score'] >= 0.5:
            result.append(Concept(id=topic['id'], name=topic['display_name'], provenance=['tópico atribuído pelo OpenAlex; relevância não auditada']))
    return result
