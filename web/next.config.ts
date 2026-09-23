import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Static export: plain files, served by Vercel / Cloudflare Pages (the API is a separate server)
  output: "export",
  trailingSlash: true,
};

export default nextConfig;
