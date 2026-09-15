export type InterfazeServerEnv = {
  apiKey: string;
  model: string;
  baseURL?: string;
  timeoutMs: number;
  retryAttempts: number;
  resultCacheTtlSeconds: number;
};

function parsePositiveInteger(
  rawValue: string | undefined,
  fallback: number,
  variableName: string,
) {
  if (!rawValue?.trim()) {
    return fallback;
  }

  const parsedValue = Number.parseInt(rawValue, 10);
  if (!Number.isFinite(parsedValue) || parsedValue <= 0) {
    throw new Error(`${variableName} must be a positive integer.`);
  }

  return parsedValue;
}

export function getInterfazeServerEnv(): InterfazeServerEnv {
  const apiKey = process.env.INTERFAZE_API_KEY?.trim() ?? "";
  const model = process.env.INTERFAZE_MODEL_NAME?.trim() || "interfaze-beta";
  const baseURL = process.env.INTERFAZE_BASE_URL?.trim() || undefined;

  return {
    apiKey,
    model,
    baseURL,
    timeoutMs: parsePositiveInteger(
      process.env.INTERFAZE_TIMEOUT_MS,
      20_000,
      "INTERFAZE_TIMEOUT_MS",
    ),
    retryAttempts: parsePositiveInteger(
      process.env.INTERFAZE_RETRY_ATTEMPTS,
      2,
      "INTERFAZE_RETRY_ATTEMPTS",
    ),
    resultCacheTtlSeconds: parsePositiveInteger(
      process.env.INTERFAZE_RESULT_CACHE_TTL_SECONDS,
      60 * 60,
      "INTERFAZE_RESULT_CACHE_TTL_SECONDS",
    ),
  };
}

export function hasInterfazeApiKey(env = getInterfazeServerEnv()) {
  return env.apiKey.length > 0 && env.apiKey !== "your-interfaze-api-key";
}
