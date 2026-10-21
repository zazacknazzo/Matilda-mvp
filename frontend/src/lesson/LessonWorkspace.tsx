import { useCallback, useEffect, useRef, useState } from "react";
import type { LessonBundle } from "../types/lesson";
import {
  lessonIndex,
  lessonRenderError,
  layoutLabels,
  navigateSlides,
} from "./lesson-view";
import { LessonPlan } from "./LessonPlan";
import { PresentationMode } from "./PresentationMode";
import { SlideControls, SlideRenderer } from "./SlideRenderer";
import "./lesson.css";

export function LessonWorkspace({ bundle }: { bundle: LessonBundle }) {
  const error = lessonRenderError(bundle);
  return error ? (
    <div className="lesson-ui lesson-invalid" role="alert">
      <h2>Aula indisponível para apresentação</h2>
      <p>{error}</p>
      <p>Confira o bundle validado antes de continuar.</p>
    </div>
  ) : (
    <ValidatedWorkspace key={bundle.lesson_bundle_id} bundle={bundle} />
  );
}

function ValidatedWorkspace({ bundle }: { bundle: LessonBundle }) {
  const [view, setView] = useState<"slides" | "plan">("slides");
  const [selected, setSelected] = useState(0);
  const [presenting, setPresenting] = useState(false);
  const launch = useRef<HTMLButtonElement>(null);
  const previouslyPresenting = useRef(false);
  useEffect(() => {
    if (!presenting && previouslyPresenting.current) launch.current?.focus();
    previouslyPresenting.current = presenting;
  }, [presenting]);
  const closePresentation = useCallback(() => setPresenting(false), []);
  const index = lessonIndex(bundle);
  const current = Math.min(selected, index.orderedSlides.length - 1);
  const slide = index.orderedSlides[current];
  return (
    <>
      <main className="lesson-ui lesson-workspace" inert={presenting}>
        <header className="lesson-workspace-header">
          <div>
            <p className="lesson-eyebrow">MATILDA / CADERNO DE AULA</p>
            <h1>{bundle.metadata.title}</h1>
            <p>
              {bundle.metadata.subject} · {bundle.metadata.education_level} ·{" "}
              {bundle.metadata.duration_minutes} minutos
            </p>
          </div>
          <button
            ref={launch}
            type="button"
            className="lesson-primary"
            onClick={() => setPresenting(true)}
          >
            Apresentar aula ↗
          </button>
        </header>
        <nav className="lesson-view-switch" aria-label="Visualização da aula">
          <button
            type="button"
            aria-pressed={view === "slides"}
            onClick={() => setView("slides")}
          >
            Slides <span>{bundle.slides.length}</span>
          </button>
          <button
            type="button"
            aria-pressed={view === "plan"}
            onClick={() => setView("plan")}
          >
            Plano de aula
          </button>
          <span>Mesma aula, duas formas de acompanhar.</span>
        </nav>
        {view === "plan" ? (
          <LessonPlan bundle={bundle} />
        ) : (
          <div className="lesson-editor">
            <nav className="lesson-outline" aria-label="Sequência de slides">
              <p className="lesson-eyebrow">SEQUÊNCIA</p>
              {index.orderedSlides.map((item, n) => (
                <button
                  type="button"
                  key={item.id}
                  aria-current={current === n ? "step" : undefined}
                  onClick={() => setSelected(n)}
                >
                  <span className="lesson-outline-number">
                    {String(n + 1).padStart(2, "0")}
                  </span>
                  <span>
                    <strong>{item.title}</strong>
                    <small>
                      {layoutLabels[item.layout]} · {item.duration_minutes} min
                    </small>
                  </span>
                </button>
              ))}
            </nav>
            <section
              className="lesson-preview"
              aria-label="Prévia dos slides"
              tabIndex={0}
              onKeyDown={(event) =>
                navigateSlides(
                  event,
                  current,
                  index.orderedSlides.length,
                  setSelected,
                )
              }
            >
              <SlideRenderer
                slide={slide}
                references={index.references}
                position={current + 1}
                total={index.orderedSlides.length}
              />
              <SlideControls
                index={current}
                total={index.orderedSlides.length}
                onChange={setSelected}
              />
              <p className="lesson-keyboard-help">
                Use ← → para navegar, Home para o início e End para o último
                slide.
              </p>
              <aside className="lesson-notes" aria-label="Notas do professor">
                <h3>
                  Notas do professor{" "}
                  <span>Somente neste painel e no plano</span>
                </h3>
                <p>{slide.speaker_notes || "Nenhuma nota adicional."}</p>
              </aside>
            </section>
          </div>
        )}
        {view === "slides" ? (
          <section className="lesson-limitations">
            <h2>Limitações da aula</h2>
            <ul>
              {bundle.limitations.map((text, n) => (
                <li key={n}>{text}</li>
              ))}
            </ul>
            {!bundle.references.length ? (
              <p>
                Sem enriquecimentos científicos aprovados. Nenhuma atribuição
                histórica foi acrescentada.
              </p>
            ) : null}
          </section>
        ) : null}
      </main>
      {presenting ? (
        <PresentationMode
          slides={index.orderedSlides}
          references={index.references}
          index={current}
          onChange={setSelected}
          onClose={closePresentation}
        />
      ) : null}
    </>
  );
}
