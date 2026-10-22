import type { EnrichmentPreview } from "../types/studio";

export function PreviewPanel({
  preview,
  onEdit,
}: {
  preview: EnrichmentPreview;
  onEdit(): void;
}) {
  const labels = new Map(
    preview.concepts.map((concept) => [concept.id, concept.name]),
  );
  return (
    <section aria-labelledby="studio-preview-title">
      <div className="studio-preview-heading">
        <div>
          <span className="eyebrow">MATILDA STUDIO · PRÉVIA</span>
          <h1 id="studio-preview-title" tabIndex={-1}>
            Prévia de enriquecimento
          </h1>
          <p>
            {preview.project.title} · {preview.project.subject} ·{" "}
            {preview.project.education_level} ·{" "}
            {preview.project.duration_minutes} min
          </p>
        </div>
        <button onClick={onEdit}>Editar entrada</button>
      </div>
      <p>
        Retida até {new Date(preview.expires_at).toLocaleString("pt-BR")}.
        Consulta não renova o prazo.
      </p>
      <div className="studio-preview-grid">
        <section className="studio-panel" aria-label="Material preservado">
          <h2>Material original</h2>
          {preview.source_documents.map((document) => (
            <article key={document.id}>
              <h3>{document.title}</h3>
              <pre data-testid="original-document">{document.content}</pre>
            </article>
          ))}
          <h3>Conceitos identificados</h3>
          {preview.concepts.length ? (
            <ul>
              {preview.concepts.map((concept) => (
                <li key={concept.id}>{concept.name}</li>
              ))}
            </ul>
          ) : (
            <p>Nenhum conceito do catálogo identificado.</p>
          )}
          <h3>Objetivos originais</h3>
          {preview.project.learning_objectives.length ? (
            <ul>
              {preview.project.learning_objectives.map((objective, i) => (
                <li key={i}>{objective}</li>
              ))}
            </ul>
          ) : (
            <p>Não informados.</p>
          )}
        </section>
        <section className="studio-panel" aria-label="Propostas pedagógicas">
          <h2>Sugestões de enriquecimento</h2>
          <p>
            Propostas geradas por IA. Confira as fontes e revise as sugestões e
            os objetivos antes de gerar a aula.
          </p>
          {preview.suggestions.length === 0 && (
            <div className="studio-notice">
              <h3>Sem cobertura documental</h3>
              <p>
                O catálogo não encontrou contribuições elegíveis para este
                material. Isso não indica inexistência de contribuições
                femininas.
              </p>
            </div>
          )}
          {preview.suggestions.map((suggestion) => (
            <article className="studio-suggestion" key={suggestion.id}>
              <span className="badge">Pendente</span>
              <h3>
                {suggestion.concept_ids
                  .map((id) => labels.get(id) || id)
                  .join(" · ")}
              </h3>
              <h4>Onde inserir</h4>
              <blockquote>{suggestion.source_anchor.quote}</blockquote>
              <small>
                Ocorrência {suggestion.source_anchor.occurrence + 1} no
                documento original.
              </small>
              <h4>Proposta pedagógica</h4>
              <p>{suggestion.suggested_content}</p>
              <h4>Por que inserir</h4>
              <p>{suggestion.pedagogical_rationale}</p>
              <h4>Relação científica</h4>
              <p>{suggestion.scientific_explanation}</p>
              <h4>Afirmação documental preservada</h4>
              <p className="studio-claim">{suggestion.historical_claim}</p>
              <p>
                Contribuição: <code>{suggestion.contribution_id}</code>
              </p>
              {suggestion.evidence_ids.map((id) => (
                <a
                  className="studio-reference-link"
                  key={id}
                  href={`#studio-evidence-${encodeURIComponent(id)}`}
                  onClick={(event) => {
                    event.preventDefault();
                    document.getElementById(`studio-evidence-${id}`)?.focus();
                  }}
                >
                  Conferir evidência {id}
                </a>
              ))}
            </article>
          ))}
          <h3>Objetivos sugeridos por IA</h3>
          <ul>
            {preview.suggested_objectives.map((objective, i) => (
              <li key={i}>{objective}</li>
            ))}
          </ul>
        </section>
        <section className="studio-panel" aria-label="Fontes científicas">
          <h2>Evidências e fontes</h2>
          {preview.evidence_references.map((reference) => (
            <article
              className="studio-reference"
              id={`studio-evidence-${reference.id}`}
              tabIndex={-1}
              key={reference.id}
            >
              <h3>{reference.source_title}</h3>
              <p>{reference.claim_supported}</p>
              <p>
                <strong>Participantes da publicação:</strong>{" "}
                {reference.participants.join(", ")}
              </p>
              <p>
                <strong>Localização:</strong> {reference.excerpt_or_location}
              </p>
              <p>
                Verificação:{" "}
                {reference.verification_status === "verified"
                  ? "documentação verificada"
                  : reference.verification_status}{" "}
                ·{" "}
                {reference.source_type === "documental"
                  ? "documental"
                  : "histórica"}
              </p>
              <a href={reference.source_url} target="_blank" rel="noreferrer">
                Abrir fonte original
              </a>
              <ul>
                {reference.limitations.map((limitation, i) => (
                  <li key={i}>{limitation}</li>
                ))}
              </ul>
              <small>
                Snapshot do catálogo local em{" "}
                {new Date(reference.retrieved_at).toLocaleString("pt-BR")}.
              </small>
            </article>
          ))}
        </section>
      </div>
      <section className="studio-limitations">
        <h2>Cobertura e limitações</h2>
        <ul>
          {preview.limitations.map((limitation, i) => (
            <li key={i}>{limitation}</li>
          ))}
        </ul>
        <small>
          Provedor: {preview.generation_metadata.provider} · Modelo:{" "}
          {preview.generation_metadata.model} ·{" "}
          {new Date(preview.generation_metadata.generated_at).toLocaleString(
            "pt-BR",
          )}
        </small>
      </section>
    </section>
  );
}
