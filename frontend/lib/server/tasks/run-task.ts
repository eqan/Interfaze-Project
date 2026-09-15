import { isIP } from "node:net";

import type {
  ExtractIdTaskInput,
  TaskRunErrorShape,
  TaskRunResponse,
} from "../../../types/task";

import {
  extractIdWithInterfaze,
  InterfazeNotConfiguredError,
  InterfazeProviderRequestError,
  InterfazeProviderTimeoutError,
  type InterfazeExecutionResult,
} from "../interfaze";
import { getInterfazeServerEnv } from "../interfaze-env";
import {
  getTaskResultCache,
  type CachedExtractIdTaskResult,
  type TaskResultCache,
} from "../task-cache";

export type TaskRouteOutcome = {
  body: TaskRunResponse;
  statusCode: number;
};

type TaskRunContext = {
  authenticated: boolean;
  cache?: TaskResultCache;
  executeExtractId?: (
    input: Pick<ExtractIdTaskInput, "imageUrl" | "instruction">,
  ) => Promise<InterfazeExecutionResult>;
  now?: () => Date;
  retryAttempts?: number;
  timeoutMs?: number;
  uuid?: () => string;
};

class ValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValidationError";
  }
}

function isLocalHost(hostname: string) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "::1";
}

function isPrivateIpv4Address(hostname: string) {
  if (hostname.startsWith("10.") || hostname.startsWith("127.")) {
    return true;
  }

  if (hostname.startsWith("192.168.")) {
    return true;
  }

  if (hostname === "0.0.0.0") {
    return true;
  }

  const octets = hostname.split(".").map((segment) => Number.parseInt(segment, 10));
  if (octets.length !== 4 || octets.some((octet) => Number.isNaN(octet))) {
    return false;
  }

  return octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31;
}

function isPrivateIpv6Address(hostname: string) {
  const normalized = hostname.toLowerCase();
  return (
    normalized === "::1" ||
    normalized === "::" ||
    normalized.startsWith("fc") ||
    normalized.startsWith("fd") ||
    normalized.startsWith("fe80:")
  );
}

function isPublicHttpsUrl(value: string) {
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:") {
      return false;
    }

    const hostname = parsed.hostname.toLowerCase();
    if (isLocalHost(hostname) || hostname.endsWith(".local")) {
      return false;
    }

    const ipVersion = isIP(hostname);
    if (ipVersion === 4 && isPrivateIpv4Address(hostname)) {
      return false;
    }

    if (ipVersion === 6 && isPrivateIpv6Address(hostname)) {
      return false;
    }

    return true;
  } catch {
    return false;
  }
}

function normalizeExtractIdInput(input: unknown, createUuid: () => string): ExtractIdTaskInput {
  if (!input || typeof input !== "object") {
    throw new ValidationError("Task input is required.");
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
    throw new ValidationError("imageUrl must be a public https URL.");
  }

  if (instruction.length < 10 || instruction.length > 500) {
    throw new ValidationError("instruction must be between 10 and 500 characters.");
  }

  if (idempotencyKey && (idempotencyKey.length < 8 || idempotencyKey.length > 128)) {
    throw new ValidationError("idempotencyKey must be between 8 and 128 characters.");
  }

  return {
    idempotencyKey: idempotencyKey || `extract-id-${createUuid()}`,
    imageUrl,
    instruction,
  };
}

function buildResponse(
  statusCode: number,
  params: {
    cached: boolean;
    code: string;
    createdAt: string;
    durationMs: number;
    idempotencyKey: string;
    message: string;
    requestId: string;
    retriable?: boolean;
    result?: CachedExtractIdTaskResult["result"] | null;
  },
): TaskRouteOutcome {
  const errors: TaskRunErrorShape[] =
    statusCode >= 400
      ? [
          {
            code: params.code,
            message: params.message,
            retriable: params.retriable ?? false,
          },
        ]
      : [];

  return {
    body: {
      errors,
      message: params.message,
      meta: {
        cached: params.cached,
        createdAt: params.createdAt,
        durationMs: params.durationMs,
        idempotencyKey: params.idempotencyKey,
        provider: "interfaze",
        requestId: params.requestId,
      },
      result: params.result ?? null,
      status: statusCode < 400,
      task: "extract_id",
    },
    statusCode,
  };
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number) {
  let timeoutId: NodeJS.Timeout | undefined;

  const timeoutPromise = new Promise<T>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(new InterfazeProviderTimeoutError());
    }, timeoutMs);
  });

  return Promise.race([promise, timeoutPromise]).finally(() => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
  });
}

function shouldRetry(error: unknown) {
  return (
    error instanceof InterfazeProviderTimeoutError ||
    (error instanceof InterfazeProviderRequestError && error.retriable)
  );
}

