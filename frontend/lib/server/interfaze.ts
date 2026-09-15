import {
  APIConnectionError,
  APIConnectionTimeoutError,
  AuthenticationError,
  inputs,
  Interfaze,
  InterfazeError,
  InternalServerError,
  PermissionDeniedError,
  RateLimitError,
  responseFormat,
} from "interfaze";
import { z } from "zod";

import type { ExtractIdTaskInput, ExtractIdTaskResult } from "../../types/task";

import {
  getInterfazeServerEnv,
  hasInterfazeApiKey,
  type InterfazeServerEnv,
} from "./interfaze-env";

const interfazeIdSchema = z.object({
  dob: z.string().min(1),
  driver_licence_number: z.string().min(1),
  first_name: z.string().min(1),
  last_name: z.string().min(1),
});

export type InterfazeExecutionResult = {
  provider: "interfaze";
  result: ExtractIdTaskResult;
};

export class InterfazeNotConfiguredError extends Error {
  constructor(message = "Interfaze is not configured.") {
    super(message);
    this.name = "InterfazeNotConfiguredError";
  }
}

export class InterfazeProviderTimeoutError extends Error {
  constructor(message = "The extraction task timed out.") {
    super(message);
    this.name = "InterfazeProviderTimeoutError";
  }
}

export class InterfazeProviderRequestError extends Error {
  readonly retriable: boolean;
  readonly statusCode: number;

  constructor(message: string, statusCode = 502, retriable = false) {
    super(message);
    this.name = "InterfazeProviderRequestError";
    this.statusCode = statusCode;
    this.retriable = retriable;
  }
}

function toExtractIdResult(payload: z.infer<typeof interfazeIdSchema>): ExtractIdTaskResult {
  return {
    dob: payload.dob,
    driverLicenceNumber: payload.driver_licence_number,
    firstName: payload.first_name,
    lastName: payload.last_name,
  };
}

export async function extractIdWithInterfaze(
  input: Pick<ExtractIdTaskInput, "imageUrl" | "instruction">,
  env = getInterfazeServerEnv(),
): Promise<InterfazeExecutionResult> {
  if (!hasInterfazeApiKey(env)) {
    throw new InterfazeNotConfiguredError("Interfaze is not configured.");
  }

  const client = new Interfaze({
    apiKey: env.apiKey,
    baseURL: env.baseURL,
    maxRetries: 0,
    timeout: env.timeoutMs,
  });

  try {
    const response = await client.chat.completions.create({
      messages: [
        {
          content: [
            { text: input.instruction, type: "text" },
            inputs.image(input.imageUrl),
          ],
          role: "user",
        },
      ],
      model: env.model,
      response_format: responseFormat(
        z.toJSONSchema(interfazeIdSchema),
        "driver_license_extraction",
      ),
    });

    const content = response.choices[0]?.message?.content;
    if (typeof content !== "string" || !content.trim()) {
      throw new InterfazeProviderRequestError(
        "Interfaze returned an empty structured response.",
        502,
        true,
      );
    }

    let parsedContent: unknown;
    try {
      parsedContent = JSON.parse(content);
    } catch {
      throw new InterfazeProviderRequestError(
        "Interfaze returned an invalid structured response.",
        502,
        true,
      );
    }

    const parsedResult = interfazeIdSchema.parse(parsedContent);

    return {
      provider: "interfaze",
      result: toExtractIdResult(parsedResult),
    };
  } catch (error) {
    if (
      error instanceof InterfazeNotConfiguredError ||
      error instanceof InterfazeProviderTimeoutError ||
      error instanceof InterfazeProviderRequestError
    ) {
      throw error;
    }

    if (error instanceof APIConnectionTimeoutError) {
      throw new InterfazeProviderTimeoutError();
    }

    if (error instanceof APIConnectionError) {
      throw new InterfazeProviderRequestError(
        "The extraction task could not reach Interfaze.",
        503,
        true,
      );
    }

    if (error instanceof RateLimitError) {
      throw new InterfazeProviderRequestError(
        "Interfaze rate limit reached.",
        429,
        true,
      );
    }

    if (error instanceof AuthenticationError) {
      throw new InterfazeProviderRequestError(
        "Interfaze authentication failed.",
        502,
        false,
      );
    }

    if (error instanceof PermissionDeniedError) {
      throw new InterfazeProviderRequestError(
        "Interfaze rejected the extraction request.",
        502,
        false,
      );
    }

    if (error instanceof InternalServerError) {
      throw new InterfazeProviderRequestError(
        "Interfaze extraction failed.",
        502,
        true,
      );
    }

    if (error instanceof z.ZodError) {
      throw new InterfazeProviderRequestError(
        "Interfaze returned a response that did not match the schema.",
        502,
        true,
      );
    }

    if (error instanceof InterfazeError) {
      throw new InterfazeProviderRequestError(error.message, 502, false);
    }

    throw new InterfazeProviderRequestError(
      "Interfaze extraction failed.",
      502,
      true,
    );
  }
}
