import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/auth";
import { getAuthServerEnv, hasAuthSecretKey } from "@/lib/server/auth-env";
import { AuthJwtError, verifyProjectJwt } from "@/lib/server/auth/jwt";
import { handleTaskRunRequest } from "@/lib/server/tasks/run-task";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value?.trim();
  const env = getAuthServerEnv();

  let authenticated = false;

  if (token && hasAuthSecretKey(env)) {
    try {
      await verifyProjectJwt({
        secretKey: env.secretKey,
        token,
      });
      authenticated = true;
    } catch (error) {
      if (!(error instanceof AuthJwtError)) {
        throw error;
      }
    }
  }

  const outcome = await handleTaskRunRequest(body, {
    authenticated,
  });

  return NextResponse.json(outcome.body, {
    status: outcome.statusCode,
  });
}
