import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for small production Docker images.
  output: "standalone",
};

export default nextConfig;
