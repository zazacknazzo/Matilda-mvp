import { useLayoutEffect, useRef, useState } from "react";
import type { PreviewRequest } from "../types/studio";
import type { ScientificSourceSnapshot } from "./scientific-source";
import { ScientificDossier } from "./ScientificDossier";
import "./scientific-dossier.css";
import type { Analysis } from "../types";

/** The existing Forensics host already owns its state and recorded investigation.
 * Only its ID crosses the write boundary; T06 resolves the context on the server.
 */
export function ForensicsLessonAction({
  analysis,
  onPrepare,
}: {
  analysis: Analysis;
  onPrepare(analysis: Analysis): void;
}) {
  return (
    <button
      type="button"
      className="primary-button"
      onClick={() => onPrepare(analysis)}
    >
      Transformar em aula
    </button>
  );
}

export interface ForensicsStudioBridgeProps<State> {
  source: ScientificSourceSnapshot;
  state: State;
  onConfigure(
    origin: Pick<PreviewRequest, "doi" | "analysis_id">,
    snapshot: ScientificSourceSnapshot,
    state: State,
  ): void;
  onExplore?(contributionId: string, state: State): void;
  onReturn(state: State): void;
}

/** The host owns preparation/review/presentation state and confirms configuration. */
export function ForensicsStudioBridge<State>({
  source,
  state,
  onConfigure,
  onExplore,
  onReturn,
}: ForensicsStudioBridgeProps<State>) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const returnFocusId = useRef<string | null>(null);
  const triggers = useRef(new Map<string, HTMLButtonElement>());
  useLayoutEffect(() => {
    if (selectedId === null && returnFocusId.current) {
      triggers.current.get(returnFocusId.current)?.focus();
      returnFocusId.current = null;
    }
  }, [selectedId]);
  if (selectedId !== null)
    return (
      <ScientificDossier
        source={source}
        contributionId={selectedId}
        onBack={() => {
          returnFocusId.current = selectedId;
          setSelectedId(null);
          onReturn(state);
        }}
      />
    );
  return (
    <section
      className="forensics-studio-bridge"
      aria-label="Ponte Forensics–Studio"
    >
      <h2>Da investigação à aula</h2>
      <p>
        Prepare uma aula com esta origem científica. Confirme a configuração no
        Studio antes de solicitar uma prévia.
      </p>
      <button
        type="button"
        onClick={() => {
          const origin = source.scientific_context.analysis_id
            ? { analysis_id: source.scientific_context.analysis_id }
            : source.papers[0]
              ? { doi: source.papers[0].doi }
              : {};
          onConfigure(origin, structuredClone(source), state);
        }}
      >
        Transformar em aula
      </button>
      {source.matches.length ? (
        <ul>
          {source.matches.map((match) => (
            <li key={match.contribution.id}>
              <button
                type="button"
                ref={(element) => {
                  if (element)
                    triggers.current.set(match.contribution.id, element);
                  else triggers.current.delete(match.contribution.id);
                }}
                onClick={() => {
                  setSelectedId(match.contribution.id);
                  onExplore?.(match.contribution.id, state);
                }}
              >
                Explorar descoberta · {match.contribution.title}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p role="status">
          Sem cobertura elegível neste catálogo; isto não indica inexistência de
          contribuições femininas.
        </p>
      )}
    </section>
  );
}
