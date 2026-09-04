import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output keeps the production image small: only the runtime
  // code needed to serve the app, plus a runnable docker entrypoint.
  // Required by frontend/dockerfile.
  output: "standalone",
  experimental: {
    serverActions: {
      bodySizeLimit: "110mb",
    },
  },
};

export default nextConfig;
