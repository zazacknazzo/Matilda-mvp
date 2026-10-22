import type { Match, Paper } from "../types";
import type {
  ScientificContext,
  SourceDocument,
} from "../types/scientific-context";

/** T06 component input: composition of M0 models, from a server-owned snapshot.
 * Never send this object as client authority to the Studio generation API.
 */
export interface ScientificSourceSnapshot {
  scientific_context: ScientificContext;
  source_documents: SourceDocument[];
  papers: Paper[];
  matches: Match[];
}
