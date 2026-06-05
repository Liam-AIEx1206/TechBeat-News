import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  serverExternalPackages: ["pdf-parse", "officeparser"],
  experimental: {
    middlewareClientMaxBodySize: "250mb",
  },
  async rewrites() {
    return [
      {
        source: '/api-backend/:path*',
        destination: 'http://backend:8000/:path*',
      },
    ]
  },
};

export default nextConfig;

