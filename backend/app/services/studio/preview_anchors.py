"""Private model selections backed by server-owned, literal scientific anchors."""
from dataclasses import dataclass
from hashlib import sha256
import json
from itertools import islice

from pydantic import Field
from pydantic_core import PydanticCustomError

from app.schemas.lesson import Id, LessonModel, Text
from app.schemas.scientific_context import SourceAnchor
from app.schemas.studio import Objective
from app.services.concept_analysis import editorial_alias_spans


class PlannedSuggestion(LessonModel):
    contribution_id: Id
    concept_ids: list[Id] = Field(min_length=1, max_length=20)
    evidence_ids: list[Id] = Field(min_length=1, max_length=20)
    source_anchor_id: Id
    pedagogical_rationale: Text
    suggested_content: Text


class PreviewPlan(LessonModel):
    suggested_objectives: list[Objective] = Field(min_length=1, max_length=10)
    suggestions: list[PlannedSuggestion] = Field(max_length=20)


@dataclass(frozen=True)
class CanonicalAnchor:
    id: str
    source_anchor: SourceAnchor
    concept_id: str

    def for_model(self):
        return {'id': self.id, 'source_anchor': self.source_anchor.model_dump(), 'concept_ids': [self.concept_id]}


class CanonicalAnchors:
    """Build once per operation; callers never trust a model-authored quote or offset."""
    MAX_CHOICES = 8

    def __init__(self, *, context, documents, matches, concepts):
        self._matches = {match.contribution.id: match for match in matches}
        self._documents = {document.id: document for document in documents}
        editorial = {concept.id: concept for concept in concepts}
        resolved = {(p.source_document_id, p.concept_id) for p in context.provenance if p.concept_id is not None}
        needed = {c.id for match in matches for c in match.matched_concepts if c.id in match.contribution.concept_ids}
        options = []
        for document in documents:
            for identifier in sorted(needed):
                concept = editorial.get(identifier)
                if concept is None or (document.id, identifier) not in resolved:
                    continue
                for start, end in islice(editorial_alias_spans(document.content, concept.aliases), 2):
                    quote = document.content[start:end]
                    cursor, occurrence = -1, -1
                    while cursor < start:
                        cursor = document.content.find(quote, cursor + 1)
                        occurrence += 1
                        if cursor < 0:
                            raise PydanticCustomError('missing_grounded_anchor', 'Trecho conceitual não é literal.')
                    anchor = SourceAnchor(source_document_id=document.id, quote=quote, occurrence=occurrence)
                    if anchor.locate(document) != (start, end):
                        raise PydanticCustomError('missing_grounded_anchor', 'Ocorrência conceitual não corresponde ao documento.')
                    token = sha256(json.dumps([context.id, document.id, identifier, start, end]).encode()).hexdigest()[:24]
                    options.append(CanonicalAnchor('anchor-' + token, anchor, identifier))
        self._allowed = {}
        chosen = {}
        # Guarantee every contribution has a grounded choice before adding alternatives.
        for identifier, match in self._matches.items():
            supported = {c.id for c in match.matched_concepts} & set(match.contribution.concept_ids)
            eligible = [option for option in options if option.concept_id in supported]
            if not eligible:
                raise PydanticCustomError('missing_grounded_anchor', 'Contribuição sem trecho conceitual literal nos documentos autorizados.')
            self._allowed[identifier] = {option.id for option in eligible}
            chosen.setdefault(eligible[0].id, eligible[0])
        if len(chosen) > self.MAX_CHOICES:
            raise PydanticCustomError('missing_grounded_anchor', 'Limite de âncoras não comporta todas as contribuições autorizadas.')
        for option in options:
            if len(chosen) >= self.MAX_CHOICES:
                break
            chosen.setdefault(option.id, option)
        self._choices = chosen

    def for_model(self):
        return {
            'authorized_contributions': [{
                'contribution_id': match.contribution.id,
                'concept_ids': [c.id for c in match.matched_concepts],
                'evidence_ids': [e.id for e in match.evidence],
                'source_anchor_ids': [identifier for identifier in self._choices if identifier in self._allowed[match.contribution.id]],
                'scientific_explanation': match.explanation,
            } for match in self._matches.values()],
            'authorized_source_anchors': [option.for_model() for option in self._choices.values()],
        }

    def response_schema(self):
        schema = PreviewPlan.model_json_schema()
        schema['properties']['suggestions'].update(minItems=1 if self._matches else 0, maxItems=20 if self._matches else 0)
        if self._matches:
            properties = schema['$defs']['PlannedSuggestion']['properties']
            properties['contribution_id']['enum'] = list(self._matches)
            properties['concept_ids']['items']['enum'] = sorted({c.id for m in self._matches.values() for c in m.matched_concepts})
            properties['evidence_ids']['items']['enum'] = sorted({e.id for m in self._matches.values() for e in m.evidence})
            properties['source_anchor_id']['enum'] = list(self._choices)
        return schema

    def resolve(self, selection: PlannedSuggestion) -> SourceAnchor:
        match = self._matches.get(selection.contribution_id)
        if match is None:
            raise PydanticCustomError('unknown_contribution', 'Contribuição não autorizada.')
        if not set(selection.evidence_ids) <= {e.id for e in match.evidence}:
            raise PydanticCustomError('unauthorized_evidence', 'Evidência não autorizada para a contribuição.')
        if not set(selection.concept_ids) <= ({c.id for c in match.matched_concepts} & set(match.contribution.concept_ids)):
            raise PydanticCustomError('invalid_concept', 'Conceito não autorizado para a contribuição.')
        option = self._choices.get(selection.source_anchor_id)
        if option is None:
            raise PydanticCustomError('invalid_source_anchor', 'Identificador de âncora não autorizado.', {'anchor_error': 'unknown_anchor_id'})
        if option.id not in self._allowed[selection.contribution_id] or set(selection.concept_ids) != {option.concept_id}:
            raise PydanticCustomError('invalid_source_anchor', 'Âncora sem vínculo com a contribuição e os conceitos selecionados.', {'anchor_error': 'anchor_binding_mismatch'})
        option.source_anchor.locate(self._documents[option.source_anchor.source_document_id])
        return option.source_anchor.model_copy(deep=True)
