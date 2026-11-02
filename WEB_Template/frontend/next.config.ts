import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Standalone output pro Docker production build
  output: 'standalone',

  // ponytail: dev v Dockeru na Windows (WATCHPACK_POLLING z docker-compose.dev.yml) – Turbopack přes bind mount
  // nevidí nové soubory ("Module not found"); polling je podle docs poslední možnost, mimo kontejner se nezapne
  ...(process.env.WATCHPACK_POLLING === 'true' ? { watchOptions: { pollIntervalMs: 1000 } } : {}),

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

  // Django URL končí lomítkem: bez tohohle by Next /api/x/ přesměroval na /api/x (POST pak na backendu spadne)
  skipTrailingSlashRedirect: true,

  // Same-origin proxy (D-003): Vercel přepošle /api/* na backend, httpOnly cookies zůstanou na doméně frontendu
  async rewrites() {
    const backendUrl = (process.env.BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '');
    return [
      // :path* lomítko na konci zahodí, proto zvlášť varianta s lomítkem
      { source: '/api/:path*/', destination: `${backendUrl}/api/:path*/` },
      { source: '/api/:path*', destination: `${backendUrl}/api/:path*` },
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
