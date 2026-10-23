"""Private authoring variants: a layout owns its required pedagogical content."""
from typing import Annotated, Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from app.schemas.lesson import Id, LessonModel, Text


class TitleContent(LessonModel):
    layout: Literal['TITLE']
    introduction: Text | None = None

    def blocks(self):
        return [{'type': 'text', 'text': self.introduction}] if self.introduction is not None else []


class ConceptContent(LessonModel):
    layout: Literal['CONCEPT']
    text: Text
    bullets: list[Text] = Field(default_factory=list, max_length=4)

    def blocks(self):
        return [{'type': 'text', 'text': self.text}] + ([{'type': 'bullets', 'items': self.bullets}] if self.bullets else [])


class ProcessContent(LessonModel):
    layout: Literal['PROCESS']
    steps: list[Text] = Field(min_length=2, max_length=6)

    def blocks(self):
        return [{'type': 'steps', 'items': self.steps}]


class QuestionContent(LessonModel):
    layout: Literal['QUESTION']
    question: Text

    def blocks(self):
        return [{'type': 'question', 'text': self.question}]


class SummaryContent(LessonModel):
    layout: Literal['SUMMARY']
    synthesis: Text

    def blocks(self):
        return [{'type': 'text', 'text': self.synthesis}]


class SpotlightContent(LessonModel):
    layout: Literal['SCIENTIST_SPOTLIGHT']
    evidence_id: Id

    def blocks(self):
        return [{'type': 'evidence_claim', 'evidence_id': self.evidence_id}]


SlideContent = Annotated[
    TitleContent | ConceptContent | ProcessContent | QuestionContent | SummaryContent | SpotlightContent,
    Field(discriminator='layout'),
]


class CompactSlide(LessonModel):
    title: Annotated[str, Field(min_length=1, max_length=100, pattern=r'\S')]
    subtitle: Text | None = None
    content: SlideContent
    # A coarse authoring floor, not a claim of instructional quality.
    speaker_notes: Annotated[str, Field(min_length=80, max_length=1500, pattern=r'\S')]
    evidence_ids: list[Id] = Field(default_factory=list, max_length=4)

    def public_fields(self):
        """Package model-authored fields; never invent, replace or truncate them."""
        return {'layout': self.content.layout, 'title': self.title, 'subtitle': self.subtitle,
                'content_blocks': self.content.blocks() + [
                    {'type': 'evidence_claim', 'evidence_id': eid} for eid in self.evidence_ids],
                'speaker_notes': self.speaker_notes}

    @model_validator(mode='after')
    def visible_budget(self):
        # Cross-field length is still defended locally and in the public validator.
        visible = len(self.title) + len(self.subtitle or '')
        for block in self.content.blocks():
            visible += len(block.get('text', '')) + sum(len(item) for item in block.get('items', []))
        if visible > 600:
            raise PydanticCustomError('lesson_slide_content_too_large', 'Slide excede 600 caracteres pedagógicos visíveis.')
        return self
