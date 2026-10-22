import {
  ArrowDown,
  ArrowUpRight,
  BookOpen,
  FileCheck,
  Lightbulb,
  Users,
} from "lucide-react";
import type { Analysis, Match } from "../types";
import { citationLabels } from "./EvidenceInspector";

/** A reading order for catalog matches, not a claim of historical influence. */
export function GuidedMap({
  analysis,
  matches,
  selected,
  onSelect,
}: {
  analysis: Analysis;
  matches: Match[];
  selected: Match | null;
  onSelect: (match: Match) => void;
}) {
  return (
    <section
      className="guided-map"
      aria-label="Mapa simplificado da investigação"
    >
      <div className="map-intro">
        <span className="eyebrow">SIGA A LEITURA DE CIMA PARA BAIXO</span>
        <h2>Como essas histórias se conectam?</h2>
        <p>
          O artigo e as contribuições abaixo compartilham assuntos. Escolha uma
          história para consultar quem participou e as fontes.
        </p>
      </div>
      <div className="map-root">
        <BookOpen size={22} />
        <div>
          <span>1 · SEU ARTIGO</span>
          <h3>{analysis.paper.title}</h3>
          <small>
            {analysis.paper.year ?? "Ano não informado"} · DOI{" "}
            {analysis.paper.doi}
          </small>
        </div>
      </div>
      <div className="map-connector">
        <ArrowDown size={18} />
        <span>Assuntos em comum · não comprovam influência</span>
      </div>
      <div className="map-stories">
        {matches.map((match, index) => (
          <article
            className={
              "map-story" +
              (selected?.contribution.id === match.contribution.id
                ? " is-selected"
                : "")
            }
            key={match.contribution.id}
          >
            <div className="map-topics">
              <Lightbulb size={16} />
              <span>2 · ASSUNTOS EM COMUM</span>
            </div>
            <div className="map-topic-list">
              {match.matched_concepts.map((concept) => (
                <span key={concept.id}>{concept.name}</span>
              ))}
              {!match.matched_concepts.length && (
                <span>Consulte a explicação da relação</span>
              )}
            </div>
            <div className="map-story-heading">
              <span className="story-index">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <small>3 · CONTRIBUIÇÃO DOCUMENTADA</small>
                <h3>{match.contribution.title}</h3>
              </div>
            </div>
            <p className="map-people">
              <Users size={16} />
              {match.researchers.map((person) => person.name).join(" · ") ||
                "Participantes não informados"}
            </p>
            <p className="map-description">{match.explanation}</p>
            <span className="map-citation">
              {citationLabels[match.citation_status] || match.citation_status}
            </span>
            <button
              className="map-evidence-button"
              onClick={() => onSelect(match)}
              aria-pressed={selected?.contribution.id === match.contribution.id}
            >
              <FileCheck size={17} />
              <span>
                Ver história e {match.evidence.length}{" "}
                {match.evidence.length === 1 ? "fonte" : "fontes"}
              </span>
              <ArrowUpRight size={16} />
            </button>
          </article>
        ))}
      </div>
      {!matches.length && (
        <div className="map-empty">
          <h3>Nenhuma conexão para exibir</h3>
          <p>
            {analysis.contributions.length
              ? "Selecione todas as contribuições no filtro para ampliar a leitura."
              : "O catálogo atual não encontrou correspondências. Isso não indica ausência de contribuições femininas."}
          </p>
        </div>
      )}
      <p className="map-footnote">
        A numeração indica a ordem de leitura, não uma sequência histórica. A
        comparação de referências aparece em cada contribuição.
      </p>
    </section>
  );
}
