import assert from "node:assert/strict";
import test from "node:test";

import { handleWebExtractRequest } from "../../lib/server/web-extract/run";

function createNow(iso = "2026-09-15T10:00:00.000Z") {
  return () => new Date(iso);
}

function createUuid(value = "request-1") {
  return () => value;
}

function createValidRequest(overrides?: Record<string, unknown>) {
  return {
    idempotencyKey: "extract-page-demo-1234",
    prompt: "Extract the page title and price",
    url: "https://example.com",
    ...overrides,
  };
}

test("valid page extract request maps a typed success payload", async () => {
  const outcome = await handleWebExtractRequest(createValidRequest(), {
    callBackend: async () => ({
      statusCode: 200,
      body: {
        errors: [],
        message: "Page extracted",
        meta: {
          cached: false,
          checkAttempts: 2,
          confidence: 0.95,
          durationMs: 210,
          idempotencyKey: "extract-page-demo-1234",
          provider: "local-html+deepseek",
          requestId: "be-1",
        },
        result: {
          commands: [{ attr: "text", many: false, name: "title", selector: "h1" }],
          confidence: 0.95,
          data: { title: "Example Domain" },
          url: "https://example.com",
        },
        status: true,
        task: "extract_page",
      },
    }),
    now: createNow(),
    uuid: createUuid(),
  });

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(outcome.body.result?.data.title, "Example Domain");
  assert.equal(outcome.body.result?.confidence, 0.95);
  assert.equal(outcome.body.meta.cached, false);
  assert.equal(outcome.body.meta.truncated, false);
  assert.equal(outcome.body.meta.confidence, 0.95);
  assert.equal(outcome.body.meta.checkAttempts, 2);
});

test("invalid url returns a stable invalid_request response", async () => {
  const outcome = await handleWebExtractRequest(
    {
      prompt: "Extract the page title",
      url: "http://localhost/product",
    },
    {
      now: createNow(),
      uuid: createUuid(),
    },
  );

  assert.equal(outcome.statusCode, 400);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.body.errors[0]?.code, "invalid_request");
});

test("short prompts are allowed so the backend refiner can broaden them", async () => {
  let receivedPrompt = "";
  const outcome = await handleWebExtractRequest(
    {
      prompt: "name",
      url: "https://example.com",
    },
    {
      callBackend: async (input) => {
        receivedPrompt = input.prompt;
        return {
          statusCode: 200,
          body: {
            errors: [],
            message: "Page extracted",
            meta: {
              cached: false,
              durationMs: 10,
              idempotencyKey: input.idempotencyKey,
              provider: "local-html+deepseek",
              requestId: "be-short",
            },
            result: {
              commands: [],
              confidence: 1,
              data: { name: "Example Domain" },
              url: "https://example.com",
            },
            status: true,
            task: "extract_page",
          },
        };
      },
      now: createNow(),
      uuid: createUuid("request-short"),
    },
  );

  assert.equal(outcome.statusCode, 200);
  assert.equal(receivedPrompt, "name");
  assert.equal(outcome.body.result?.data.name, "Example Domain");
});

test("unauthenticated requests still call the extract API", async () => {
  let called = false;
  const outcome = await handleWebExtractRequest(createValidRequest(), {
    callBackend: async () => {
      called = true;
      return {
        body: {
          errors: [],
          message: "Page extracted",
          meta: {
            cached: false,
            durationMs: 10,
            idempotencyKey: "extract-page-demo-1234",
            provider: "local-html+deepseek",
            requestId: "be-open",
          },
          result: {
            commands: [],
            confidence: 1,
            data: { title: "Example Domain" },
            url: "https://example.com",
          },
          status: true,
          task: "extract_page",
        },
        statusCode: 200,
      };
    },
    now: createNow(),
    uuid: createUuid(),
  });

  assert.equal(outcome.statusCode, 200);
  assert.equal(called, true);
});

