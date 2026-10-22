import type { LessonBundle } from "../types/lesson";

export async function getLesson(
  id: string,
  signal?: AbortSignal,
): Promise<LessonBundle> {
  const response = await fetch(
    `/api/studio/lessons/${encodeURIComponent(id)}`,
    {
      credentials: "same-origin",
      signal,
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error(
      response.status === 404
        ? "Aula indisponível ou sessão expirada."
        : "Não foi possível consultar a aula salva. Tente novamente.",
    );
  }
  return response.json();
}
