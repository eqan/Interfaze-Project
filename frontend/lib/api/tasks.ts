import type {
  ExtractIdTaskInput,
  TaskRunRequest,
  TaskRunResponse,
} from "@/types/task";

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

export class TaskRequestError extends Error {
  response: TaskRunResponse | null;

  constructor(message: string, response: TaskRunResponse | null = null) {
    super(message);
    this.name = "TaskRequestError";
    this.response = response;
  }
}

export async function runTask(request: TaskRunRequest): Promise<TaskRunResponse> {
  const response = await fetch("/api/tasks/run", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    cache: "no-store",
    credentials: "same-origin",
  });

  const payload = (await response.json()) as TaskRunResponse;
  if (!response.ok) {
    throw new TaskRequestError(
      errorMessageFromPayload(payload, "The task request failed."),
      payload ?? null,
    );
  }

  return payload;
}

export function runExtractIdTask(input: ExtractIdTaskInput) {
  return runTask({
    task: "extract_id",
    input,
  });
}
