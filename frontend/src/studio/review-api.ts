import type { EnrichmentPreview, ReviewRequest } from "../types/studio";

/** T03 transport seam. The host supplies this port; no fixture fallback. */
export interface ReviewApi {
  getPreview(id: string, signal?: AbortSignal): Promise<EnrichmentPreview>;
  saveReview(
    id: string,
    request: ReviewRequest,
    signal?: AbortSignal,
  ): Promise<EnrichmentPreview>;
}

export class ReviewApiError extends Error {
  constructor(public readonly status: number) {
    super("Falha na API de revisão.");
    this.name = "ReviewApiError";
  }
}

export function reviewErrorMessage(error: unknown): string {
  if (error instanceof ReviewApiError) {
    if (error.status === 409)
      return "A revisão mudou ou há uma geração em andamento. Suas edições foram mantidas. Consulte a versão salva antes de tentar novamente.";
    if (error.status === 422)
      return "A revisão foi recusada: confira objetivos e decisões. Identificadores ou campos científicos inválidos não podem ser gravados. Suas edições foram mantidas.";
    if (error.status === 404)
      return "Prévia indisponível ou sessão expirada. Suas edições foram mantidas nesta tela.";
  }
  // Never render raw provider, transport or validation bodies (which may contain material).
  return "Não foi possível confirmar a gravação ou consulta. Suas edições foram mantidas. Consulte a versão salva antes de repetir a gravação.";
}

export function createReviewApi(fetcher: typeof fetch = fetch): ReviewApi {
  async function request(
    id: string,
    body?: ReviewRequest,
    signal?: AbortSignal,
  ) {
    const path = `/api/studio/previews/${encodeURIComponent(id)}`;
    const response = await fetcher(body ? `${path}/review` : path, {
      method: body ? "POST" : "GET",
      credentials: "same-origin",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal,
    });
    // The browser supplies Origin for writes. No session token is exposed to JS.
    if (!response.ok) throw new ReviewApiError(response.status);
    return response.json() as Promise<EnrichmentPreview>;
  }
  return {
    getPreview: (id, signal) => request(id, undefined, signal),
    saveReview: (id, body, signal) => request(id, body, signal),
  };
}
