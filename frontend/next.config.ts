import type { NextConfig } from "next";

// Proxy /api/* to the Flask backend so the browser only ever talks to one origin.
// This keeps httpOnly cookies same-origin (see SPEC section 13).
const nextConfig: NextConfig = {
  async rewrites() {
    const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
