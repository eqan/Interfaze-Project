import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const AUTH_TOKEN_COOKIE = "project_template_auth_token";

function isPublicPathname(pathname: string) {
  return (
    pathname === "/auth" ||
    pathname.startsWith("/api/auth/") ||
    pathname.startsWith("/api/web-extract/")
  );
}

function decodeBase64Url(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");

  try {
    return atob(padded);
  } catch {
    return null;
  }
}

function readTokenExpiry(token: string) {
  const [, payload] = token.split(".");

  if (!payload) {
    return null;
  }

  const decodedPayload = decodeBase64Url(payload);

  if (!decodedPayload) {
    return null;
  }

  try {
    const parsedPayload = JSON.parse(decodedPayload) as { exp?: number };
    return typeof parsedPayload.exp === "number" ? parsedPayload.exp : null;
  } catch {
    return null;
  }
}

function isUsableAuthToken(token: string | undefined) {
  if (!token) {
    return false;
  }

  if (token.split(".").length !== 3) {
    return false;
  }

  const expiry = readTokenExpiry(token);

  if (expiry === null) {
    return false;
  }

  return expiry > Date.now() / 1000;
}

export function proxy(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const publicPath = isPublicPathname(pathname);
  const token = request.cookies.get(AUTH_TOKEN_COOKIE)?.value;
  const hasUsableToken = isUsableAuthToken(token);

  if (!hasUsableToken && !publicPath) {
    const loginUrl = new URL("/auth", request.url);
    const nextTarget = `${pathname}${request.nextUrl.search}`;

    if (nextTarget !== "/auth") {
      loginUrl.searchParams.set("next", nextTarget);
    }

    const response = NextResponse.redirect(loginUrl);

    if (token) {
      response.cookies.set(AUTH_TOKEN_COOKIE, "", {
        maxAge: 0,
        path: "/",
      });
    }

    return response;
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)"],
};
