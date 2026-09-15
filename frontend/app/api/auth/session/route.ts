import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/auth";
import {
  handleSessionRequest,
  type AuthSessionOutcome,
} from "@/lib/server/auth/session";
import { shouldUseSecureCookies } from "@/lib/server/auth/cookies";

function applyAuthCookie(response: NextResponse, outcome: AuthSessionOutcome) {
  if (!outcome.cookie) {
    return response;
  }

  response.cookies.set(outcome.cookie.name, outcome.cookie.value, {
    httpOnly: true,
    maxAge: outcome.cookie.maxAgeSeconds,
    path: "/",
    sameSite: "lax",
    secure: outcome.cookie.secure,
  });

  return response;
}

export async function GET(request: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value;
  const outcome = await handleSessionRequest(token, {
    secureCookies: shouldUseSecureCookies(request.url),
  });

  const response = NextResponse.json(outcome.body, {
    status: outcome.statusCode,
  });

  return applyAuthCookie(response, outcome);
}