async function executeWithRetries(
  input: ExtractIdTaskInput,
  executeExtractId: NonNullable<TaskRunContext["executeExtractId"]>,
  timeoutMs: number,
  retryAttempts: number,
) {
  let lastError: unknown;

  for (let attempt = 0; attempt <= retryAttempts; attempt += 1) {
    try {
      return await withTimeout(
        executeExtractId({
          imageUrl: input.imageUrl,
          instruction: input.instruction,
        }),
        timeoutMs,
      );
    } catch (error) {
      lastError = error;
      if (!shouldRetry(error) || attempt === retryAttempts) {
        throw error;
      }
    }
  }

  throw lastError;
}

export async function handleTaskRunRequest(
  body: unknown,
  context: TaskRunContext,
): Promise<TaskRouteOutcome> {
  const environment = getInterfazeServerEnv();
  const now = context.now ?? (() => new Date());
  const createUuid = context.uuid ?? (() => crypto.randomUUID());
  const cache = context.cache ?? getTaskResultCache();
  const executeExtractId = context.executeExtractId ?? extractIdWithInterfaze;
  const timeoutMs = context.timeoutMs ?? environment.timeoutMs;
  const retryAttempts = context.retryAttempts ?? environment.retryAttempts;

  const startedAt = now();
  const requestId = createUuid();

  let input: ExtractIdTaskInput;
  try {
    if (!body || typeof body !== "object") {
      throw new ValidationError("Task body is required.");
    }

    const requestRecord = body as Record<string, unknown>;
    if (requestRecord.task !== "extract_id") {
      throw new ValidationError("Only the extract_id task is currently supported.");
    }

    input = normalizeExtractIdInput(requestRecord.input, createUuid);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Invalid task request.";
    return buildResponse(400, {
      cached: false,
      code: "invalid_request",
      createdAt: now().toISOString(),
      durationMs: now().getTime() - startedAt.getTime(),
      idempotencyKey: "invalid-request",
      message,
      requestId,
      retriable: false,
    });
  }

  if (!context.authenticated) {
    return buildResponse(401, {
      cached: false,
      code: "auth_required",
      createdAt: now().toISOString(),
      durationMs: now().getTime() - startedAt.getTime(),
      idempotencyKey: input.idempotencyKey ?? "missing-auth",
      message: "Authentication is required before running extraction tasks.",
      requestId,
      retriable: false,
    });
  }

  const cachedResult = cache.get(input.idempotencyKey ?? "");
  if (cachedResult) {
    return buildResponse(200, {
      cached: true,
      code: "ok",
      createdAt: cachedResult.createdAt,
      durationMs: now().getTime() - startedAt.getTime(),
      idempotencyKey: cachedResult.idempotencyKey,
      message: "Extraction completed from cache.",
      requestId,
      result: cachedResult.result,
    });
  }

  try {
    const execution = await executeWithRetries(
      input,
      executeExtractId,
      timeoutMs,
      retryAttempts,
    );

    const createdAt = now().toISOString();
    const cacheEntry: CachedExtractIdTaskResult = {
      createdAt,
      idempotencyKey: input.idempotencyKey ?? `extract-id-${requestId}`,
      provider: execution.provider,
      result: execution.result,
    };

    cache.set(
      cacheEntry.idempotencyKey,
      cacheEntry,
      environment.resultCacheTtlSeconds * 1000,
    );

    return buildResponse(200, {
      cached: false,
      code: "ok",
      createdAt,
      durationMs: now().getTime() - startedAt.getTime(),
      idempotencyKey: cacheEntry.idempotencyKey,
      message: "Extraction completed.",
      requestId,
      result: cacheEntry.result,
    });
  } catch (error) {
    const createdAt = now().toISOString();
    const durationMs = now().getTime() - startedAt.getTime();
    const idempotencyKey = input.idempotencyKey ?? `extract-id-${requestId}`;

    if (error instanceof InterfazeNotConfiguredError) {
      return buildResponse(503, {
        cached: false,
        code: "provider_unavailable",
        createdAt,
        durationMs,
        idempotencyKey,
        message: error.message,
        requestId,
        retriable: false,
      });
    }

    if (error instanceof InterfazeProviderTimeoutError) {
      return buildResponse(504, {
        cached: false,
        code: "provider_timeout",
        createdAt,
        durationMs,
        idempotencyKey,
        message: error.message,
        requestId,
        retriable: true,
      });
    }

    if (error instanceof InterfazeProviderRequestError) {
      return buildResponse(error.statusCode, {
        cached: false,
        code:
          error.statusCode === 429 ? "provider_rate_limited" : "provider_failure",
        createdAt,
        durationMs,
        idempotencyKey,
        message: error.message,
        requestId,
        retriable: error.retriable,
      });
    }

    return buildResponse(502, {
      cached: false,
      code: "provider_failure",
      createdAt,
      durationMs,
      idempotencyKey,
      message: "The extraction task failed unexpectedly.",
      requestId,
      retriable: true,
    });
  }
}
