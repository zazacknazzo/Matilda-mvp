import type { KeyboardEvent } from "react";
import type { ContentBlock, LessonBundle, LessonSlide } from "../types/lesson";

export const layoutLabels: Record<LessonSlide["layout"], string> = {
  TITLE: "Abertura",
  CONCEPT: "Conceitos",
  PROCESS: "Processo",
  SCIENTIST_SPOTLIGHT: "Ciência e autoria",
  QUESTION: "Discussão",
  SUMMARY: "Síntese",
};

export function safeSourceUrl(value: string): string | null {
  try {
    if (/[\s\u0000-\u001f\u007f]/u.test(value)) return null;
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) &&
      url.hostname &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function lessonIndex(bundle: LessonBundle) {
  const slides = new Map(bundle.slides.map((slide) => [slide.id, slide]));
  return {
    slides,
    activities: new Map(
      bundle.activities.map((activity) => [activity.id, activity]),
    ),
    references: new Map(
      bundle.references.map((reference) => [reference.id, reference]),
    ),
    orderedSlides: bundle.sections.flatMap((section) =>
      section.slide_ids.map((id) => slides.get(id)!),
    ),
  };
}

// Rendering safeguards for an already server-validated bundle, not a second API schema.
// Scientific eligibility, accepted decisions and canonical snapshots remain server-owned.
export function lessonRenderError(bundle: LessonBundle): string | null {
  try {
    if (
      bundle.schema_version !== 1 ||
      !bundle.slides.length ||
      !bundle.sections.length
    )
      return "Versão ou estrutura de aula inválida.";
    const index = lessonIndex(bundle);
    for (const collection of [
      bundle.sections,
      bundle.slides,
      bundle.activities,
      bundle.references,
    ]) {
      if (new Set(collection.map((item) => item.id)).size !== collection.length)
        return "A aula contém identificadores duplicados.";
    }
    const linkedSlides = bundle.sections.flatMap(
      (section) => section.slide_ids,
    );
    const linkedActivities = bundle.sections.flatMap(
      (section) => section.activity_ids,
    );
    if (
      new Set(linkedSlides).size !== bundle.slides.length ||
      linkedSlides.length !== bundle.slides.length ||
      new Set(linkedActivities).size !== bundle.activities.length ||
      linkedActivities.length !== bundle.activities.length
    )
      return "A sequência contém vínculos ausentes ou repetidos.";
    const used = new Set<string>();
    function checkBlocks(blocks: ContentBlock[]) {
      return blocks.every((block) => {
        switch (block.type) {
          case "text":
          case "question":
            return typeof block.text === "string";
          case "bullets":
          case "steps":
            return (
              Array.isArray(block.items) &&
              block.items.every((item) => typeof item === "string")
            );
          case "evidence_claim": {
            used.add(block.evidence_id);
            return (
              Object.keys(block).every((key) =>
                ["type", "evidence_id"].includes(key),
              ) && index.references.has(block.evidence_id)
            );
          }
          default:
            return false;
        }
      });
    }
    for (const reference of bundle.references) {
      if (
        !safeSourceUrl(reference.source_url) ||
        reference.verification_status !== "verified" ||
        !["documental", "historical"].includes(reference.source_type)
      )
        return "Fonte documental inválida ou não verificada.";
    }
    for (const section of bundle.sections) {
      if (
        !checkBlocks(section.explanation_blocks) ||
        section.slide_ids.some(
          (id) => index.slides.get(id)?.section_id !== section.id,
        ) ||
        section.activity_ids.some(
          (id) => index.activities.get(id)?.section_id !== section.id,
        )
      )
        return "A seção contém blocos ou vínculos inválidos.";
      if (
        section.slide_ids.reduce(
          (sum, id) => sum + index.slides.get(id)!.duration_minutes,
          0,
        ) !== section.duration_minutes
      )
        return "Os tempos dos slides não correspondem à seção.";
    }
    for (const slide of bundle.slides) {
      if (
        !Object.hasOwn(layoutLabels, slide.layout) ||
        !checkBlocks(slide.content_blocks)
      )
        return "O slide contém layout ou bloco inválido.";
      const evidence = new Set(
        slide.content_blocks.flatMap((block) =>
          block.type === "evidence_claim" ? [block.evidence_id] : [],
        ),
      );
      const contributions = new Set(
        [...evidence].map((id) => index.references.get(id)!.contribution_id),
      );
      if (
        evidence.size !== slide.evidence_ids.length ||
        slide.evidence_ids.some((id) => !evidence.has(id)) ||
        contributions.size !== slide.contribution_ids.length ||
        slide.contribution_ids.some((id) => !contributions.has(id))
      )
        return "As evidências do slide não correspondem aos blocos documentais.";
      const kinds = slide.content_blocks.map((block) => block.type);
      if (
        (slide.layout === "SCIENTIST_SPOTLIGHT" && !evidence.size) ||
        (slide.layout === "PROCESS" && !kinds.includes("steps")) ||
        (slide.layout === "QUESTION" && !kinds.includes("question"))
      )
        return "O conteúdo obrigatório do layout está ausente.";
    }
    if (
      used.size !== bundle.references.length ||
      bundle.references.some((reference) => !used.has(reference.id))
    )
      return "As fontes não correspondem às evidências utilizadas.";
    if (
      bundle.sections.reduce(
        (sum, section) => sum + section.duration_minutes,
        0,
      ) !== bundle.metadata.duration_minutes
    )
      return "A sequência não corresponde à duração da aula.";
    return null;
  } catch {
    return "Não foi possível resolver os dados da aula.";
  }
}

export function navigateSlides(
  event: KeyboardEvent<HTMLElement>,
  index: number,
  count: number,
  onChange: (index: number) => void,
) {
  const target = event.target;
  if (
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    (target instanceof HTMLElement &&
      (target.isContentEditable ||
        ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)))
  )
    return;
  const next = {
    ArrowRight: index + 1,
    PageDown: index + 1,
    ArrowLeft: index - 1,
    PageUp: index - 1,
    Home: 0,
    End: count - 1,
  }[event.key];
  if (next === undefined) return;
  event.preventDefault();
  onChange(Math.max(0, Math.min(count - 1, next)));
}
