"""NVIDIA-only authoring schema; deterministic expansion to the unchanged LessonDraft."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.lesson import ContentBlock, Index, LessonModel, Minutes, Text
from app.services.studio.lesson_validator import LessonDraft

INSTRUCTION = '''\nPara o schema compacto: aninhe slides e atividades na seção correspondente.
Informe minutos inteiros por seção, somando a duração solicitada; reserve ao menos
um minuto por slide. O servidor distribui esses minutos entre os slides e cria
chaves e vínculos. Não escreva esses campos. Objetivos continuam sendo índices
semânticos da lista aprovada, escolhidos por você para cada seção e atividade.
Produza 3–8 seções, 4–12 slides NO TOTAL e 1–4 atividades NO TOTAL.
Escreva a explicação docente uma única vez em speaker_notes; o plano será montado
com os blocos dos slides e essas notas. Slides devem ser concisos (até 600
caracteres pedagógicos visíveis), com notas instrutivas e avaliação coerente.
Use evidence_claim somente com evidence_id autorizado. Não invente história.
'''


class CompactSlide(LessonModel):
    layout: Literal['TITLE', 'CONCEPT', 'PROCESS', 'SCIENTIST_SPOTLIGHT', 'QUESTION', 'SUMMARY']
    title: Annotated[str, Field(min_length=1, max_length=100)]
    subtitle: Text | None = None
    content_blocks: list[ContentBlock] = Field(max_length=6)
    speaker_notes: Annotated[str, Field(min_length=1, max_length=1500, pattern=r'\S')]


class CompactActivity(LessonModel):
    type: Literal['comprehension', 'discussion']
    prompt: Text
    teacher_guidance: Text
    objective_indexes: list[Index] = Field(min_length=1)
    assessment_criteria: list[Text] = Field(min_length=1)


class CompactSection(LessonModel):
    title: Text
    duration_minutes: Minutes
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
        if any(s.duration_minutes < len(s.slides) for s in self.sections):
            raise ValueError('Minutos da seção não comportam os slides.')
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
    return (request.system_instruction + INSTRUCTION, {
        **material,
        'source_documents': [{k: d[k] for k in ('type', 'content')} for d in material.get('source_documents', [])],
        'accepted_suggestions': [{k: s[k] for k in ('pedagogical_rationale', 'suggested_content')}
                                 for s in material.get('accepted_suggestions', [])],
    }, _schema_annotations(CompactLessonDraft.model_json_schema()))


def expand(content: bytes, *, duration_minutes: int) -> bytes:
    draft = CompactLessonDraft.model_validate_json(content)
    if sum(s.duration_minutes for s in draft.sections) != duration_minutes:
        raise ValueError('Durações não correspondem à configuração aprovada.')
    sections, slides, activities = [], [], []
    for section_index, section in enumerate(draft.sections):
        section_key = f'section-{section_index}'
        slide_keys, activity_keys, explanation = [], [], []
        minutes, remainder = divmod(section.duration_minutes, len(section.slides))
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
        sections.append({'key': section_key, 'title': section.title, 'duration_minutes': section.duration_minutes,
                         'objective_indexes': section.objective_indexes, 'explanation_blocks': explanation,
                         'slide_keys': slide_keys, 'activity_keys': activity_keys})
    full = LessonDraft(prior_knowledge=draft.prior_knowledge, materials=draft.materials, sections=sections,
                       slides=slides, activities=activities, limitations=draft.limitations)
    return full.model_dump_json().encode()
