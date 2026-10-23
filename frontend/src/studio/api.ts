import type {
  EnrichmentPreview,
  PreviewRequest,
  StudioErrorCode,
} from "../types/studio";

const messages: Record<StudioErrorCode, string> = {
  invalid_input: "Confira os campos e os limites da entrada.",
  not_found: "Prévia indisponível ou sessão expirada.",
  review_conflict: "O projeto mudou. Consulte a prévia salva antes de repetir.",
  generation_in_progress:
    "Uma operação Studio já está em andamento. Aguarde antes de repetir.",
  input_too_large:
    "O material excede o limite de tamanho ou tokens. Reduza a entrada.",
  session_limit:
    "Limite de cinco prévias por hora atingido. Aguarde antes de tentar novamente.",
  invalid_generation:
    "O provedor de IA retornou conteúdo inválido ou incompleto. O material foi preservado.",
  provider_unavailable:
    "O provedor de IA está indisponível ou recusou a chamada. O material foi preservado.",
  studio_not_configured:
    "Studio sem configuração de IA no backend. O material foi preservado; o Forensics continua disponível.",
  generation_timeout:
    "A prévia excedeu o prazo. O material foi preservado. Tente novamente explicitamente.",
};

export function studioErrorMessage(code: StudioErrorCode): string {
  return (
    messages[code] ||
    "Não foi possível consultar o Studio. O material foi preservado."
  );
}

export class StudioApiError extends Error {
  constructor(
    message: string,
    public projectId?: string,
  ) {
    super(message);
  }
}

async function request(
  path: string,
  body?: PreviewRequest,
): Promise<EnrichmentPreview> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 55000);
  try {
    const response = await fetch(`/api/studio/${path}`, {
      method: body ? "POST" : "GET",
      credentials: "same-origin",
      signal: controller.signal,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      let error: { code?: StudioErrorCode; project_id?: string } = {};
      try {
        error = await response.json();
      } catch {
        /* Do not display raw proxy errors. */
      }
      throw new StudioApiError(
        messages[error.code!] ||
          "Não foi possível consultar o Studio. O material foi preservado.",
        typeof error.project_id === "string" ? error.project_id : undefined,
      );
    }
    return (await response.json()) as EnrichmentPreview;
  } catch (error) {
    if (error instanceof StudioApiError) throw error;
    throw new StudioApiError(
      "Não foi possível confirmar a prévia. O material foi preservado. Consulte a prévia salva ou tente novamente.",
    );
  } finally {
    window.clearTimeout(timer);
  }
}

export const studioApi = {
  createPreview: (body: PreviewRequest) => request("preview", body),
  getPreview: (id: string) => request(`previews/${encodeURIComponent(id)}`),
};
