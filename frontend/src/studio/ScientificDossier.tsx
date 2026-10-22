import { useEffect, useId, useRef, type ReactNode } from "react";
import { citationLabels } from "../components/EvidenceInspector";
import { safeSourceUrl } from "../lesson/lesson-view";
import type { ScientificSourceSnapshot } from "./scientific-source";
import type { EnrichmentPreview } from "../types/studio";
import type { Evidence } from "../types";
import "./scientific-dossier.css";

function SourceLink({ url, title }: { url: string; title: string }) {
  const href = safeSourceUrl(url);
  return href ? (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {title}
    </a>
  ) : (
    <span>{title} · link indisponível</span>
  );
}

function DossierFrame({
  onBack,
  identity,
  children,
}: {
  onBack(): void;
  identity: string;
  children: ReactNode;
}) {
  const heading = useRef<HTMLHeadingElement>(null);
  const headingId = useId();
  useEffect(() => {
    heading.current?.focus();
  }, [identity]);
  return (
    <section className="scientific-dossier" aria-labelledby={headingId}>
      <h2 id={headingId} ref={heading} tabIndex={-1}>
        Dossiê científico
      </h2>
      <button type="button" onClick={onBack}>
        Voltar ao Studio
      </button>
      {children}
    </section>
  );
}

function EvidenceDocument({ evidence }: { evidence: Evidence }) {
  return (
    <article className="scientific-dossier-source">
      <h5>
        <SourceLink url={evidence.source_url} title={evidence.source_title} />
      </h5>
      <p>
        ID: {evidence.id} · contribuição {evidence.contribution_id}
      </p>
      <p>
        Tipo: {evidence.source_type} · Verificação:{" "}
        {evidence.verification_status}
      </p>
      <p>Localização: {evidence.excerpt_or_location}</p>
      <h5>Afirmação sustentada</h5>
      <blockquote>{evidence.claim_supported}</blockquote>
    </article>
  );
}

type Props = { contributionId: string; onBack(): void } & (
  | { source: ScientificSourceSnapshot; preview?: never }
  | { preview: EnrichmentPreview; source?: never }
);

/** M0 previews expose canonical references, without fabricating a Paper/Match. */
export function ScientificDossier(props: Props) {
  return props.preview ? (
    <PreviewDossier
      preview={props.preview}
      contributionId={props.contributionId}
      onBack={props.onBack}
    />
  ) : (
    <SourceScientificDossier
      source={props.source!}
      contributionId={props.contributionId}
      onBack={props.onBack}
    />
  );
}

function PreviewDossier({
  preview,
  contributionId,
  onBack,
}: {
  preview: EnrichmentPreview;
  contributionId: string;
  onBack(): void;
}) {
  const suggestions = preview.suggestions.filter(
    (item) => item.contribution_id === contributionId,
  );
  const references = preview.evidence_references.filter(
    (item) => item.contribution_id === contributionId,
  );
  return (
    <DossierFrame onBack={onBack} identity={contributionId}>
      <h3>Origem científica</h3>
      <p>
        {preview.scientific_context.origin_type === "material"
          ? "Sem artigo comparável: material do professor."
          : "Artigo científico vinculado à preparação."}
      </p>
      {preview.source_documents
        .filter((doc) => doc.type === "paper_metadata")
        .map((doc) => (
          <article key={doc.id}>
            <h4>{doc.title}</h4>
            <SourceLink
              url={`https://doi.org/${doc.doi}`}
              title={`DOI: ${doc.doi}`}
            />
          </article>
        ))}
      <h3>Conceitos e procedência</h3>
      <p>{preview.scientific_context.concept_labels.join("; ")}</p>
      <ul>
        {preview.scientific_context.provenance.map((entry, index) => (
          <li key={index}>
            {entry.method}
            {entry.quote && <blockquote>{entry.quote}</blockquote>}
            {entry.retrieved_at && (
              <p>
                {entry.from_cache ? "Cache" : "Consulta na fonte"} ·{" "}
                {entry.retrieved_at}
              </p>
            )}
            {entry.source_url && (
              <SourceLink url={entry.source_url} title="Fonte da procedência" />
            )}
          </li>
        ))}
      </ul>
      <h3>Contribuição documentada · {contributionId}</h3>
      {suggestions.map((item) => (
        <p key={item.id}>{item.scientific_explanation}</p>
      ))}
      {!references.length && (
        <p role="alert">Evidência indisponível nesta prévia.</p>
      )}
      {references.map((reference) => (
        <section key={reference.id}>
          <h4>Todos os participantes documentados da publicação</h4>
          <p>{reference.participants.join("; ")}</p>
          <EvidenceDocument evidence={reference} />
          <ul>
            {reference.limitations.map((limit, index) => (
              <li key={index}>{limit}</li>
            ))}
          </ul>
        </section>
      ))}
      <h3>Limitações do contexto</h3>
      <ul>
        {preview.scientific_context.limitations.map((limit, index) => (
          <li key={index}>{limit}</li>
        ))}
      </ul>
    </DossierFrame>
  );
}

