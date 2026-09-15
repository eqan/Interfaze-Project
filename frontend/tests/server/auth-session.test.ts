import assert from "node:assert/strict";
import test from "node:test";

import { mintProjectJwt, verifyProjectJwt } from "../../lib/server/auth/jwt";
import {
  handleGoogleLoginRequest,
  handleLogoutRequest,
  handleSessionRequest,
} from "../../lib/server/auth/session";
import type { AuthUserRecord } from "../../lib/server/auth/users";
import type { GoogleIdTokenProfile } from "../../lib/server/auth/google";

const SECRET = "test-auth-secret-key";

function createNow(iso = "2026-09-15T10:00:00.000Z") {
  return () => new Date(iso);
}

function createGoogleProfile(
  overrides?: Partial<GoogleIdTokenProfile>,
): GoogleIdTokenProfile {
  return {
    email: "eqan@example.com",
    emailVerified: true,
    name: "Eqan Ahmad",
    picture: "https://cdn.example.com/eqan.png",
    sub: "google-sub-123",
    ...overrides,
  };
}

function createUserRecord(overrides?: Partial<AuthUserRecord>): AuthUserRecord {
  return {
    blackListed: false,
    email: "eqan@example.com",
    id: 1,
    name: "Eqan Ahmad",
    profileUrl: "https://cdn.example.com/eqan.png",
    type: "regular_user",
    ...overrides,
  };
}

test("valid Google credential returns a typed user and auth cookie", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-google-client.apps.googleusercontent.com";
  process.env.AUTH_ACCESS_TOKEN_EXPIRE_DAYS = "7";

  const profile = createGoogleProfile();
  const outcome = await handleGoogleLoginRequest(
    { credential: "valid.google.credential" },
    {
      mintJwt: mintProjectJwt,
      now: createNow(),
      secretKey: SECRET,
      secureCookies: false,
      upsertGoogleUser: async () => createUserRecord(),
      verifyGoogleIdToken: async () => profile,
    },
  );

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(outcome.body.user?.email, profile.email);
  assert.ok(outcome.cookie?.value);
  assert.equal(outcome.cookie?.name, "project_template_auth_token");

  const verified = await verifyProjectJwt({
    secretKey: SECRET,
    token: outcome.cookie!.value,
  });
  assert.equal(verified.sub, profile.sub);
  assert.equal(verified.email, profile.email);
});

test("missing credential returns a stable invalid request response", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;

  const outcome = await handleGoogleLoginRequest(
    { credential: "" },
    {
      secretKey: SECRET,
    },
  );

  assert.equal(outcome.statusCode, 400);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.cookie, null);
});

test("invalid Google credential returns a provider rejection response", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-google-client.apps.googleusercontent.com";

  const { GoogleTokenVerificationError } = await import(
    "../../lib/server/auth/google"
  );

  const outcome = await handleGoogleLoginRequest(
    { credential: "bad.token" },
    {
      secretKey: SECRET,
      verifyGoogleIdToken: async () => {
        throw new GoogleTokenVerificationError("Google authentication failed.");
      },
    },
  );

  assert.equal(outcome.statusCode, 400);
  assert.equal(outcome.body.status, false);
  assert.match(outcome.body.message ?? "", /Google authentication failed/);
});

test("blacklisted user is rejected on login", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;
  process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = "test-google-client.apps.googleusercontent.com";

  const outcome = await handleGoogleLoginRequest(
    { credential: "valid.google.credential" },
    {
      secretKey: SECRET,
      upsertGoogleUser: async () => createUserRecord({ blackListed: true }),
      verifyGoogleIdToken: async () => createGoogleProfile(),
    },
  );

  assert.equal(outcome.statusCode, 403);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.clearCookie, true);
});

test("session verify succeeds for a valid cookie token", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;

  const minted = await mintProjectJwt({
    email: "eqan@example.com",
    expiresInDays: 7,
    name: "Eqan Ahmad",
    now: createNow(),
    picture: "https://cdn.example.com/eqan.png",
    secretKey: SECRET,
    sub: "google-sub-123",
  });

  let touched = false;
  const outcome = await handleSessionRequest(minted.token, {
    getUserByEmail: async () => createUserRecord(),
    secretKey: SECRET,
    touchLastUsed: async () => {
      touched = true;
    },
    verifyJwt: verifyProjectJwt,
  });

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(outcome.body.user?.email, "eqan@example.com");
  assert.equal(touched, true);
});

test("session verify rejects an invalid token and clears the cookie", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;

  const outcome = await handleSessionRequest("not.a.valid.jwt", {
    secretKey: SECRET,
    secureCookies: false,
    verifyJwt: verifyProjectJwt,
  });

  assert.equal(outcome.statusCode, 401);
  assert.equal(outcome.body.status, false);
  assert.equal(outcome.clearCookie, true);
  assert.equal(outcome.cookie?.value, "");
});

test("session verify rejects an expired token", async () => {
  process.env.AUTH_SECRET_KEY = SECRET;

  const minted = await mintProjectJwt({
    email: "eqan@example.com",
    expiresInDays: 7,
    name: "Eqan Ahmad",
    now: () => new Date("2020-01-01T00:00:00.000Z"),
    picture: "",
    secretKey: SECRET,
    sub: "google-sub-123",
  });

  const outcome = await handleSessionRequest(minted.token, {
    secretKey: SECRET,
    verifyJwt: verifyProjectJwt,
  });

  assert.equal(outcome.statusCode, 401);
  assert.equal(outcome.clearCookie, true);
});

test("logout clears the auth cookie", () => {
  const outcome = handleLogoutRequest({ secureCookies: true });

  assert.equal(outcome.statusCode, 200);
  assert.equal(outcome.body.status, true);
  assert.equal(outcome.clearCookie, true);
  assert.equal(outcome.cookie?.value, "");
  assert.equal(outcome.cookie?.secure, true);
  assert.equal(outcome.cookie?.maxAgeSeconds, 0);
});
