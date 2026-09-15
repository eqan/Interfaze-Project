import { NextResponse } from "next/server";

import { handleWebExtractRequest } from "@/lib/server/web-extract/run";

export async function POST(request: Request) {
  const body = await request.json().catch(() => null);
  const outcome = await handleWebExtractRequest(body);

  return NextResponse.json(outcome.body, {
    status: outcome.statusCode,
  });
}
