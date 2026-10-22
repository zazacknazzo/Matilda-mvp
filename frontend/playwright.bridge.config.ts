import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const runtime = mkdtempSync(join(tmpdir(), "matilda-t06-"));
export default defineConfig({
  testDir: "./bridge-harness/tests",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5177",
    headless: true,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  webServer: [
    {
      command:
        "../.venv/bin/python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8017",
      url: "http://127.0.0.1:8017/api/health",
      reuseExistingServer: false,
      env: {
        MATILDA_DB: join(runtime, "test.db"),
        MATILDA_CACHE_TTL: "999999999",
        GEMINI_API_KEY: "",
      },
    },
    {
      command:
        "node node_modules/vite/bin/vite.js --config bridge-harness/vite.config.ts",
      url: "http://127.0.0.1:5177",
      reuseExistingServer: false,
    },
  ],
});
