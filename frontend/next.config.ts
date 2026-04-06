import path from "node:path";
import { fileURLToPath } from "node:url";
import type { NextConfig } from "next";

const configDir = path.dirname(fileURLToPath(import.meta.url));
const tailwindPackagePath = path.join(configDir, "node_modules", "tailwindcss");
const tailwindPostcssPackagePath = path.join(
  configDir,
  "node_modules",
  "@tailwindcss",
  "postcss"
);

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: configDir,
    resolveAlias: {
      tailwindcss: tailwindPackagePath,
      "@tailwindcss/postcss": tailwindPostcssPackagePath,
    },
  },
};

export default nextConfig;
