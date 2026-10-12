import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { viteSingleFile } from "vite-plugin-singlefile";

// One self-contained index.html: module scripts and fetch() are blocked under file:// in
// Chromium, so all JS/CSS/data are inlined. The same build works on any static host.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss(), viteSingleFile()],
  build: { outDir: "dist", assetsInlineLimit: 100_000_000, chunkSizeWarningLimit: 20_000 },
});
