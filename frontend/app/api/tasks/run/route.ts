import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { AUTH_TOKEN_COOKIE } from "@/lib/auth";
import { getApiBaseUrl } from "@/lib/env";
import type {
  ExtractIdTaskInput,
  TaskRunErrorShape,
  TaskRunResponse,
} from "@/types/task";

type BackendExtractResponse = {
  status: boolean;
  message: string;
  result?: {
    first_name: string;
    last_name: string;
    dob: string;
    driver_licence_number: string;
  };
  meta?: {
    provider?: string;
    cached?: boolean;
    idempotency_key?: string;
  };
};

function isPublicHttpsUrl(value: string) {
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:") {
      return false;
    }

    const host = parsed.hostname.toLowerCase();
    return host !== "localhost" && !host.endsWith(".local");
  } catch {
    return false;
  }
}

function normalizeExtractIdInput(input: unknown): ExtractIdTaskInput {
  if (!input || typeof input !== "object") {
    throw new Error("Task input is required.");
  }

  const record = input as Record<string, unknown>;
  const imageUrl = typeof record.imageUrl === "string" ? record.imageUrl.trim() : "";
  const instruction =
    typeof record.instruction === "string"
      ? record.instruction.trim()
      : "Extract the details from this ID";
  const idempotencyKey =
    typeof record.idempotencyKey === "string" ? record.idempotencyKey.trim() : "";

  if (!isPublicHttpsUrl(imageUrl)) {
    throw new Error("imageUrl must be a public https URL.");
  }

  if (instruction.length < 10 || instruction.length > 500) {
    throw new Error("instruction must be between 10 and 500 characters.");
  }

  if (idempotencyKey && (idempotencyKey.length < 8 || idempotencyKey.length > 128)) {
    throw new Error("idempotencyKey must be between 8 and 128 characters.");
  }

  return {
    imageUrl,
    instruction,
    idempotencyKey: idempotencyKey || `extract-id-${crypto.randomUUID()}`,
  };
}

function detailToMessage(detail: unknown) {
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          const message = (item as Record<string, unknown>).msg;
          if (typeof message === "string") {
            return message;
          }
        }

        return null;
      })
      .filter(Boolean)
      .join(", ");
  }

  return "";
}

function buildErrorResponse({
  status,
  message,
  idempotencyKey,
  requestId,
  durationMs,
  code,
  retriable,
}: {
  status: number;
  message: string;
  idempotencyKey: string;
  requestId: string;
  durationMs: number;
  code: string;
  retriable: boolean;
}): NextResponse<TaskRunResponse> {
  return NextResponse.json(
    {
      status: false,
      message,
      task: "extract_id",
      result: null,
      meta: {
        requestId,
        provider: "interfaze",
        cached: false,
        idempotencyKey,
        durationMs,
        createdAt: new Date().toISOString(),
      },
      errors: [
        {
          code,
          message,
          retriable,
        } satisfies TaskRunErrorShape,
      ],
    },
    { status },
  );
}

export async function POST(request: Request) {
  const startedAt = Date.now();
  const requestId = crypto.randomUUID();

  let parsedInput: ExtractIdTaskInput;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    if (body.task !== "extract_id") {
      throw new Error("Only the extract_id task is currently supported.");
    }
    parsedInput = normalizeExtractIdInput(body.input);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid task request.";
    return buildErrorResponse({
      status: 400,
      message,
      idempotencyKey: "invalid-request",
      requestId,
      durationMs: Date.now() - startedAt,
      code: "invalid_request",
      retriable: false,
    });
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_TOKEN_COOKIE)?.value?.trim();
  if (!token) {
    return buildErrorResponse({
      status: 401,
      message: "Authentication is required before running extraction tasks.",
      idempotencyKey: parsedInput.idempotencyKey ?? "missing-auth",
      requestId,
      durationMs: Date.now() - startedAt,
      code: "auth_required",
      retriable: false,
    });
  }

  try {
    const backendResponse = await fetch(`${getApiBaseUrl()}/interfaze/extract-id`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        image_url: parsedInput.imageUrl,
        instruction: parsedInput.instruction,
        idempotency_key: parsedInput.idempotencyKey,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(20_000),
    });

    const payload = (await backendResponse.json()) as BackendExtractResponse | {
      detail?: unknown;
      message?: string;
    };
    const durationMs = Date.now() - startedAt;

    if (!backendResponse.ok) {
      const message =
        ("detail" in payload && detailToMessage(payload.detail)) ||
        ("message" in payload && typeof payload.message === "string" ? payload.message : "") ||
        "The extraction task failed.";

      return buildErrorResponse({
        status: backendResponse.status,
        message,
        idempotencyKey: parsedInput.idempotencyKey ?? "extract-id",
        requestId,
        durationMs,
        code: backendResponse.status >= 500 ? "provider_failure" : "task_rejected",
        retriable: backendResponse.status >= 500,
      });
    }

    const backendPayload = payload as BackendExtractResponse;

    return NextResponse.json<TaskRunResponse>({
      status: true,
      message: backendPayload.message || "Extraction completed.",
      task: "extract_id",
      result: backendPayload.result
        ? {
            firstName: backendPayload.result.first_name,
            lastName: backendPayload.result.last_name,
            dob: backendPayload.result.dob,
            driverLicenceNumber: backendPayload.result.driver_licence_number,
          }
        : null,
      meta: {
        requestId,
        provider: backendPayload.meta?.provider ?? "interfaze",
        cached: backendPayload.meta?.cached ?? false,
        idempotencyKey:
          backendPayload.meta?.idempotency_key ??
          parsedInput.idempotencyKey ??
          `extract-id-${requestId}`,
        durationMs,
        createdAt: new Date().toISOString(),
      },
      errors: [],
    });
  } catch (error) {
    const message =
      error instanceof Error && error.name === "TimeoutError"
        ? "The extraction task timed out."
        : "The extraction task could not reach the backend.";

    return buildErrorResponse({
      status: error instanceof Error && error.name === "TimeoutError" ? 504 : 502,
      message,
      idempotencyKey: parsedInput.idempotencyKey ?? `extract-id-${requestId}`,
      requestId,
      durationMs: Date.now() - startedAt,
      code: error instanceof Error && error.name === "TimeoutError" ? "timeout" : "network_error",
      retriable: true,
    });
  }
}
