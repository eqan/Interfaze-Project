export const AUTH_TOKEN_COOKIE = "project_template_auth_token";

export function isPublicPathname(pathname: string) {
  return (
    pathname === "/auth" ||
    pathname.startsWith("/api/auth/") ||
    pathname.startsWith("/api/web-extract/")
  );
}

export function sanitizeRedirectTarget(target: string | null | undefined) {
  if (!target || !target.startsWith("/") || target.startsWith("//")) {
    return "/";
  }

  return target;
}
