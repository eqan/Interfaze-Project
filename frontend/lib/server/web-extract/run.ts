import { isIP } from "node:net";

import { getApiBaseUrl } from "@/lib/env";
import type {
  WebExtractCommand,
  WebExtractErrorShape,
  WebExtractInput,
  WebExtractResponse,
  WebExtractResult,
} from "@/types/web-extract";

export type WebExtractRouteOutcome = {
  body: WebExtractResponse;
  statusCode: number;
};

export type BackendExtractCall = {
  body: unknown;
  statusCode: number;
};

type WebExtractContext = {
  callBackend?: (input: WebExtractInput) => Promise<BackendExtractCall>;
  now?: () => Date;
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

function asRecord(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {};
  }

  return value as Record<string, unknown>;
}

function readString(record: Record<string, unknown>, camel: string, snake: string) {
  const camelValue = record[camel];
  if (typeof camelValue === "string") {
    return camelValue;
  }

  const snakeValue = record[snake];
  return typeof snakeValue === "string" ? snakeValue : "";
}

function readNumber(record: Record<string, unknown>, camel: string, snake: string) {
  const camelValue = record[camel];
  if (typeof camelValue === "number" && Number.isFinite(camelValue)) {
    return camelValue;
  }

  const snakeValue = record[snake];
  return typeof snakeValue === "number" && Number.isFinite(snakeValue) ? snakeValue : 0;
}

function readBoolean(record: Record<string, unknown>, camel: string, snake: string) {
  const camelValue = record[camel];
  if (typeof camelValue === "boolean") {
    return camelValue;
  }

  const snakeValue = record[snake];
  return typeof snakeValue === "boolean" ? snakeValue : false;
}

function readStringList(record: Record<string, unknown>, camel: string, snake: string) {
  const camelValue = record[camel];
  if (Array.isArray(camelValue)) {
    return camelValue.filter((item): item is string => typeof item === "string");
  }

  const snakeValue = record[snake];
  return Array.isArray(snakeValue)
    ? snakeValue.filter((item): item is string => typeof item === "string")
    : [];
}

function mapCommands(value: unknown): WebExtractCommand[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((item) => {
    const record = asRecord(item);
    const name = typeof record.name === "string" ? record.name : "";
    const selector = typeof record.selector === "string" ? record.selector : "";
    if (!name || !selector) {
      return [];
    }

    return [
      {
        attr: typeof record.attr === "string" ? record.attr : "text",
        many: record.many === true,
        name,
        selector,
      },
    ];
  });
}

function mapErrors(value: unknown): WebExtractErrorShape[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.flatMap((item) => {
    const record = asRecord(item);
    const message = typeof record.message === "string" ? record.message : "";
    if (!message) {
      return [];
    }

    return [
      {
        code: typeof record.code === "string" ? record.code : "EXTRACT_FAILED",
        message,
        retriable: record.retriable === true,
      },
    ];
  });
}

function mapResult(value: unknown): WebExtractResult | null {
  const record = asRecord(value);
  if (!record.url && !record.data && !record.commands) {
    return null;
  }

  return {
    commands: mapCommands(record.commands),
    confidence: readNumber(record, "confidence", "confidence"),
    data:
      record.data && typeof record.data === "object" && !Array.isArray(record.data)
        ? (record.data as Record<string, unknown>)
        : {},
    url: typeof record.url === "string" ? record.url : "",
  };
}

function mapBackendPayload(
  payload: unknown,
  fallback: {
    createdAt: string;
    idempotencyKey: string;
    message: string;
    requestId: string;
  },
): WebExtractResponse {
  const record = asRecord(payload);
  const metaRecord = asRecord(record.meta);
  const errors = mapErrors(record.errors);
  const message =
    (typeof record.message === "string" && record.message) ||
    errors[0]?.message ||
    fallback.message;

  return {
    errors,
    message,
    meta: {
      cached: readBoolean(metaRecord, "cached", "cached"),
      createdAt: fallback.createdAt,
      durationMs: readNumber(metaRecord, "durationMs", "duration_ms"),
      idempotencyKey:
        readString(metaRecord, "idempotencyKey", "idempotency_key") ||
        fallback.idempotencyKey,
      provider: readString(metaRecord, "provider", "provider") || "local-html+deepseek",
      regionPasses: readNumber(metaRecord, "regionPasses", "region_passes"),
      requestId: readString(metaRecord, "requestId", "request_id") || fallback.requestId,
      siteType: readString(metaRecord, "siteType", "site_type"),
      toolsUsed: readStringList(metaRecord, "toolsUsed", "tools_used"),
      truncated: readBoolean(metaRecord, "truncated", "truncated"),
      confidence: readNumber(metaRecord, "confidence", "confidence"),
      checkAttempts: readNumber(metaRecord, "checkAttempts", "check_attempts"),
    },
    result: mapResult(record.result),
    status: record.status === true,
    task: "extract_page",
  };
}

