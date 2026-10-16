import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Standalone output pro Docker production build
  output: 'standalone',

  // Povolené vzory pro optimalizaci obrázků (next.js 15+)
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'https',
        hostname: '**.yourdomain.com',
      },
    ],
  },

  // Přesměrování API callů na backend (v dev prostředí)
  // V produkci řeší Traefik routing
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://backend:8000';
    return [
      // Proxy API calls na Django backend (volitelné – lze řešit i přímo)
      // {
      //   source: '/api/:path*',
      //   destination: `${apiUrl}/api/:path*`,
      // },
    ];
  },

  // Security headers (doplněk k Traefik middleware)
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },

  // Experimentální funkce
  experimental: {
    // Server Components optimalizace
  },
};

export default nextConfig;
