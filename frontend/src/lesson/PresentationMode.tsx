import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { LessonReference, LessonSlide } from "../types/lesson";
import { navigateSlides } from "./lesson-view";
import { SlideControls, SlideRenderer } from "./SlideRenderer";

export function PresentationMode({
  slides,
  references,
  index,
  onChange,
  onClose,
}: {
  slides: LessonSlide[];
  references: Map<string, LessonReference>;
  index: number;
  onChange: (index: number) => void;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDivElement>(null);
  const wasFullscreen = useRef(false);
  const [notice, setNotice] = useState("");
  useEffect(() => {
    const element = dialog.current;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.current?.focus();
    function fullscreenChanged() {
      if (document.fullscreenElement === dialog.current)
        wasFullscreen.current = true;
      else if (wasFullscreen.current) onClose();
    }
    document.addEventListener("fullscreenchange", fullscreenChanged);
    return () => {
      document.removeEventListener("fullscreenchange", fullscreenChanged);
      document.body.style.overflow = previousOverflow;
      if (document.fullscreenElement === element)
        void document.exitFullscreen().catch(() => {});
    };
  }, [onClose]);
  async function fullscreen() {
    try {
      if (!dialog.current?.requestFullscreen) throw new Error("unavailable");
      await dialog.current.requestFullscreen();
    } catch {
      setNotice(
        "Tela cheia indisponível. A apresentação continua nesta janela; use o zoom do navegador se necessário.",
      );
    }
  }
  return createPortal(
    <div
      className="lesson-presentation lesson-ui"
      ref={dialog}
      tabIndex={-1}
      role="dialog"
      aria-modal="true"
      aria-label="Apresentação da aula"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          onClose();
          return;
        }
        if (event.key === "Tab") {
          const items = dialog.current?.querySelectorAll<HTMLElement>(
            'button:not(:disabled), a[href], [tabindex="0"]',
          );
          if (items?.length) {
            const first = items[0],
              last = items[items.length - 1];
            if (
              event.shiftKey &&
              (document.activeElement === first ||
                document.activeElement === dialog.current)
            ) {
              event.preventDefault();
              last.focus();
            } else if (
              !event.shiftKey &&
              (document.activeElement === last ||
                document.activeElement === dialog.current)
            ) {
              event.preventDefault();
              first.focus();
            }
          }
        } else navigateSlides(event, index, slides.length, onChange);
      }}
    >
      <header className="lesson-presentation-toolbar">
        <span>Apresentação · notas ocultas</span>
        <div>
          <button type="button" onClick={() => void fullscreen()}>
            Tela cheia
          </button>
          <button type="button" onClick={onClose}>
            Sair da apresentação <kbd>Esc</kbd>
          </button>
        </div>
      </header>
      {notice ? (
        <p className="lesson-fullscreen-notice" role="status">
          {notice}
        </p>
      ) : null}
      <div className="lesson-projection">
        <SlideRenderer
          slide={slides[index]}
          references={references}
          position={index + 1}
          total={slides.length}
        />
      </div>
      <SlideControls index={index} total={slides.length} onChange={onChange} />
    </div>,
    document.body,
  );
}
