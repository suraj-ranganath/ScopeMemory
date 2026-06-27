import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/health": "http://127.0.0.1:8080",
      "/auth": "http://127.0.0.1:8080",
      "/demo": "http://127.0.0.1:8080",
      "/fixtures": "http://127.0.0.1:8080",
      "/iam": "http://127.0.0.1:8080",
      "/index": "http://127.0.0.1:8080",
      "/mcp": "http://127.0.0.1:8080"
    }
  },
  build: {
    outDir: "dist",
    emptyOutDir: true
  }
});
