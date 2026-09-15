import { AUTH_TOKEN_COOKIE } from "@/lib/auth";

export type AuthCookieDescriptor = {
  name: string;
  options: {
    httpOnly: true;
    maxAge: number;
    path: "/";
    sameSite: "lax";
    secure: boolean;
  };
  value: string;
};

export type AuthCookieOptions = {
  maxAgeSeconds: number;
  secure: boolean;
  value: string;
};

export function buildAuthSessionCookie({
  maxAgeSeconds,
  secure,
  value,
}: AuthCookieOptions): AuthCookieDescriptor {
  return {
    name: AUTH_TOKEN_COOKIE,
    value,
    options: {
      httpOnly: true,
      maxAge: Math.max(0, maxAgeSeconds),
      path: "/",
      sameSite: "lax",
      secure,
    },
  };
}

export function buildClearedAuthSessionCookie(secure: boolean) {
  return buildAuthSessionCookie({
    maxAgeSeconds: 0,
    secure,
    value: "",
  });
}

export function shouldUseSecureCookies(requestUrl: string) {
  try {
    return new URL(requestUrl).protocol === "https:";
  } catch {
    return false;
  }
}

export function getCookieMaxAgeSeconds(exp?: number, nowMs = Date.now()) {
  if (!exp) {
    return 60 * 60 * 24 * 7;
  }

  const remaining = Math.floor(exp - nowMs / 1000);
  return remaining > 0 ? remaining : 0;
}
