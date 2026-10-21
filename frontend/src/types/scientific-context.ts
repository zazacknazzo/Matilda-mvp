/** Serialized Pydantic contracts from schemas/scientific_context.py (schema v1).
 * Defaults are materialized by the server; nullable fields remain explicit.
 * Validate untrusted input on the backend, including cross-document references.
 */
export interface SourceDocument {
  id: string;
  project_id: string;
  type: "text" | "concept_list" | "paper_metadata";
  title: string; // Nonblank, at most 20,000 characters; preserves real paper titles.
  content: string; // Literal, at most 20,000 characters; never truncated.
  doi: string | null;
  extraction_status: "ready";
}

export interface Provenance {
  source_document_id: string;
  concept_id: string | null; // Null for teacher_input/ai_suggested; scientific resolution is separate.
  method:
    | "teacher_input"
    | "editorial_alias"
    | "openalex_metadata"
    | "ai_suggested";
  quote: string | null; // Nonblank literal when present, at most 20,000 characters.
  retrieved_at: string | null;
  from_cache: boolean | null;
  source_url: string | null;
}

export interface SourceAnchor {
  source_document_id: string;
  quote: string; // Nonblank literal, at most 20,000 characters.
  occurrence: number; // Integer >= 0; overlapping occurrences, as in the PR #15 contract.
}

export interface ScientificContext {
  id: string;
  origin_type: "doi" | "material" | "mixed";
  paper_ids: string[];
  concept_ids: string[];
  concept_labels: string[];
  source_document_ids: string[];
  provenance: Provenance[];
  limitations: string[]; // At least one nonblank limitation when concept_ids is empty.
  analysis_id: string | null;
}
