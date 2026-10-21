"""T11: deterministic Markdown from an authorized, persisted LessonBundle only."""
import html
import re
from hashlib import sha256
from urllib.parse import quote

from app.schemas.lesson import (
    ContentBlock, EvidenceClaimBlock, LessonBundle, LessonReference,
    QuestionBlock, StepsBlock, TextBlock,
)


def markdown_text(value: str) -> str:
    """Treat every generated string as text, including HTML and Markdown syntax."""
    value = html.escape(value, quote=False).replace('\r\n', '\n').replace('\r', '\n')
    value = re.sub(r'([\\`*_{}\[\]()#+.!|>~-])', r'\\\1', value)
    return value.replace('\n', '  \n')


def source_url(value: str) -> str:
    LessonReference.safe_link(value)
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError('URL documental inválida.')
    return quote(value, safe=":/?#@!$&'*+,;=%-._~")


def export_filename(bundle_id: str) -> str:
    # Opaque IDs and teacher-controlled titles never become header/path fragments.
    digest = sha256(bundle_id.encode('utf-8')).hexdigest()[:24]
    return f'matilda-aula-{digest}.md'


def lesson_markdown(bundle: LessonBundle) -> str:
    # Revalidate even if a caller mutated a Pydantic instance after construction.
    bundle = LessonBundle.model_validate(bundle.model_dump())
    references = {reference.id: reference for reference in bundle.references}
    for reference in bundle.references:
        source_url(reference.source_url)
    slides = {slide.id: slide for slide in bundle.slides}
    activities = {activity.id: activity for activity in bundle.activities}
    lines: list[str] = []

    def paragraph(text: str) -> None:
        lines.extend([markdown_text(text), ''])

    def heading(level: int, text: str) -> None:
        lines.extend(['#' * level + ' ' + markdown_text(text).replace('  \n', ' '), ''])

    def items(values: list[str], empty: str = 'Nenhum item informado.') -> None:
        if not values:
            paragraph(empty)
        for value in values:
            lines.append('- ' + markdown_text(value).replace('  \n', '  \n  '))
        lines.append('')

    def blocks(values: list[ContentBlock]) -> None:
        for block in values:
            if isinstance(block, EvidenceClaimBlock):
                reference = references[block.evidence_id]
                paragraph('Afirmação documentada: ' + reference.claim_supported)
                paragraph('Fonte: ' + reference.source_title)
            elif isinstance(block, QuestionBlock):
                paragraph('Questão: ' + block.text)
            elif isinstance(block, TextBlock):
                paragraph(block.text)
            elif isinstance(block, StepsBlock):
                for number, value in enumerate(block.items, 1):
                    lines.append(f'{number}. ' + markdown_text(value).replace('  \n', '  \n   '))
                lines.append('')
            else:
                items(block.items)

    heading(1, bundle.metadata.title)
    paragraph(f'{bundle.metadata.subject} · {bundle.metadata.education_level} · {bundle.metadata.duration_minutes} minutos')
    paragraph('Plano do professor. Conteúdo pedagógico gerado por IA sujeito à revisão docente; afirmações documentais resolvidas pelas fontes abaixo.')
    heading(2, 'Objetivos de aprendizagem')
    items(bundle.metadata.learning_objectives)
    heading(2, 'Conhecimentos prévios')
    items(bundle.metadata.prior_knowledge)
    heading(2, 'Materiais necessários')
    items(bundle.metadata.materials)
    heading(2, 'Sequência da aula')
    elapsed = 0
    slide_number = 0
    for section in bundle.sections:
        heading(3, f'{elapsed}–{elapsed + section.duration_minutes} min · {section.title}')
        elapsed += section.duration_minutes
        paragraph('Objetivos: ' + '; '.join(bundle.metadata.learning_objectives[index] for index in section.objective_indexes))
        blocks(section.explanation_blocks)
        for slide_id in section.slide_ids:
            slide = slides[slide_id]
            slide_number += 1
            heading(4, f'Slide {slide_number} · {slide.title} ({slide.duration_minutes} min)')
            if slide.subtitle:
                paragraph(slide.subtitle)
            blocks(slide.content_blocks)
            paragraph('Notas do professor: ' + (slide.speaker_notes or 'Nenhuma nota adicional.'))
        for activity_id in section.activity_ids:
            activity = activities[activity_id]
            heading(4, 'Atividade · ' + ('Discussão' if activity.type == 'discussion' else 'Compreensão'))
            paragraph(activity.prompt)
            paragraph('Orientação ao professor: ' + activity.teacher_guidance)
            paragraph('Objetivos: ' + '; '.join(bundle.metadata.learning_objectives[index] for index in activity.objective_indexes))
            heading(5, 'Critérios de avaliação')
            items(activity.assessment_criteria)
            paragraph('Tempo incluído nesta seção; não somar novamente.')
    heading(2, 'Referências documentais')
    if not bundle.references:
        paragraph('Sem enriquecimentos científicos aprovados. Nenhuma atribuição histórica foi acrescentada.')
    for reference in bundle.references:
        heading(3, reference.source_title)
        paragraph('Afirmação documentada: ' + reference.claim_supported)
        paragraph('Participantes da publicação: ' + '; '.join(reference.participants))
        title = markdown_text(reference.source_title).replace('  \n', ' ')
        lines.extend([f'[{title}](<{source_url(reference.source_url)}>)', ''])
        paragraph(reference.excerpt_or_location)
        paragraph(f'Fonte {"em cache" if reference.from_cache else "recuperada"} · {reference.retrieved_at}')
        items(reference.limitations)
    heading(2, 'Limitações da aula')
    items(bundle.limitations, 'Nenhuma limitação registrada.')
    heading(2, 'Registro de geração')
    metadata = bundle.generation_metadata
    paragraph(f'Provedor: {metadata.provider} · modelo: {metadata.model} · data: {metadata.generated_at} · contrato: {bundle.schema_version} · revisão: {bundle.review_revision}')
    return '\n'.join(lines).rstrip() + '\n'
