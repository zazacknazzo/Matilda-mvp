// M0 v1. Additive contracts; backend JSON uses snake_case.
// Runtime shape + source validation belongs to the server. IDs are opaque.
import type { Evidence, Match, Paper, Researcher } from './index';

export interface SourceDocument {
  id: string;
  project_id: string;
  type: 'text' | 'concept_list' | 'paper_metadata';
  title: string; // 1–160 characters
  content: string; // literal, 1–20,000 characters; never trim original content
  doi?: string | null; // canonical Forensics DOI, maximum 250 characters
  extraction_status?: 'ready'; // default: ready
}

export interface Provenance {
  source_document_id: string;
  concept_id?: string | null;
  method: 'teacher_input' | 'editorial_alias' | 'openalex_metadata' | 'ai_suggested';
  quote?: string | null; // nonblank literal substring, maximum 20,000 characters
  retrieved_at?: string | null; // ISO 8601 UTC
  from_cache?: boolean | null;
  source_url?: string | null;
}

export interface SourceAnchor {
  source_document_id: string;
  quote: string;
  occurrence: number; // integer >= 0, literal non-overlapping matches from left to right
}

export interface ScientificContext {
  id: string;
  origin_type: 'doi' | 'material' | 'mixed';
  paper_ids?: string[]; // default []
  concept_ids?: string[]; // resolved scientific IDs only; default []
  concept_labels?: string[]; // aligned to concept_ids; default []
  source_document_ids: string[];
  provenance: Provenance[];
  limitations?: string[]; // default []; explicit coverage limitation if no concepts
  analysis_id?: string | null;
}

// States are the existing DiscoveryMatch contract, without changing Forensics types.
export type ScientificMatch = Omit<Match, 'relation_type' | 'citation_status' | 'researchers' | 'evidence' | 'contribution'> & {
  contribution: Omit<Match['contribution'], 'verification_status'> & {
    verification_status: 'verified' | 'pending';
  };
  researchers: (Omit<Researcher, 'identity_status'> & {
    identity_status: 'verified' | 'pending';
    orcid?: string | null;
  })[];
  evidence: (Omit<Evidence, 'source_type' | 'verification_status'> & {
    source_type: 'documental' | 'historical' | 'bibliographic' | 'thematic';
    verification_status: 'verified' | 'pending';
  })[];
  relation_type: 'RELATED_TO';
  citation_status: 'CITED' | 'NOT_FOUND_IN_RETRIEVED_REFERENCES' | 'UNKNOWN' | 'THEMATIC_ONLY';
};

// Interface to implement in T04, not an HTTP operation or an implemented adapter.
export type ScientificRetriever = (
  context: ScientificContext,
  options: { comparable_paper?: Paper | null },
) => ScientificMatch[];
