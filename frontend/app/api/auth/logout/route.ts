import { NextResponse } from "next/server";

import { handleLogoutRequest } from "@/lib/server/auth/session";
import { shouldUseSecureCookies } from "@/lib/server/auth/cookies";

export async function POST(request: Request) {
  const outcome = handleLogoutRequest({
    secureCookies: shouldUseSecureCookies(request.url),
  });

  const response = NextResponse.json(outcome.body, {
    status: outcome.statusCode,
  });

  if (outcome.cookie) {
    response.cookies.set(outcome.cookie.name, outcome.cookie.value, {
      httpOnly: true,
      maxAge: outcome.cookie.maxAgeSeconds,
      path: "/",
      sameSite: "lax",
      secure: outcome.cookie.secure,
    });
  }

  return response;
}
