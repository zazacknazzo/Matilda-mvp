"""Coarse, explicit authoring checks; semantic quality still needs a teacher."""


def assess_quality(draft, *, objective_count, authorized_evidence):
    conceptual = [slide for slide in draft.slides if slide.layout in ('CONCEPT', 'PROCESS')]
    conceptual_chars = sum(len(block.text) if block.type == 'text' else
                           sum(len(item) for item in block.items) if block.type in ('steps', 'bullets') else 0
                           for slide in conceptual for block in slide.content_blocks)
    taught = {index for section in draft.sections for index in section.objective_indexes
              if any(slide.section_key == section.key for slide in conceptual)}
    assessed = {index for activity in draft.activities for index in activity.objective_indexes}
    expected = set(range(objective_count))
    used = {block.evidence_id for slide in draft.slides for block in slide.content_blocks if block.type == 'evidence_claim'}
    missing = []
    if conceptual_chars < 80:
        missing.append('conceptual_content_below_floor')
    if taught != expected:
        missing.append('objective_teaching_coverage_missing')
    if assessed != expected:
        missing.append('objective_assessment_coverage_missing')
    flags = ['conceptual_depth', 'instructional_notes', 'activity_applicability',
             'semantic_objective_alignment', 'scientific_relevance', 'pacing']
    if authorized_evidence and not used:
        flags.append('approved_evidence_unused')
    if any(slide.duration_minutes > 12 for slide in draft.slides):
        flags.append('long_slide_allocation')
    if any(section.activity_keys and section.duration_minutes < 3 for section in draft.sections):
        flags.append('short_activity_allocation')
    if len({slide.speaker_notes for slide in draft.slides}) < len(draft.slides):
        flags.append('repeated_teacher_notes')
    return {'structural_checks_passed': not missing, 'missing_requirements': missing,
            'conceptual_characters': conceptual_chars, 'minimum_conceptual_characters': 80,
            'objective_count': objective_count, 'taught_objectives': len(taught), 'assessed_objectives': len(assessed),
            'teacher_note_characters': sum(len(slide.speaker_notes) for slide in draft.slides),
            'activity_count': len(draft.activities), 'used_evidence_count': len(used),
            'approved_minutes': sum(section.duration_minutes for section in draft.sections),
            'teacher_review_required': True, 'teacher_review_points': flags}
