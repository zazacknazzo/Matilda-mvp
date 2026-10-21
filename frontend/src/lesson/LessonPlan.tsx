import type { LessonBundle } from "../types/lesson";
import { LessonBlocks, LessonSource } from "./LessonBlocks";
import { lessonIndex } from "./lesson-view";

function TextList({ values, empty }: { values: string[]; empty: string }) {
  return values.length ? (
    <ul>
      {values.map((text, i) => (
        <li key={i}>{text}</li>
      ))}
    </ul>
  ) : (
    <p>{empty}</p>
  );
}

export function LessonPlan({ bundle }: { bundle: LessonBundle }) {
  const index = lessonIndex(bundle);
  return (
    <article className="lesson-plan" aria-label="Plano de aula">
      <header>
        <p className="lesson-eyebrow">
          ROTEIRO DOCENTE / {bundle.metadata.duration_minutes} MINUTOS
        </p>
        <h2>Plano de aula</h2>
        <p>
          {bundle.metadata.title} · {bundle.metadata.subject} ·{" "}
          {bundle.metadata.education_level}
        </p>
      </header>
      <div className="lesson-plan-overview">
        <section>
          <h3>Objetivos de aprendizagem</h3>
          <ol>
            {bundle.metadata.learning_objectives.map((text, i) => (
              <li key={i}>{text}</li>
            ))}
          </ol>
        </section>
        <section>
          <h3>Conhecimentos prévios</h3>
          <TextList
            values={bundle.metadata.prior_knowledge}
            empty="Nenhum conhecimento prévio indicado."
          />
          <h3>Materiais necessários</h3>
          <TextList
            values={bundle.metadata.materials}
            empty="Nenhum material adicional indicado."
          />
        </section>
      </div>
      <h3 className="lesson-plan-sequence-title">Sequência da aula</h3>
      {bundle.sections.map((section, i) => {
        const start = bundle.sections
          .slice(0, i)
          .reduce((sum, item) => sum + item.duration_minutes, 0);
        return (
          <section className="lesson-plan-section" key={section.id}>
            <header>
              <span className="lesson-time">
                {start}–{start + section.duration_minutes} min
              </span>
              <h3>{section.title}</h3>
              <span>{section.duration_minutes} min</span>
            </header>
            <p className="lesson-objective-link">
              Objetivos:{" "}
              {section.objective_indexes
                .map((n) => bundle.metadata.learning_objectives[n])
                .join(" · ")}
            </p>
            <LessonBlocks
              blocks={section.explanation_blocks}
              references={index.references}
            />
            {section.slide_ids.map((id) => {
              const slide = index.slides.get(id)!;
              return (
                <section className="lesson-plan-slide" key={id}>
                  <h4>
                    Slide {index.orderedSlides.indexOf(slide) + 1} ·{" "}
                    {slide.title} <span>({slide.duration_minutes} min)</span>
                  </h4>
                  {slide.subtitle ? <p>{slide.subtitle}</p> : null}
                  <LessonBlocks
                    blocks={slide.content_blocks}
                    references={index.references}
                  />
                  <aside className="lesson-notes">
                    <h5>Notas do professor</h5>
                    <p>{slide.speaker_notes || "Nenhuma nota adicional."}</p>
                  </aside>
                </section>
              );
            })}
            {section.activity_ids.map((id) => {
              const activity = index.activities.get(id)!;
              return (
                <section className="lesson-activity" key={id}>
                  <p className="lesson-eyebrow">
                    ATIVIDADE /{" "}
                    {activity.type === "discussion"
                      ? "DISCUSSÃO"
                      : "COMPREENSÃO"}
                  </p>
                  <h4>{activity.prompt}</h4>
                  <p>
                    <strong>Orientação ao professor:</strong>{" "}
                    {activity.teacher_guidance}
                  </p>
                  <p>
                    Objetivos:{" "}
                    {activity.objective_indexes
                      .map((n) => bundle.metadata.learning_objectives[n])
                      .join(" · ")}
                  </p>
                  <h5>Critérios de avaliação</h5>
                  <TextList values={activity.assessment_criteria} empty="" />
                  <small>
                    Tempo incluído nesta seção; não somar novamente.
                  </small>
                </section>
              );
            })}
          </section>
        );
      })}
      <section>
        <h3>Referências documentais</h3>
        {bundle.references.length ? (
          bundle.references.map((reference) => (
            <LessonSource key={reference.id} reference={reference} />
          ))
        ) : (
          <p>
            Sem enriquecimentos científicos aprovados. Nenhuma atribuição
            histórica foi acrescentada.
          </p>
        )}
      </section>
      <section className="lesson-limitations">
        <h3>Limitações da aula</h3>
        <TextList
          values={bundle.limitations}
          empty="Nenhuma limitação registrada."
        />
      </section>
    </article>
  );
}
