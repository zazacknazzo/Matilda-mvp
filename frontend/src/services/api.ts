import type { Paper, Analysis } from "../types";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      signal: AbortSignal.timeout(22000),
    });
  } catch {
    throw new Error(
      "Não foi possível conectar ao serviço. Verifique se o backend está em execução e tente novamente.",
    );
  }
  const body = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : "Não foi possível processar a consulta. Confira o DOI e tente novamente.",
    );
  return body;
}
export const retrievePaper = (doi: string) =>
  request<Paper>("/api/papers/" + encodeURIComponent(doi));
export const investigate = (doi: string) =>
  request<Analysis>("/api/analyses", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doi }),
  });

export const expandDiscovery = (id: string) =>
  request<Analysis>(`/api/analyses/${encodeURIComponent(id)}/discovery`, {
    method: "POST",
  });

export const getAnalysis = (id: string) =>
  request<Analysis>(`/api/analyses/${encodeURIComponent(id)}`);
