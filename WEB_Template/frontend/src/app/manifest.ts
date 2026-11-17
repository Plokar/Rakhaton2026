import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'MDTcore',
    short_name: 'MDTcore',
    description: 'Podklady pro multidisciplinární onkologickou komisi (MDT)',
    start_url: '/dashboard',
    display: 'standalone',
    background_color: '#f4f6f8',
    theme_color: '#0f766e',
    // T-383: z ikony na ploše rovnou na živé zasedání
    shortcuts: [{ name: 'Živě na MDT', short_name: 'Živě', url: '/dashboard/live', icons: [{ src: '/icon-192.png', sizes: '192x192' }] }],
    icons: [
      {
        src: '/icon-192.png',
        sizes: '192x192',
        type: 'image/png',
      },
      {
        src: '/icon-512.png',
        sizes: '512x512',
        type: 'image/png',
      },
    ],
  };
}