test("amazon product extract maps title and price into the envelope", async () => {
  const amazonUrl =
    "https://www.amazon.com/Charger-Dot-Matrix-Display-Charging-MacBook/dp/B0F9PKSJ17?sr=8-4&th=1";
  const outcome = await handleWebExtractRequest(
    {
      idempotencyKey: "amazon-sharge-140w-1",
      prompt: "Extract the product name and price",
      url: amazonUrl,
    },
    {
      callBackend: async () => ({
        statusCode: 200,
        body: {
          errors: [],
          message: "Page extracted",
          meta: {
            cached: false,
            durationMs: 410,
            idempotencyKey: "amazon-sharge-140w-1",
            provider: "local-html+deepseek",
            requestId: "be-amazon-1",
          },
          result: {
            commands: [
              { attr: "text", many: false, name: "name", selector: "#productTitle" },
              {
                attr: "text",
                many: false,
                name: "price",
                selector: ".a-price .a-offscreen",
              },
            ],
            confidence: 1,
            data: {
              name: "SHARGE 140W 3-Port GaN Laptop Charger, USB C MacBook Charger with Display",
              price: "$94.00",
            },
            url: amazonUrl,
          },
          status: true,
          task: "extract_page",
        },
      }),
      now: createNow(),
      uuid: createUuid("request-amazon"),
    },
  );

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(
    outcome.body.result?.data.name,
    "SHARGE 140W 3-Port GaN Laptop Charger, USB C MacBook Charger with Display",
  );
  assert.equal(outcome.body.result?.data.price, "$94.00");
});

test("amazon catalog extract maps title and price into the envelope", async () => {
  const amazonUrl =
    "https://www.amazon.com/Charger-Dot-Matrix-Display-Charging-MacBook/dp/B0F9PKSJ17?sr=8-4&th=1";
  const outcome = await handleWebExtractRequest(
    {
      idempotencyKey: "amazon-sharge-140w-catalog-1",
      prompt: "Extract the product name and price",
      url: amazonUrl,
    },
    {
      callBackend: async () => ({
        statusCode: 200,
        body: {
          errors: [],
          message: "Page extracted",
          meta: {
            cached: false,
            durationMs: 90,
            idempotencyKey: "amazon-sharge-140w-catalog-1",
            provider: "amazon-creators",
            requestId: "be-amazon-catalog-1",
          },
          result: {
            commands: [
              {
                attr: "text",
                many: false,
                name: "name",
                selector: "amazon-creators:itemInfo.title",
              },
              {
                attr: "text",
                many: false,
                name: "price",
                selector: "amazon-creators:offersV2.listings.price",
              },
            ],
            confidence: 1,
            data: {
              name: "SHARGE 140W 3-Port GaN Laptop Charger, USB C MacBook Charger with Display",
              price: "$94.00",
            },
            url: amazonUrl,
          },
          status: true,
          task: "extract_page",
        },
      }),
      now: createNow(),
      uuid: createUuid("request-amazon-catalog"),
    },
  );

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.meta.provider, "amazon-creators");
  assert.equal(
    outcome.body.result?.data.name,
    "SHARGE 140W 3-Port GaN Laptop Charger, USB C MacBook Charger with Display",
  );
  assert.equal(outcome.body.result?.data.price, "$94.00");
});

test("backend access wall failure is mapped into the envelope", async () => {
  const outcome = await handleWebExtractRequest(createValidRequest(), {
    callBackend: async () => ({
      statusCode: 422,
      body: {
        errors: [
          {
            code: "FETCH_BLOCKED",
            message: "The downloaded page looks like an access wall, not the requested content.",
            retriable: true,
          },
        ],
        message: "The page did not contain extractable product data.",
        meta: {
          cached: false,
          durationMs: 80,
          idempotencyKey: "extract-page-demo-1234",
          provider: "local-html",
          requestId: "be-2",
        },
        result: null,
        status: false,
        task: "extract_page",
      },
    }),
    now: createNow(),
    uuid: createUuid(),
  });

  assert.equal(outcome.statusCode, 422);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.body.errors[0]?.code, "FETCH_BLOCKED");
});
