export interface MarkdownDownload {
  blob: Blob;
  filename: string;
}
export interface LessonExportApi {
  getMarkdown(id: string, signal?: AbortSignal): Promise<MarkdownDownload>;
}

export function createLessonExportApi(
  fetcher: typeof fetch = fetch,
): LessonExportApi {
  return {
    async getMarkdown(id, signal) {
      const response = await fetcher(
        `/api/studio/lessons/${encodeURIComponent(id)}/export?format=markdown`,
        { credentials: "same-origin", signal },
      );
      if (!response.ok)
        throw new Error(
          response.status === 404
            ? "Aula indisponível ou sessão expirada. Consulte a aula antes de tentar novamente."
            : "Não foi possível exportar o Markdown. Tente novamente.",
        );
      if (
        !/^text\/markdown(?:;|$)/i.test(
          response.headers.get("Content-Type") || "",
        )
      )
        throw new Error(
          "A exportação não retornou um arquivo Markdown válido.",
        );
      const disposition = response.headers.get("Content-Disposition") || "";
      const name =
        /^(?:attachment);\s*filename="?([a-zA-Z0-9_-]{1,100}\.md)"?$/i.exec(
          disposition,
        )?.[1];
      const blob = await response.blob();
      if (signal?.aborted)
        throw new DOMException("Exportação cancelada.", "AbortError");
      return { blob, filename: name || "matilda-aula.md" };
    },
  };
}

export function downloadMarkdown({ blob, filename }: MarkdownDownload): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = /^[a-zA-Z0-9_-]{1,100}\.md$/i.test(filename)
    ? filename
    : "matilda-aula.md";
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
