import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

// Pin the workspace root to this folder. Without it, Next walks up and can pick
// a stray lockfile in a parent directory as the project root.
const here = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  turbopack: { root: here },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
