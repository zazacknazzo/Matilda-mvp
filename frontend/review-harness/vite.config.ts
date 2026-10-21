import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";

// Isolated development server. Browser tests override HTTP with per-test state.
// This double deliberately provides no ownership/session/security guarantees.
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  cacheDir: "../node_modules/.vite-review",
  plugins: [
    react(),
    {
      name: "review-example-http",
      configureServer(server) {
        const states = new Map<string, ReturnType<typeof JSON.parse>>();
        server.middlewares.use((req, res, next) => {
          const match = req.url?.match(
            /^\/api\/studio\/previews\/([^/]+)(\/review)?$/,
          );
          if (!match) return next();
          const id = decodeURIComponent(match[1]);
          if (!states.has(id)) {
            const filename =
              id === "preview-empty"
                ? "no-coverage-preview.json"
                : "pending-preview.json";
            const preview = JSON.parse(
              readFileSync(
                new URL(
                  `../../tests/fixtures/studio/api/${filename}`,
                  import.meta.url,
                ),
                "utf8",
              ),
            );
            preview.preview_id = id;
            states.set(id, preview);
          }
          const preview = states.get(id);
          res.setHeader("Content-Type", "application/json");
          if (req.method === "GET" && !match[2])
            return res.end(JSON.stringify(preview));
          if (req.method !== "POST" || !match[2]) {
            res.statusCode = 405;
            return res.end();
          }
          let text = "";
          req.on("data", (chunk) => {
            text += chunk;
          });
          req.on("end", () => {
            try {
              const body = JSON.parse(text);
              if (body.review_revision !== preview.review_revision) {
                res.statusCode = 409;
                return res.end(
                  JSON.stringify({
                    detail: "Revisão obsoleta.",
                    code: "review_conflict",
                    retryable: false,
                  }),
                );
              }
              for (const decision of body.decisions) {
                const suggestion = preview.suggestions.find(
                  (item: { id: string }) => item.id === decision.suggestion_id,
                );
                if (!suggestion) throw new Error("Unknown ID");
                suggestion.status = decision.status;
                suggestion.pedagogical_rationale =
                  decision.pedagogical_rationale ??
                  suggestion.pedagogical_rationale;
                suggestion.suggested_content =
                  decision.suggested_content ?? suggestion.suggested_content;
              }
              preview.approved_objectives = body.approved_objectives;
              preview.review_revision += 1;
              preview.project.status = preview.suggestions.every(
                (item: { status: string }) => item.status !== "pending",
              )
                ? "reviewed"
                : "preview_ready";
              res.end(JSON.stringify(preview));
            } catch {
              res.statusCode = 422;
              res.end(
                JSON.stringify({
                  detail: "Revisão inválida.",
                  code: "invalid_input",
                  retryable: false,
                }),
              );
            }
          });
        });
      },
    },
  ],
  server: {
    host: "127.0.0.1",
    port: 5175,
    strictPort: true,
    fs: { allow: [fileURLToPath(new URL("../..", import.meta.url))] },
  },
});