function normalizeInput(body: unknown, createUuid: () => string): WebExtractInput {
  if (!body || typeof body !== "object") {
    throw new ValidationError("url and prompt are required.");
  }

  const record = body as Record<string, unknown>;
  const url = typeof record.url === "string" ? record.url.trim() : "";
  const prompt = typeof record.prompt === "string" ? record.prompt.trim() : "";
  const idempotencyKey =
    typeof record.idempotencyKey === "string" ? record.idempotencyKey.trim() : "";

  if (!isPublicHttpsUrl(url)) {
    throw new ValidationError("url must be a public https URL.");
  }

  if (!prompt || prompt.length > 500) {
    throw new ValidationError("prompt must be between 1 and 500 characters.");
  }

  if (idempotencyKey && (idempotencyKey.length < 8 || idempotencyKey.length > 128)) {
    throw new ValidationError("idempotencyKey must be between 8 and 128 characters.");
  }

  return {
    idempotencyKey: idempotencyKey || `extract-page-${createUuid()}`,
    prompt,
    url,
  };
}

function buildFailure(
  statusCode: number,
  params: {
    code: string;
    createdAt: string;
    idempotencyKey: string;
    message: string;
    requestId: string;
    retriable?: boolean;
  },
): WebExtractRouteOutcome {
  return {
    body: {
      errors: [
        {
          code: params.code,
          message: params.message,
          retriable: params.retriable ?? false,
        },
      ],
      message: params.message,
      meta: {
        cached: false,
        createdAt: params.createdAt,
        durationMs: 0,
        idempotencyKey: params.idempotencyKey,
        provider: "local-html+deepseek",
        regionPasses: 0,
        requestId: params.requestId,
        siteType: "",
        toolsUsed: [],
        truncated: false,
        confidence: 0,
        checkAttempts: 0,
      },
      result: null,
      status: false,
      task: "extract_page",
    },
    statusCode,
  };
}

async function defaultCallBackend(
  input: WebExtractInput,
  timeoutMs: number,
): Promise<BackendExtractCall> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${getApiBaseUrl()}/web-extract/extract-page`, {
      body: JSON.stringify({
        idempotencyKey: input.idempotencyKey,
        prompt: input.prompt,
        url: input.url,
      }),
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
      },
      method: "POST",
      signal: controller.signal,
    });

    const payload = await response.json().catch(() => null);
    return {
      body: payload,
      statusCode: response.status,
    };
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function handleWebExtractRequest(
  body: unknown,
  context: WebExtractContext = {},
): Promise<WebExtractRouteOutcome> {
  const now = context.now ?? (() => new Date());
  const createUuid = context.uuid ?? (() => crypto.randomUUID());
  const createdAt = now().toISOString();
  const requestId = createUuid();

  try {
    const input = normalizeInput(body, createUuid);
    const callBackend =
      context.callBackend ??
      ((payload) => defaultCallBackend(payload, context.timeoutMs ?? 60000));
    const backend = await callBackend(input);
    const mapped = mapBackendPayload(backend.body, {
      createdAt,
      idempotencyKey: input.idempotencyKey ?? `extract-page-${requestId}`,
      message: "The page extraction request failed.",
      requestId,
    });

    return {
      body: mapped,
      statusCode: backend.statusCode,
    };
  } catch (error) {
    if (error instanceof ValidationError) {
      return buildFailure(400, {
        code: "invalid_request",
        createdAt,
        idempotencyKey: "none",
        message: error.message,
        requestId,
      });
    }

    if (error instanceof DOMException && error.name === "AbortError") {
      return buildFailure(504, {
        code: "FETCH_TIMEOUT",
        createdAt,
        idempotencyKey: "none",
        message: "The page took too long to extract.",
        requestId,
        retriable: true,
      });
    }

    return buildFailure(502, {
      code: "EXTRACT_FAILED",
      createdAt,
      idempotencyKey: "none",
      message: "The page extraction request failed.",
      requestId,
      retriable: true,
    });
  }
}
