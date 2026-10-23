"""Private, indivisible scientific candidates backed by canonical literal anchors."""
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
    candidate_id: Id
    pedagogical_rationale: Text
    suggested_content: Text


class PreviewPlan(LessonModel):
    suggested_objectives: list[Objective] = Field(min_length=1, max_length=10)
    suggestions: list[PlannedSuggestion] = Field(max_length=20)


@dataclass(frozen=True)
class ScientificCandidate:
    id: str
    contribution_id: str
    concept_id: str
    evidence_ids: tuple[str, ...]
    source_anchor: SourceAnchor

    def preview_fields(self):
        return {'contribution_id': self.contribution_id, 'concept_ids': [self.concept_id],
                'evidence_ids': list(self.evidence_ids), 'source_anchor': self.source_anchor.model_copy(deep=True)}


class ScientificCandidates:
    """Build once; one selection resolves all scientific fields without alternatives."""
    MAX_CHOICES = 8

    def __init__(self, *, context, documents, matches, concepts):
        self._matches = {match.contribution.id: match for match in matches}
        self._documents = {document.id: document for document in documents}
        self._document_keys = {document.id: f'd{index + 1}' for index, document in enumerate(documents)}
        self._contribution_keys = {identifier: f's{index + 1}' for index, identifier in enumerate(self._matches)}
        editorial = {concept.id: concept for concept in concepts}
        resolved = {(p.source_document_id, p.concept_id) for p in context.provenance if p.concept_id is not None}
        needed = {c.id for match in matches for c in match.matched_concepts if c.id in match.contribution.concept_ids}
        anchors = []
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
                    anchors.append((identifier, anchor))
        chosen, alternatives = {}, []
        # Guarantee one indivisible candidate per authorized contribution before alternatives.
        for identifier, match in self._matches.items():
            if match.contribution.verification_status != 'verified':
                raise PydanticCustomError('ineligible_contribution', 'Contribuição não verificada.')
            if not match.evidence or any(e.contribution_id != identifier or e.verification_status != 'verified'
                                        or e.source_type not in ('documental', 'historical') for e in match.evidence):
                raise PydanticCustomError('unauthorized_evidence', 'Evidência não elegível para a contribuição.')
            supported = {c.id for c in match.matched_concepts} & set(match.contribution.concept_ids)
            eligible = []
            for concept_id, anchor in anchors:
                if concept_id not in supported:
                    continue
                evidence_ids = tuple(e.id for e in match.evidence)
                token = sha256(json.dumps([context.id, identifier, concept_id, evidence_ids, anchor.model_dump()],
                                          sort_keys=True).encode()).hexdigest()[:24]
                eligible.append(ScientificCandidate('candidate-' + token, identifier, concept_id, evidence_ids, anchor))
            if not eligible:
                raise PydanticCustomError('missing_grounded_anchor', 'Contribuição sem trecho conceitual literal nos documentos autorizados.')
            chosen[eligible[0].id] = eligible[0]
            alternatives.extend(eligible[1:])
        if len(chosen) > self.MAX_CHOICES:
            raise PydanticCustomError('missing_grounded_anchor', 'Limite de candidatos não comporta todas as contribuições autorizadas.')
        for candidate in alternatives:
            if len(chosen) >= self.MAX_CHOICES:
                break
            chosen.setdefault(candidate.id, candidate)
        self._choices = chosen

    def for_model(self):
        return {
            'source_documents': [{'key': self._document_keys[d.id], 'type': d.type, 'content': d.content}
                                 for d in self._documents.values()],
            'scientific_contributions': {self._contribution_keys[identifier]: {
                'title': match.contribution.title,
                'evidence_claims': [e.claim_supported for e in match.evidence],
            } for identifier, match in self._matches.items()},
            'scientific_candidates': [{
                'id': candidate.id, 'contribution': self._contribution_keys[candidate.contribution_id],
                'concept': next(c.name for c in self._matches[candidate.contribution_id].matched_concepts if c.id == candidate.concept_id),
                'document': self._document_keys[candidate.source_anchor.source_document_id],
                'quote': candidate.source_anchor.quote, 'occurrence': candidate.source_anchor.occurrence,
            } for candidate in self._choices.values()],
        }

    def response_schema(self):
        schema = PreviewPlan.model_json_schema()
        schema['properties']['suggestions'].update(minItems=1 if self._matches else 0, maxItems=20 if self._matches else 0)
        if self._choices:
            schema['$defs']['PlannedSuggestion']['properties']['candidate_id']['enum'] = list(self._choices)
        return schema

    def resolve(self, identifier: str) -> ScientificCandidate:
        candidate = self._choices.get(identifier)
        if candidate is None:
            raise PydanticCustomError('invalid_scientific_candidate', 'Candidato científico não autorizado nesta operação.')
        candidate.source_anchor.locate(self._documents[candidate.source_anchor.source_document_id])
        return candidate
