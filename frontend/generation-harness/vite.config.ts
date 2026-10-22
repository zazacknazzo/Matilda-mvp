import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  cacheDir: "../node_modules/.vite-generation",
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5177,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8017",
        timeout: 100000,
        proxyTimeout: 100000,
      },
    },
    fs: { allow: [fileURLToPath(new URL("../..", import.meta.url))] },
  },
});
