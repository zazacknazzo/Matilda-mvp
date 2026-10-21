/** Serialized Pydantic contracts from schemas/scientific_context.py (schema v1).
 * Defaults are materialized by the server; nullable fields remain explicit.
 * Validate untrusted input on the backend, including cross-document references.
 */
export interface SourceDocument {
  id: string;
  project_id: string;
  type: "text" | "concept_list" | "paper_metadata";
  title: string;
  content: string;
  doi: string | null;
  extraction_status: "ready";
}

export interface Provenance {
  source_document_id: string;
  concept_id: string | null;
  method:
    | "teacher_input"
    | "editorial_alias"
    | "openalex_metadata"
    | "ai_suggested";
  quote: string | null;
  retrieved_at: string | null;
  from_cache: boolean | null;
  source_url: string | null;
}

export interface SourceAnchor {
  source_document_id: string;
  quote: string;
  occurrence: number;
}

export interface ScientificContext {
  id: string;
  origin_type: "doi" | "material" | "mixed";
  paper_ids: string[];
  concept_ids: string[];
  concept_labels: string[];
  source_document_ids: string[];
  provenance: Provenance[];
  limitations: string[];
  analysis_id: string | null;
}
