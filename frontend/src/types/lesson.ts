// T02 / M0 v1. JSON in snake_case. Runtime validation belongs to the server.
// All strings are plain text, never trusted HTML. Scientific IDs are external.
export type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'bullets'; items: string[] }
  | { type: 'steps'; items: string[] } // 2–6 nonblank steps
  | { type: 'question'; text: string }
  | { type: 'evidence_claim'; evidence_id: string }; // no free historical text

export interface LessonMetadata {
  title: string; // 1–160 characters
  subject: string; // 1–80
  education_level: string; // 1–80
  duration_minutes: number; // integer 10–120
  learning_objectives: string[]; // 1–10 approved objectives, up to 300 characters
  prior_knowledge: string[];
  materials: string[];
}

export interface LessonGenerationMetadata {
  provider: string;
  model: string;
  prompt_version: string;
  schema_version: 1;
  generated_at: string; // ISO 8601 UTC
  duration_ms: number; // integer >= 0
  input_tokens?: number | null; // integer >= 0 or unavailable; omitted defaults null
  output_tokens?: number | null;
}

export interface LessonReference {
  id: string;
  contribution_id: string;
  claim_supported: string; // canonical, maximum 1,500 characters
  source_title: string;
  source_url: string; // HTTP(S), no credentials or whitespace
  source_type: 'documental' | 'historical';
  excerpt_or_location: string;
  verification_status: 'verified';
  researcher_ids: string[];
  participants: string[]; // all documented coauthors
  limitations: string[];
  retrieved_at: string; // ISO 8601 UTC
  from_cache: boolean;
}

export interface LessonSection {
  id: string;
  title: string;
  duration_minutes: number; // positive integer; sum of its slides
  objective_indexes: number[]; // unique, zero based, approved metadata objectives
  explanation_blocks: ContentBlock[];
  slide_ids: string[]; // at least one; each slide referenced once
  activity_ids: string[];
}

export interface LessonSlide {
  id: string;
  section_id: string;
  layout: 'TITLE' | 'CONCEPT' | 'PROCESS' | 'SCIENTIST_SPOTLIGHT' | 'QUESTION' | 'SUMMARY';
  title: string; // maximum 100 characters
  subtitle?: string | null; // omitted defaults null
  content_blocks: ContentBlock[]; // maximum 6; <=600 pedagogical characters including titles
  speaker_notes: string; // maximum 1,500 characters; never project as slide text
  duration_minutes: number; // positive integer; includes activity time
  contribution_ids: string[]; // exactly those resolved from evidence_ids
  evidence_ids: string[]; // exactly those used by evidence_claim blocks
}

export interface LessonActivity {
  id: string;
  section_id: string;
  type: 'comprehension' | 'discussion';
  prompt: string;
  teacher_guidance: string;
  objective_indexes: number[];
  assessment_criteria: string[]; // at least one criterion, at least one objective
}

export interface LessonBundle {
  lesson_bundle_id: string;
  project_id: string;
  preview_id: string;
  schema_version: 1;
  review_revision: number; // integer >=0, frozen server revision
  metadata: LessonMetadata;
  sections: LessonSection[]; // 3–8; total exactly metadata.duration_minutes
  slides: LessonSlide[]; // 4–12
  activities: LessonActivity[]; // 1–4; time already counted in sections/slides
  references: LessonReference[]; // canonical snapshots, deduplicated, exactly used evidence
  limitations: string[];
  generation_metadata: LessonGenerationMetadata;
}
