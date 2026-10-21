import { createPortal } from "react-dom";
import type { LessonBundle } from "../types/lesson";
import { LessonPlan } from "./LessonPlan";
import "./lesson-print.css";

/** A direct body child so the host can hide its entire UI during native printing. */
export function LessonPrintView({ bundle }: { bundle: LessonBundle }) {
  return createPortal(
    <div className="lesson-print-view lesson-ui" aria-hidden="true">
      <LessonPlan bundle={bundle} />
    </div>,
    document.body,
  );
}
