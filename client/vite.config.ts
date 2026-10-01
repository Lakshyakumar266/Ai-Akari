import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    watch: {
      ignored: [
        "**/*.vrm",
        "**/characters/**",
        "**/public/characters/**",
      ],
    },
  },
});

/**
 * Vite Configuration
 * Configures React plugin, Tailwind CSS v4 compiler, and watcher exclusion patterns for 3D VRM assets.
 */
