import { NextResponse } from "next/server";

import {
  handleGoogleLoginRequest,
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

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const outcome = await handleGoogleLoginRequest(body, {
    secureCookies: shouldUseSecureCookies(request.url),
  });

  const response = NextResponse.json(outcome.body, {
    status: outcome.statusCode,
  });

  return applyAuthCookie(response, outcome);
}
