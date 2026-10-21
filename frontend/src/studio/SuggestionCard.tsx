import { useId } from "react";
import type { EnrichmentPreview, EnrichmentSuggestion } from "../types/studio";
import { safeSourceUrl } from "../lesson/lesson-view";

export type SuggestionEdit = Pick<
  EnrichmentSuggestion,
  "status" | "pedagogical_rationale" | "suggested_content"
>;

interface Props {
  suggestion: EnrichmentSuggestion;
  preview: EnrichmentPreview;
  edit: SuggestionEdit;
  disabled: boolean;
  onChange: (edit: SuggestionEdit) => void;
}

export function SuggestionCard({
  suggestion,
  preview,
  edit,
  disabled,
  onChange,
}: Props) {
  const labelId = useId();
  const document = preview.source_documents.find(
    (item) => item.id === suggestion.source_anchor.source_document_id,
  );
  const concepts = preview.concepts.filter((item) =>
    suggestion.concept_ids.includes(item.id),
  );
  const status = {
    pending: "Pendente",
    accepted: "Aceita",
    rejected: "Rejeitada",
  }[edit.status];
  return (
    <article className="review-suggestion" aria-labelledby={labelId}>
      <header>
        <h3 id={labelId}>
          {concepts.map((item) => item.name).join(" · ") ||
            "Sugestão de enriquecimento"}
        </h3>
        <strong>{status}</strong>
      </header>
      <p>
        <strong>Onde inserir · {document?.title}</strong>
      </p>
      <blockquote>{suggestion.source_anchor.quote}</blockquote>
      <p>
        Ocorrência {suggestion.source_anchor.occurrence + 1} no documento
        original.
      </p>
      <p>{suggestion.scientific_explanation}</p>
      <fieldset disabled={disabled}>
        <legend>Decisão sobre esta sugestão</legend>
        <label>
          <input
            type="radio"
            name={labelId}
            checked={edit.status === "accepted"}
            onChange={() => onChange({ ...edit, status: "accepted" })}
          />{" "}
          Aceitar
        </label>
        <label>
          <input
            type="radio"
            name={labelId}
            checked={edit.status === "rejected"}
            onChange={() => onChange({ ...edit, status: "rejected" })}
          />{" "}
          Rejeitar
        </label>
        <label>
          Proposta pedagógica
          <textarea
            maxLength={20000}
            value={edit.suggested_content}
            onChange={(event) =>
              onChange({ ...edit, suggested_content: event.target.value })
            }
          />
        </label>
        <label>
          Justificativa pedagógica
          <textarea
            maxLength={20000}
            value={edit.pedagogical_rationale}
            onChange={(event) =>
              onChange({ ...edit, pedagogical_rationale: event.target.value })
            }
          />
        </label>
      </fieldset>
      <section aria-label="Evidências científicas">
        <h4>Histórico documentado · somente leitura</h4>
        <p className="review-literal">{suggestion.historical_claim}</p>
        {suggestion.evidence_ids.map((id) => {
          const evidence = preview.evidence_references.find(
            (item) => item.id === id,
          );
          if (!evidence) return <p key={id}>Evidência indisponível.</p>;
          const url = safeSourceUrl(evidence.source_url);
          return (
            <div className="review-evidence" key={id}>
              <p>
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    {evidence.source_title}
                  </a>
                ) : (
                  <span>{evidence.source_title} — link indisponível</span>
                )}
              </p>
              <p>{evidence.excerpt_or_location}</p>
              <p>
                <strong>Participantes documentados:</strong>{" "}
                {evidence.participants.join("; ")}
              </p>
              <ul>
                {evidence.limitations.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
              <p>
                Fonte {evidence.from_cache ? "em cache" : "consultada"} ·{" "}
                <time dateTime={evidence.retrieved_at}>
                  {evidence.retrieved_at}
                </time>
              </p>
            </div>
          );
        })}
      </section>
    </article>
  );
}
