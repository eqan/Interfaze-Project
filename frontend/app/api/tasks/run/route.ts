import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/auth";
import { handleTaskRunRequest } from "@/lib/server/tasks/run-task";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value?.trim();
  const outcome = await handleTaskRunRequest(body, {
    authenticated: Boolean(token),
  });

  return NextResponse.json(outcome.body, {
    status: outcome.statusCode,
  });
}
