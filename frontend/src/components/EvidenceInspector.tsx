import {
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  FileCheck2,
  Fingerprint,
  Info,
} from "lucide-react";
import type { Match, GraphNode, Paper } from "../types";
import { typeNames } from "./ScientificGraph";
export const citationLabels: Record<string, string> = {
  CITED: "Citação identificada",
  NOT_FOUND_IN_RETRIEVED_REFERENCES:
    "Não localizada nas referências recuperadas",
  UNKNOWN: "Comparação inconclusiva",
  THEMATIC_ONLY: "Associação temática",
};
export function EvidenceInspector({
  match,
  node,
  paper,
}: {
  match: Match | null;
  node: GraphNode | null;
  paper: Paper;
}) {
  return (
    <aside
      className="inspector"
      aria-label="Inspetor de evidências"
      aria-live="polite"
    >
      <div className="panel-toolbar">
        <div>
          <Fingerprint size={17} />
          <strong>Inspetor de evidências</strong>
        </div>
        <span>03</span>
      </div>
      {!match ? (
        <div className="inspector-empty">
          <div className="round-icon">
            <BookOpen size={23} />
          </div>
          <span className="eyebrow">
            {node ? typeNames[node.type] : "CONSULTE AS FONTES"}
          </span>
          <h2>{node?.label || "Siga uma conexão."}</h2>
          <p>
            {node?.type === "CONCEPT"
              ? "Conceito identificado nos metadados disponíveis. Selecione uma contribuição para consultar as fontes."
              : node?.type === "PAPER"
                ? "Registro bibliográfico recuperado do OpenAlex. A relação de citação é indicada pelas setas do grafo."
                : "Escolha uma contribuição na lista ou no grafo para conhecer a participação científica e consultar suas fontes."}
          </p>
          {node?.type === "PAPER" && (
            <a
              className="text-link"
              href={node.id === paper.id ? paper.source_url : node.id}
              target="_blank"
              rel="noreferrer"
            >
              Abrir no OpenAlex <ArrowUpRight size={14} />
            </a>
          )}
          <div className="chain-preview">
            <span>Artigo</span>
            <i>↓ aborda</i>
            <span>Conceito</span>
            <i>↑ relação temática</i>
            <span>Contribuição</span>
            <i>↓ sustentada por</i>
            <span>Documento</span>
          </div>
        </div>
      ) : (
        <div className="dossier">
          <span className="eyebrow">DOSSIÊ CIENTÍFICO</span>
          <div className="verified">
            <CheckCircle2 size={14} />
            Contribuição documentada
          </div>
          <h2>{match.contribution.title}</h2>
          <p className="contribution-description">
            {match.contribution.description}
          </p>
          <section>
            <h3>Participação científica</h3>
            {match.researchers.map((r) => (
              <div className="researcher" key={r.id}>
                <div className="initials">
                  {r.name
                    .split(" ")
                    .filter((n) => n.length > 2)
                    .slice(0, 2)
                    .map((n) => n[0])
                    .join("")}
                </div>
                <div>
                  <strong>{r.name}</strong>
                  <a
                    href={r.verification_sources[0]}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Identidade · fonte biográfica <ArrowUpRight size={11} />
                  </a>
                </div>
              </div>
            ))}
            <details>
              <summary>Ver todos os participantes da publicação</summary>
              <p>{match.contribution.participants.join(" · ")}</p>
            </details>
          </section>
          <section>
            <h3>Relação com este artigo</h3>
            <span className="badge thematic">
              Relação temática · RELATED_TO
            </span>
            <p>{match.explanation}</p>
            <div
              className={
                "citation-status " +
                (match.citation_status === "CITED" ? "cited" : "")
              }
            >
              <BookOpen size={15} />
              <span>{citationLabels[match.citation_status]}</span>
            </div>
            <p className="small">
              A correspondência bibliográfica e a natureza temática da conexão
              são classificações independentes.
            </p>
          </section>
          <section>
            <h3>
              <FileCheck2 size={15} /> Fontes documentais
            </h3>
            {match.evidence.map((e) => (
              <article className="source-card" key={e.id}>
                <span className="eyebrow">FONTE PRIMÁRIA · DOCUMENTAL</span>
                <a href={e.source_url} target="_blank" rel="noreferrer">
                  {e.source_title}
                  <ArrowUpRight size={16} />
                </a>
                <p>{e.excerpt_or_location}</p>
                <details>
                  <summary>Afirmação sustentada pela fonte</summary>
                  <p>{e.claim_supported}</p>
                </details>
              </article>
            ))}
          </section>
          <section className="limitations">
            <h3>
              <Info size={15} /> Limites da interpretação
            </h3>
            <ul>
              {match.limitations.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </section>
        </div>
      )}
    </aside>
  );
}
