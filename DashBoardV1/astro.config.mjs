// Sitio estático: Astro arma el HTML y los scripts; los datos se leen en el navegador desde /datos (S3).
import { defineConfig } from "astro/config";
import tailwindcss from "@tailwindcss/vite";

// En desarrollo, /api se envía a la distribución de CloudFront ya desplegada.
const API = process.env.AGRO_API ?? "https://d6wslbico5u76.cloudfront.net";
const proxy = { "/api": { target: API, changeOrigin: true, secure: true } };

export default defineConfig({
  output: "static",
  devToolbar: { enabled: false },
  build: { inlineStylesheets: "auto" },
  vite: {
    plugins: [tailwindcss()],
    server: { proxy },
    preview: { proxy },
  },
});
