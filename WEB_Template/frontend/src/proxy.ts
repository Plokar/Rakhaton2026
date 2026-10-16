import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Next.js Middleware – ochrana chráněných rout
 *
 * Chráněné routy: /dashboard, /profile, /settings, ...
 * Pokud uživatel nemá JWT cookie → přesměrovat na /login
 */

const PROTECTED_PATHS = ['/dashboard'];
const AUTH_PATHS = ['/login', '/register', '/forgot-password', '/reset-password'];


export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get('access_token');
  const isAuthenticated = !!accessToken;

  // Přesměrovat nepřihlášené z chráněných stránek na login
  const isProtected = PROTECTED_PATHS.some((path) =>
    pathname.startsWith(path),
  );
  if (isProtected && !isAuthenticated) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Přesměrovat přihlášené z auth stránek na dashboard
  const isAuthPage = AUTH_PATHS.some((path) => pathname.startsWith(path));
  if (isAuthPage && isAuthenticated) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Spustit middleware na všech cestách kromě:
     * - _next/static (statické soubory)
     * - _next/image (optimalizace obrázků)
     * - favicon.ico, public assets
     * - api routes
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$|api/).*)',
  ],
};
