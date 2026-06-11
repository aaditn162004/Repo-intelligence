import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone output is only needed for Docker; Vercel handles its own output
  ...(process.env.VERCEL ? {} : { output: "standalone" }),
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.API_INTERNAL_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
