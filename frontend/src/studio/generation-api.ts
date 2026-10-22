import type {
  EnrichmentPreview,
  GenerateRequest,
  StudioErrorCode,
} from "../types/studio";
import type { LessonBundle } from "../types/lesson";

export interface GenerationApi {
  getPreview(id: string, signal?: AbortSignal): Promise<EnrichmentPreview>;
  generate(
    request: GenerateRequest,
    key: string,
    signal?: AbortSignal,
  ): Promise<LessonBundle>;
}

const messages: Record<StudioErrorCode, string> = {
  invalid_input: "Confira a solicitação de geração.",
  not_found: "Prévia indisponível ou sessão expirada.",
  review_conflict: "A revisão mudou. Volte à revisão antes de gerar.",
  generation_in_progress:
    "Uma geração já está em andamento. Consulte o estado.",
  input_too_large: "A entrada excede os limites de tamanho ou tokens.",
  session_limit:
    "Limite de gerações por hora atingido. Aguarde antes de tentar novamente.",
  invalid_generation:
    "O provedor retornou uma aula inválida ou incompleta. A revisão foi preservada.",
  provider_unavailable: "Provedor indisponível. A revisão foi preservada.",
  studio_not_configured: "O provedor precisa ser configurado no backend.",
  generation_timeout:
    "Não foi possível confirmar a geração dentro do prazo. Consulte o estado antes de repetir.",
};
export function generationMessage(code: StudioErrorCode): string {
  return (
    messages[code] ||
    "Não foi possível confirmar a operação. Consulte o estado salvo."
  );
}
export class GenerationApiError extends Error {
  constructor(
    public readonly code: StudioErrorCode,
    public readonly retryable = false,
  ) {
    super(generationMessage(code));
  }
}

export function createGenerationApi(
  fetcher: typeof fetch = fetch,
): GenerationApi {
  async function call(
    path: string,
    body?: GenerateRequest,
    key?: string,
    external?: AbortSignal,
  ) {
    const controller = new AbortController();
    const abort = () => controller.abort();
    if (external?.aborted) controller.abort();
    external?.addEventListener("abort", abort, { once: true });
    const timer = window.setTimeout(abort, body ? 85000 : 55000);
    try {
      const response = await fetcher(`/api/studio/${path}`, {
        method: body ? "POST" : "GET",
        credentials: "same-origin",
        signal: controller.signal,
        headers: body
          ? { "Content-Type": "application/json", "Idempotency-Key": key! }
          : undefined,
        body: body
          ? JSON.stringify({
              preview_id: body.preview_id,
              review_revision: body.review_revision,
              accepted_suggestion_ids: body.accepted_suggestion_ids,
            })
          : undefined,
      });
      if (!response.ok) {
        let payload: { code?: StudioErrorCode; retryable?: boolean } = {};
        try {
          payload = await response.json();
        } catch {
          /* Never display raw proxy responses. */
        }
        throw new GenerationApiError(
          payload.code && Object.hasOwn(messages, payload.code)
            ? payload.code
            : "provider_unavailable",
          payload.retryable === true,
        );
      }
      return await response.json();
    } catch (error) {
      if (error instanceof GenerationApiError) throw error;
      throw new GenerationApiError(
        controller.signal.aborted
          ? "generation_timeout"
          : "provider_unavailable",
        true,
      );
    } finally {
      window.clearTimeout(timer);
      external?.removeEventListener("abort", abort);
    }
  }
  return {
    getPreview: (id, signal) =>
      call(`previews/${encodeURIComponent(id)}`, undefined, undefined, signal),
    generate: (request, key, signal) => call("generate", request, key, signal),
  };
}
