import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./review-harness/tests",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5175",
    headless: true,
    viewport: { width: 1440, height: 1050 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  webServer: {
    command:
      "node node_modules/vite/bin/vite.js --config review-harness/vite.config.ts",
    url: "http://127.0.0.1:5175",
    reuseExistingServer: false,
    timeout: 30000,
  },
});
