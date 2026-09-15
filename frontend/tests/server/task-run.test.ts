import assert from "node:assert/strict";
import test from "node:test";

import {
  InterfazeProviderRequestError,
  InterfazeProviderTimeoutError,
} from "../../lib/server/interfaze";
import { createMemoryTaskResultCache } from "../../lib/server/task-cache";
import { handleTaskRunRequest } from "../../lib/server/tasks/run-task";

function createNow(...timestamps: string[]) {
  const queue = timestamps.map((timestamp) => new Date(timestamp));
  const fallback = queue[queue.length - 1] ?? new Date("2026-09-15T00:00:00.000Z");

  return () => queue.shift() ?? fallback;
}

function createUuid(...values: string[]) {
  let index = 0;

  return () => {
    const value = values[index] ?? values[values.length - 1] ?? "static-uuid";
    index += 1;
    return value;
  };
}

function createValidRequest(overrides?: Record<string, unknown>) {
  return {
    input: {
      idempotencyKey: "extract-id-demo-1234",
      imageUrl: "https://cdn.example.com/id-card.png",
      instruction: "Extract the details from this ID",
      ...(overrides ?? {}),
    },
    task: "extract_id" as const,
  };
}

function createProviderResult() {
  return {
    provider: "interfaze" as const,
    result: {
      dob: "1996-02-14",
      driverLicenceNumber: "D-123-456-789",
      firstName: "Eqan",
      lastName: "Ahmad",
    },
  };
}

test("valid extraction request returns a typed success payload", async () => {
  const outcome = await handleTaskRunRequest(createValidRequest(), {
    authenticated: true,
    cache: createMemoryTaskResultCache(),
    executeExtractId: async () => createProviderResult(),
    now: createNow("2026-09-15T10:00:00.000Z", "2026-09-15T10:00:00.125Z"),
    retryAttempts: 0,
    uuid: createUuid("request-1"),
  });

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(outcome.body.errors.length, 0);
  assert.equal(outcome.body.meta.cached, false);
  assert.equal(outcome.body.meta.idempotencyKey, "extract-id-demo-1234");
  assert.deepEqual(outcome.body.result, createProviderResult().result);
});

test("invalid payload returns a stable invalid_request response", async () => {
  const outcome = await handleTaskRunRequest(
    {
      input: {
        idempotencyKey: "short",
        imageUrl: "http://localhost:3000/id.png",
        instruction: "short",
      },
      task: "extract_id",
    },
    {
      authenticated: true,
      cache: createMemoryTaskResultCache(),
      now: createNow("2026-09-15T10:00:00.000Z", "2026-09-15T10:00:00.010Z"),
      uuid: createUuid("request-2"),
    },
  );

  assert.equal(outcome.statusCode, 400);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.body.errors[0]?.code, "invalid_request");
  assert.match(outcome.body.errors[0]?.message ?? "", /public https URL|between 10 and 500/);
});

test("provider timeout retries once and then succeeds", async () => {
  let attempts = 0;

  const outcome = await handleTaskRunRequest(createValidRequest(), {
    authenticated: true,
    cache: createMemoryTaskResultCache(),
    executeExtractId: async () => {
      attempts += 1;
      if (attempts === 1) {
        throw new InterfazeProviderTimeoutError();
      }

      return createProviderResult();
    },
    now: createNow(
      "2026-09-15T10:00:00.000Z",
      "2026-09-15T10:00:00.050Z",
      "2026-09-15T10:00:00.100Z",
    ),
    retryAttempts: 1,
    uuid: createUuid("request-3"),
  });

  assert.equal(attempts, 2);
  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(outcome.body.meta.cached, false);
});

test("provider hard failure returns a structured provider_failure response", async () => {
  const outcome = await handleTaskRunRequest(createValidRequest(), {
    authenticated: true,
    cache: createMemoryTaskResultCache(),
    executeExtractId: async () => {
      throw new InterfazeProviderRequestError("Interfaze authentication failed.", 502, false);
    },
    now: createNow("2026-09-15T10:00:00.000Z", "2026-09-15T10:00:00.020Z"),
    retryAttempts: 2,
    uuid: createUuid("request-4"),
  });

  assert.equal(outcome.statusCode, 502);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.body.errors[0]?.code, "provider_failure");
  assert.equal(outcome.body.errors[0]?.retriable, false);
});

test("duplicate request with the same idempotency key returns the cached result", async () => {
  const cache = createMemoryTaskResultCache();
  let attempts = 0;

  const context = {
    authenticated: true,
    cache,
    executeExtractId: async () => {
      attempts += 1;
      return createProviderResult();
    },
    now: createNow(
      "2026-09-15T10:00:00.000Z",
      "2026-09-15T10:00:00.050Z",
      "2026-09-15T10:00:00.100Z",
      "2026-09-15T10:00:00.150Z",
    ),
    retryAttempts: 0,
    uuid: createUuid("request-5", "request-6"),
  };

  const firstOutcome = await handleTaskRunRequest(createValidRequest(), context);
  const secondOutcome = await handleTaskRunRequest(createValidRequest(), context);

  assert.equal(attempts, 1);
  assert.equal(firstOutcome.statusCode, 200);
  assert.equal(secondOutcome.statusCode, 200);
  assert.equal(secondOutcome.body.meta.cached, true);
  assert.deepEqual(secondOutcome.body.result, firstOutcome.body.result);
});
