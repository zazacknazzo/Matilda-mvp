import type { LessonReference, LessonSlide } from "../types/lesson";
import { LessonBlocks } from "./LessonBlocks";
import { layoutLabels } from "./lesson-view";

export function SlideRenderer({
  slide,
  references,
  position,
  total,
}: {
  slide: LessonSlide;
  references: Map<string, LessonReference>;
  position: number;
  total: number;
}) {
  return (
    <article
      className={`lesson-slide lesson-layout-${slide.layout.toLowerCase()}`}
      data-layout={slide.layout}
      aria-label={`Slide ${position} de ${total}: ${slide.title}`}
      tabIndex={0}
    >
      <div className="lesson-slide-top">
        <span>MATILDA / CIÊNCIA EM CONTEXTO</span>
        <span>{layoutLabels[slide.layout]}</span>
      </div>
      <div className="lesson-slide-body">
        <p className="lesson-eyebrow">
          {String(position).padStart(2, "0")} / {layoutLabels[slide.layout]}
        </p>
        <h2>{slide.title}</h2>
        {slide.subtitle ? (
          <p className="lesson-slide-subtitle">{slide.subtitle}</p>
        ) : null}
        <LessonBlocks blocks={slide.content_blocks} references={references} />
      </div>
      <footer className="lesson-slide-footer">
        <span>{slide.duration_minutes} min</span>
        <span>
          {position} / {total}
        </span>
      </footer>
    </article>
  );
}

export function SlideControls({
  index,
  total,
  onChange,
}: {
  index: number;
  total: number;
  onChange: (index: number) => void;
}) {
  return (
    <nav className="lesson-controls" aria-label="Navegação dos slides">
      <button
        type="button"
        disabled={index === 0}
        onClick={() => onChange(index - 1)}
        aria-label="Slide anterior"
      >
        ← Anterior
      </button>
      <div className="lesson-progress">
        <span role="status" aria-live="polite" aria-atomic="true">
          Slide {index + 1} de {total}
        </span>
        <progress
          value={index + 1}
          max={total}
          aria-label="Progresso da apresentação"
        />
      </div>
      <button
        type="button"
        disabled={index === total - 1}
        onClick={() => onChange(index + 1)}
        aria-label="Próximo slide"
      >
        Próximo →
      </button>
    </nav>
  );
}
