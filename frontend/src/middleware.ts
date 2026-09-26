import { NextResponse, type NextRequest } from "next/server";

const APP_PATHS = ["/dashboard", "/scan", "/analyze", "/analysis", "/history", "/saved", "/compare", "/profile", "/settings"];
const AUTH_PATHS = ["/login", "/register"];

export function middleware(req: NextRequest) {
  const { pathname, search } = req.nextUrl;
  if (pathname.startsWith("/api/")) {
    // The rewrite proxy does not forward the client address; pass it explicitly (overwriting any
    // client-supplied value) so the backend can rate-limit per client.
    const headers = new Headers(req.headers);
    const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
    headers.set("x-client-ip", forwarded || req.headers.get("x-real-ip") || "unknown");
    // Proves to the backend that this request came through our proxy (see backend PROXY_SECRET).
    headers.delete("x-proxy-secret");
    if (process.env.PROXY_SECRET) headers.set("x-proxy-secret", process.env.PROXY_SECRET);
    return NextResponse.next({ request: { headers } });
  }
  const hasSession = Boolean(req.cookies.get("gi_session")?.value);
  if (!hasSession && APP_PATHS.some((p) => pathname === p || pathname.startsWith(`${p}/`))) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    url.search = `?next=${encodeURIComponent(pathname + search)}`;
    return NextResponse.redirect(url);
  }
  if (hasSession && AUTH_PATHS.includes(pathname)) {
    const url = req.nextUrl.clone();
    url.pathname = "/dashboard";
    url.search = "";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = { matcher: ["/api/:path*", "/((?!api|_next|favicon.ico|.*\\..*).*)"] };
