import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  // The default Forensics suite must remain runnable without a Gemini provider.
  testMatch: "investigation.spec.ts",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    headless: true,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  workers: 1,
});
