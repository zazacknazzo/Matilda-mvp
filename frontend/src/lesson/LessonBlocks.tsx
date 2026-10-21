import type { ContentBlock, LessonReference } from "../types/lesson";
import { safeSourceUrl } from "./lesson-view";

export function LessonSource({ reference }: { reference: LessonReference }) {
  const url = safeSourceUrl(reference.source_url);
  return (
    <figure className="lesson-evidence">
      <figcaption className="lesson-eyebrow">Afirmação documentada</figcaption>
      <blockquote>{reference.claim_supported}</blockquote>
      <p className="lesson-authors">
        <strong>Participantes da publicação</strong>
        <br />
        {reference.participants.join(" · ")}
      </p>
      <p className="lesson-source-link">
        {url ? (
          <a href={url} target="_blank" rel="noopener noreferrer">
            {reference.source_title} ↗
          </a>
        ) : (
          <span>Link indisponível · {reference.source_title}</span>
        )}
      </p>
      <p className="lesson-source-location">{reference.excerpt_or_location}</p>
      <ul className="lesson-source-limits">
        {reference.limitations.map((text, i) => (
          <li key={i}>{text}</li>
        ))}
      </ul>
      <small>
        {reference.from_cache ? "Fonte em cache" : "Fonte recuperada"} ·{" "}
        {reference.retrieved_at}
      </small>
    </figure>
  );
}

export function LessonBlocks({
  blocks,
  references,
}: {
  blocks: ContentBlock[];
  references: Map<string, LessonReference>;
}) {
  return (
    <div className="lesson-blocks">
      {blocks.map((block, i) => {
        switch (block.type) {
          case "text":
            return <p key={i}>{block.text}</p>;
          case "question":
            return (
              <p className="lesson-question" key={i}>
                {block.text}
              </p>
            );
          case "bullets":
            return (
              <ul className="lesson-bullets" key={i}>
                {block.items.map((item, n) => (
                  <li key={n}>{item}</li>
                ))}
              </ul>
            );
          case "steps":
            return (
              <ol className="lesson-steps" key={i}>
                {block.items.map((item, n) => (
                  <li key={n}>
                    <span>{String(n + 1).padStart(2, "0")}</span>
                    {item}
                  </li>
                ))}
              </ol>
            );
          case "evidence_claim": {
            const reference = references.get(block.evidence_id);
            return reference ? (
              <LessonSource key={i} reference={reference} />
            ) : (
              <p role="alert" key={i}>
                Evidência indisponível. Confira a aula validada.
              </p>
            );
          }
          default:
            return (
              <p role="alert" key={i}>
                Bloco não suportado.
              </p>
            );
        }
      })}
    </div>
  );
}
