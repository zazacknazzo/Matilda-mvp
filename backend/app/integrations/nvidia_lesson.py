"""NVIDIA-only authoring schema; deterministic expansion to the unchanged LessonDraft."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.lesson import ContentBlock, Index, LessonModel, Text, validate_slide_content
from app.services.studio.lesson_validator import LessonDraft
from app.studio.lesson_diagnostics import LessonRejected

CONTRACT_VERSION = 'compact-v3-authorized'

INSTRUCTION = '''\nRetorne um único objeto JSON completo conforme o schema de resposta, não o próprio schema.
Sem Markdown, cercas de código ou texto antes/depois. Use aspas duplas e escapes
JSON válidos nas strings; não repita chaves, não use vírgulas finais nem NaN/Infinity.
Para o schema compacto: aninhe slides e atividades na seção correspondente.
Escolha time_weight inteiro de 1 a 1000 por seção: maior peso reserva mais tempo
adicional para a intenção pedagógica daquela seção. Não informe duration_minutes.
O servidor reserva um minuto por slide e distribui o tempo restante aprovado
proporcionalmente aos pesos, por maiores restos (empates na ordem das seções).
Depois divide cada seção entre seus slides, com resto na ordem. Atividades estão
incluídas no tempo da seção. O servidor cria chaves e vínculos. Objetivos continuam sendo índices
semânticos da lista aprovada, escolhidos por você para cada seção e atividade.
Produza 3–8 seções, 4–12 slides NO TOTAL e 1–4 atividades NO TOTAL.
Escreva a explicação docente uma única vez em speaker_notes; o plano será montado
com os blocos dos slides e essas notas. Slides devem ser concisos (até 600
caracteres pedagógicos visíveis), com notas instrutivas e avaliação coerente.
Use evidence_claim somente com evidence_id literal da enumeração autorizada.
Sem evidências autorizadas, não use evidence_claim nem SCIENTIST_SPOTLIGHT.
Não invente, abrevie ou substitua identificadores. Não invente história.
'''


class CompactSlide(LessonModel):
    layout: Literal['TITLE', 'CONCEPT', 'PROCESS', 'SCIENTIST_SPOTLIGHT', 'QUESTION', 'SUMMARY']
    title: Annotated[str, Field(min_length=1, max_length=100, pattern=r'\S')]
    subtitle: Text | None = None
    content_blocks: list[ContentBlock] = Field(max_length=6)
    speaker_notes: Annotated[str, Field(min_length=1, max_length=1500, pattern=r'\S')]

    @model_validator(mode='after')
    def content_matches_layout(self):
        validate_slide_content(self.layout, self.title, self.subtitle, self.content_blocks,
                               has_contribution=any(block.type == 'evidence_claim' for block in self.content_blocks))
        return self


class CompactActivity(LessonModel):
    type: Literal['comprehension', 'discussion']
    prompt: Text
    teacher_guidance: Text
    objective_indexes: list[Index] = Field(min_length=1)
    assessment_criteria: list[Text] = Field(min_length=1)


class CompactSection(LessonModel):
    title: Text
    time_weight: Annotated[int, Field(ge=1, le=1000)]
    objective_indexes: list[Index] = Field(min_length=1)
    slides: list[CompactSlide] = Field(min_length=1, max_length=12)
    activities: list[CompactActivity] = Field(max_length=4)


class CompactLessonDraft(LessonModel):
    prior_knowledge: list[Text]
    materials: list[Text]
    sections: list[CompactSection] = Field(min_length=3, max_length=8)
    limitations: list[Text]

    @model_validator(mode='after')
    def aggregate_limits(self):
        if not 4 <= sum(len(s.slides) for s in self.sections) <= 12:
            raise ValueError('Aula exige 4–12 slides totais.')
        if not 1 <= sum(len(s.activities) for s in self.sections) <= 4:
            raise ValueError('Aula exige 1–4 atividades totais.')
        return self


def _schema_annotations(value):
    if isinstance(value, dict):
        # A property NAMED title is a dict and must remain; only annotation strings go.
        return {k: _schema_annotations(v) for k, v in value.items() if not (k == 'title' and isinstance(v, str))}
    if isinstance(value, list):
        return [_schema_annotations(v) for v in value]
    return value


def contract(request):
    material = request.material
    schema = _schema_annotations(CompactLessonDraft.model_json_schema())
    configuration = material.get('configuration', {})
    objectives = configuration.get('learning_objectives') if isinstance(configuration, dict) else None
    if isinstance(objectives, list) and objectives:
        for name in ('CompactSection', 'CompactActivity'):
            schema['$defs'][name]['properties']['objective_indexes']['items']['enum'] = list(range(len(objectives)))
    allowed = material.get('authorized_evidence', {})
    if allowed:
        schema['$defs']['EvidenceClaimBlock']['properties']['evidence_id']['enum'] = sorted(allowed)
    else:
        del schema['$defs']['EvidenceClaimBlock']
        blocks = schema['$defs']['CompactSlide']['properties']['content_blocks']['items']
        blocks['oneOf'] = [item for item in blocks['oneOf'] if item['$ref'] != '#/$defs/EvidenceClaimBlock']
        del blocks['discriminator']['mapping']['evidence_claim']
        layouts = schema['$defs']['CompactSlide']['properties']['layout']['enum']
        layouts.remove('SCIENTIST_SPOTLIGHT')
    return (request.system_instruction + INSTRUCTION, {
        **material,
        'source_documents': [{k: d[k] for k in ('type', 'content')} for d in material.get('source_documents', [])],
        'accepted_suggestions': [{k: s[k] for k in ('pedagogical_rationale', 'suggested_content')}
                                 for s in material.get('accepted_suggestions', [])],
    }, schema)


class LessonAuthoringError(LessonRejected):
    """Fixed diagnostic codes and integer metrics only; never provider content."""
    def __init__(self, code, **metrics):
        super().__init__(code, 'provider')
        self.metrics = {key: value for key, value in metrics.items()
                        if key in {'approved_minutes', 'minimum_minutes', 'section_minutes'} and type(value) is int}


def approved_duration(material):
    configuration = material.get('configuration')
    if configuration is None or isinstance(configuration, dict) and 'duration_minutes' not in configuration:
        raise LessonAuthoringError('lesson_configuration_missing')
    if not isinstance(configuration, dict):
        raise LessonAuthoringError('lesson_configuration_invalid')
    duration = configuration['duration_minutes']
    if type(duration) is not int or not 10 <= duration <= 120:
        raise LessonAuthoringError('lesson_configuration_invalid')
    return duration


def approved_objective_count(material):
    configuration = material.get('configuration', {})
    objectives = configuration.get('learning_objectives') if isinstance(configuration, dict) else None
    if not isinstance(objectives, list) or not objectives or any(not isinstance(text, str) or not text.strip() for text in objectives):
        raise LessonAuthoringError('lesson_objectives_missing')
    return len(objectives)


def expand(content: bytes, *, duration_minutes: int, authorized_evidence: set[str], objective_count: int) -> bytes:
    draft = CompactLessonDraft.model_validate_json(content)
    for owner in [*draft.sections, *(activity for section in draft.sections for activity in section.activities)]:
        if any(index >= objective_count for index in owner.objective_indexes):
            raise LessonAuthoringError('lesson_objective_not_approved')
        if len(set(owner.objective_indexes)) != len(owner.objective_indexes):
            raise LessonAuthoringError('lesson_duplicate_identifier')
    for section in draft.sections:
        for slide in section.slides:
            if any(block.type == 'evidence_claim' and block.evidence_id not in authorized_evidence
                   for block in slide.content_blocks):
                raise LessonAuthoringError('lesson_evidence_not_authorized')
            if slide.layout == 'SCIENTIST_SPOTLIGHT' and not authorized_evidence:
                raise LessonAuthoringError('lesson_slide_layout_invalid')
    # A baseline minute per slide is mandatory, not a repair of model minutes.
    minimums = [len(section.slides) for section in draft.sections]
    remaining = duration_minutes - sum(minimums)
    if remaining < 0:
        raise LessonAuthoringError('lesson_time_budget_infeasible', approved_minutes=duration_minutes,
                                   minimum_minutes=sum(minimums))
    weight_total = sum(section.time_weight for section in draft.sections)
    shares = [divmod(remaining * section.time_weight, weight_total) for section in draft.sections]
    durations = [minimum + share[0] for minimum, share in zip(minimums, shares)]
    leftover = duration_minutes - sum(durations)
    order = sorted(range(len(shares)), key=lambda index: (-shares[index][1], index))
    for index in order[:leftover]:
        durations[index] += 1
    sections, slides, activities = [], [], []
    for section_index, section in enumerate(draft.sections):
        section_key = f'section-{section_index}'
        slide_keys, activity_keys, explanation = [], [], []
        minutes, remainder = divmod(durations[section_index], len(section.slides))
        for index, slide in enumerate(section.slides):
            key = f'slide-{len(slides)}'
            slide_keys.append(key)
            slides.append({**slide.model_dump(), 'key': key, 'section_key': section_key,
                           'duration_minutes': minutes + (index < remainder)})
            explanation.extend(b.model_dump() for b in slide.content_blocks)
            if slide.speaker_notes.strip():
                explanation.append({'type': 'text', 'text': slide.speaker_notes})
        for activity in section.activities:
            key = f'activity-{len(activities)}'
            activity_keys.append(key)
            activities.append({**activity.model_dump(), 'key': key, 'section_key': section_key})
        sections.append({'key': section_key, 'title': section.title, 'duration_minutes': durations[section_index],
                         'objective_indexes': section.objective_indexes, 'explanation_blocks': explanation,
                         'slide_keys': slide_keys, 'activity_keys': activity_keys})
    try:
        full = LessonDraft(prior_knowledge=draft.prior_knowledge, materials=draft.materials, sections=sections,
                           slides=slides, activities=activities, limitations=draft.limitations)
        return full.model_dump_json().encode()
    except (ValueError, KeyError, TypeError):
        raise LessonAuthoringError('lesson_expansion_invalid') from None
