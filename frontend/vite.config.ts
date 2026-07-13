import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig } from "vite";
import tsConfigPaths from "vite-tsconfig-paths";

// Plugins reconstruídos a partir do que o wrapper do Lovable embrulhava, sem
// dependência dele. Diferença deliberada: nitro em preset `node-server`
// (rodamos no homelab em container Node), não cloudflare.
export default defineConfig(({ command }) => ({
  server: {
    port: 3000,
    // Em dev, deixa /api same-origin: o browser chama /api/... na porta 3000 e
    // o Vite repassa para o backend FastAPI — cookies ficam first-party (lax),
    // sem dor de CORS. Em produção, ver VITE_API_URL em src/lib/api.ts.
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  plugins: [
    // tanstackStart injeta o router plugin, que precisa vir ANTES do plugin de
    // JSX (@vitejs/plugin-react) — ordem exigida pelo próprio build.
    tanstackStart({
      server: { entry: "server" },
      importProtection: {
        behavior: "error",
        client: {
          files: ["**/server/**"],
          specifiers: ["server-only"],
        },
      },
    }),
    viteReact(),
    tailwindcss(),
    tsConfigPaths({ projects: ["./tsconfig.json"] }),
    // nitro só no build — gera .output/server (node) + .output/public.
    ...(command === "build" ? [nitro({ defaultPreset: "node-server" })] : []),
  ],
}));
