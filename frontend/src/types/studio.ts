// T03 v1. Transport contracts; import scientific/lesson types without variants.
import type { Concept } from './index';
import type { ScientificContext, SourceAnchor, SourceDocument } from './scientific-context';
import type { LessonGenerationMetadata, LessonReference } from './lesson';

export type ProjectStatus = 'draft' | 'preview_ready' | 'reviewed' | 'generating' | 'ready';
export type GenerationStatus = 'idle' | 'generating' | 'ready' | 'failed';
export type StudioErrorCode =
  | 'invalid_input' | 'not_found' | 'review_conflict' | 'generation_in_progress'
  | 'input_too_large' | 'session_limit' | 'invalid_generation'
  | 'provider_unavailable' | 'studio_not_configured' | 'generation_timeout';

export interface PreviewRequest {
  title: string; // trimmed, 1–160 characters
  subject?: string; // default Ciências, max 80
  education_level?: string; // default Ensino Médio, max 80
  duration_minutes?: number; // integer 10–120, default 50
  objectives?: string[]; // 0–10, up to 300 characters each
  concepts?: string[]; // 0–20, up to 100 characters each
  material_text?: string; // literal, max 20,000 characters, default empty
  doi?: string | null;
  analysis_id?: string | null; // alternative to doi
  project_id?: string | null;
}

export interface StudioError {
  detail: string;
  code: StudioErrorCode;
  retryable: boolean;
  project_id?: string | null; // only when owned by the current session
}

export interface LessonProject {
  id: string;
  title: string;
  subject: string;
  education_level: string;
  duration_minutes: number;
  learning_objectives: string[]; // original teacher input, preserved
  scientific_context_id: string | null;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  last_teacher_activity_at: string;
  expires_at: string; // UTC, 7 days after last valid teacher action
}

export interface EnrichmentSuggestion {
  id: string;
  project_id: string;
  concept_ids: string[];
  source_anchor: SourceAnchor;
  researcher_ids: string[];
  contribution_id: string;
  evidence_ids: string[];
  scientific_explanation: string;
  historical_claim: string; // exact canonical claims joined by two newlines
  pedagogical_rationale: string;
  suggested_content: string;
  status: 'pending' | 'accepted' | 'rejected';
}

export interface EnrichmentPreview {
  preview_id: string;
  project_id: string;
  schema_version: 1;
  scientific_context: ScientificContext;
  concepts: Concept[];
  suggested_objectives: string[];
  suggestions: EnrichmentSuggestion[];
  evidence_references: LessonReference[];
  limitations: string[];
  review_revision: number;
  expires_at: string;
  generation_metadata: LessonGenerationMetadata;
  generation_status: GenerationStatus;
  last_lesson_bundle_id: string | null;
  project: LessonProject;
  source_documents: SourceDocument[];
  approved_objectives: string[]; // empty before review, then 1–10
  last_error: StudioError | null;
}

export interface ReviewDecision {
  suggestion_id: string;
  status: 'accepted' | 'rejected';
  pedagogical_rationale?: string | null; // null/omitted means no edit
  suggested_content?: string | null;
}

export interface ReviewRequest {
  review_revision: number; // expected revision; successful save increments it
  decisions: ReviewDecision[]; // unique IDs; partial decisions allowed
  approved_objectives: string[]; // 1–10, up to 300 characters each
}

export interface GenerateRequest {
  preview_id: string;
  review_revision: number;
  accepted_suggestion_ids: string[]; // unique, exactly the persisted accepted set
}

export interface StudioWriteHeaders {
  Origin: string; // must equal a configured trusted origin at the HTTP adapter
}

export interface GenerationHeaders extends StudioWriteHeaders {
  'Idempotency-Key': string; // opaque, nonblank, max 128 characters
}

export interface ExportQuery {
  format?: 'markdown';
}

// Generate/lesson GET return the existing LessonBundle directly. Export is UTF-8 Markdown.
