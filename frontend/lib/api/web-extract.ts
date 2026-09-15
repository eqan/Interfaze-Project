import type { WebExtractInput, WebExtractResponse } from "@/types/web-extract";

function errorMessageFromPayload(payload: unknown, fallback: string) {
  if (!payload || typeof payload !== "object") {
    return fallback;
  }

  const record = payload as Record<string, unknown>;
  const message = record.message;
  if (typeof message === "string" && message.trim()) {
    return message;
  }

  const errors = record.errors;
  if (Array.isArray(errors)) {
    const firstError = errors[0];
    if (
      firstError &&
      typeof firstError === "object" &&
      typeof (firstError as Record<string, unknown>).message === "string"
    ) {
      return (firstError as Record<string, string>).message;
    }
  }

  return fallback;
}

export class WebExtractRequestError extends Error {
  response: WebExtractResponse | null;

  constructor(message: string, response: WebExtractResponse | null = null) {
    super(message);
    this.name = "WebExtractRequestError";
    this.response = response;
  }
}

export async function runWebExtract(
  input: WebExtractInput,
): Promise<WebExtractResponse> {
  const response = await fetch("/api/web-extract/run", {
    body: JSON.stringify(input),
    cache: "no-store",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
    },
    method: "POST",
  });

  const payload = (await response.json()) as WebExtractResponse;
  if (!response.ok) {
    throw new WebExtractRequestError(
      errorMessageFromPayload(payload, "The page extraction request failed."),
      payload ?? null,
    );
  }

  return payload;
}
