import type {
  AuthenticatedUser,
  GoogleLoginResponse,
  VerifySessionResponse,
} from "@/types/auth";

function errorMessageFromPayload(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const record = payload as Record<string, unknown>;
  const message = record.message;
  if (typeof message === "string" && message.trim()) {
    return message;
  }

  const detail = record.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  return fallback;
}

async function parseJson(response: Response) {
  const rawText = await response.text();
  if (!rawText) {
    return null;
  }

  try {
    return JSON.parse(rawText) as Record<string, unknown>;
  } catch {
    return { message: rawText };
  }
}

async function authRequest<TResponse>(
  pathname: string,
  init: RequestInit,
  fallbackErrorMessage: string,
) {
  const headers = new Headers(init.headers);

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(pathname, {
    cache: "no-store",
    credentials: "include",
    ...init,
    headers,
  });

  const payload = await parseJson(response);

  if (!response.ok) {
    throw new Error(errorMessageFromPayload(payload, fallbackErrorMessage));
  }

  return payload as TResponse;
}

function mapUser(user: Partial<AuthenticatedUser> | null | undefined): AuthenticatedUser {
  return {
    sub: user?.sub ?? "",
    email: user?.email ?? "",
    name: user?.name ?? "Project User",
    picture: user?.picture ?? "",
    exp: user?.exp,
  };
}

export async function loginWithGoogleCredential(
  credential: string,
): Promise<AuthenticatedUser> {
  const payload = await authRequest<GoogleLoginResponse>(
    "/api/auth/google-login",
    {
      method: "POST",
      body: JSON.stringify({ credential }),
    },
    "The authentication request failed.",
  );

  if (!payload?.status || !payload.user) {
    throw new Error(payload?.message || "The authentication request failed.");
  }

  return mapUser(payload.user);
}

export async function fetchAuthSession(): Promise<AuthenticatedUser> {
  const payload = await authRequest<VerifySessionResponse>(
    "/api/auth/session",
    {
      method: "GET",
    },
    "The authentication request failed.",
  );

  if (!payload?.status || !payload.user) {
    throw new Error(payload?.message || "The authentication request failed.");
  }

  return mapUser(payload.user);
}

export async function logoutAuthSession() {
  await authRequest(
    "/api/auth/logout",
    {
      method: "POST",
    },
    "Unable to sign out.",
  );
}