/** Read-only canonical science. Material needs neither a Paper nor a graph root. */
function SourceScientificDossier({
  source,
  contributionId,
  onBack,
}: {
  source: ScientificSourceSnapshot;
  contributionId: string;
  onBack(): void;
}) {
  const match = source.matches.find(
    (item) => item.contribution.id === contributionId,
  );
  return (
    <DossierFrame onBack={onBack} identity={contributionId}>
      <section aria-label="Origem científica">
        <h3>Origem científica</h3>
        <p>
          Origem: {source.scientific_context.origin_type} · Contexto:{" "}
          {source.scientific_context.id}
        </p>
        {source.scientific_context.analysis_id && (
          <p>
            Investigação de origem: {source.scientific_context.analysis_id}. A
            ciência registrada permanece disponível mesmo se a investigação
            expirar.
          </p>
        )}
        {source.papers.length ? (
          source.papers.map((paper) => (
            <article key={paper.id}>
              <h4>{paper.title}</h4>
              <SourceLink
                url={`https://doi.org/${paper.doi}`}
                title={`DOI: ${paper.doi}`}
              />
              <p>
                Autores do artigo:{" "}
                {paper.authors.map((author) => author.name).join("; ")}
              </p>
              <SourceLink
                url={paper.source_url}
                title="Registro bibliográfico no OpenAlex"
              />
              <p>
                Metadados{" "}
                {paper.from_cache ? "em cache" : "consultados na fonte"}
                {paper.cache_stale
                  ? " · cache anterior à validade configurada"
                  : ""}{" "}
                ·{" "}
                <time dateTime={paper.retrieved_at}>{paper.retrieved_at}</time>
              </p>
              <p>
                Referências:{" "}
                {paper.references_status === "unavailable"
                  ? "indisponíveis"
                  : "conjunto recuperado; completude não auditada"}
              </p>
            </article>
          ))
        ) : (
          <p>
            Sem artigo comparável: consulte as contribuições documentadas e suas
            fontes a partir do material.
          </p>
        )}
        <h4>Conceitos e procedência</h4>
        <p>
          {source.scientific_context.concept_labels.join("; ") ||
            "Sem conceitos científicos resolvidos."}
        </p>
        <ul>
          {source.scientific_context.provenance.map((entry, index) => (
            <li key={index}>
              {entry.method} · documento {entry.source_document_id}
              {entry.concept_id ? ` · conceito ${entry.concept_id}` : ""}
              {entry.quote && <blockquote>{entry.quote}</blockquote>}
              {entry.retrieved_at && (
                <p>
                  <time dateTime={entry.retrieved_at}>
                    {entry.retrieved_at}
                  </time>{" "}
                  · {entry.from_cache ? "cache" : "consulta na fonte"}{" "}
                  {entry.source_url && (
                    <SourceLink
                      url={entry.source_url}
                      title="Fonte da procedência"
                    />
                  )}
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>
      {match ? (
        <article aria-label="Contribuição documentada">
          <h3>{match.contribution.title}</h3>
          <p>
            ID: {match.contribution.id} · Verificação:{" "}
            {match.contribution.verification_status}
          </p>
          <p>{match.contribution.description}</p>
          <h4>Pesquisadoras documentadas</h4>
          <ul>
            {match.researchers.map((researcher) => (
              <li key={researcher.id}>
                {researcher.name} · {researcher.id} · identidade{" "}
                {researcher.identity_status}
                {researcher.verification_sources.map((url, index) => (
                  <p key={url}>
                    <SourceLink
                      url={url}
                      title={`Fonte de identidade ${index + 1}`}
                    />
                  </p>
                ))}
              </li>
            ))}
          </ul>
          <h4>Todos os participantes documentados da publicação</h4>
          <p>{match.contribution.participants.join("; ")}</p>
          <h4>Relação e comparação bibliográfica</h4>
          <p>Relação temática · {match.relation_type}</p>
          <p>
            {citationLabels[match.citation_status] || match.citation_status} ·{" "}
            {match.citation_status}
          </p>
          <p>{match.explanation}</p>
          <p>
            Correspondência temática não comprova influência histórica. Não
            localizar uma citação nas referências recuperadas não comprova
            exclusão.
          </p>
          <h4>Fontes documentais</h4>
          {match.evidence.map((evidence) => (
            <EvidenceDocument key={evidence.id} evidence={evidence} />
          ))}
          <h4>Limitações da contribuição</h4>
          <ul>
            {match.limitations.map((limit, index) => (
              <li key={index}>{limit}</li>
            ))}
          </ul>
        </article>
      ) : (
        <p role="alert">
          Contribuição indisponível nos dados preservados. Volte à preparação
          para selecionar outra descoberta.
        </p>
      )}
      <section aria-label="Limitações do contexto">
        <h3>Limitações do contexto</h3>
        <ul>
          {source.scientific_context.limitations.map((limit, index) => (
            <li key={index}>{limit}</li>
          ))}
        </ul>
      </section>
      <details>
        <summary>Documentos originais · somente leitura</summary>
        {source.source_documents.map((document) => (
          <article key={document.id}>
            <h3>{document.title}</h3>
            <p>
              {document.type} · {document.id}
            </p>
            <pre>{document.content}</pre>
          </article>
        ))}
      </details>
    </DossierFrame>
  );
}
