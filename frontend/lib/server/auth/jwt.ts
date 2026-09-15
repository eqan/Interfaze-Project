import { SignJWT, jwtVerify, type JWTPayload } from "jose";

import type { AuthenticatedUser } from "@/types/auth";

export type ProjectJwtClaims = AuthenticatedUser & JWTPayload;

export type MintProjectJwtInput = {
  email: string;
  expiresInDays: number;
  name: string;
  picture: string;
  secretKey: string;
  sub: string;
  now?: () => Date;
};

export type VerifyProjectJwtInput = {
  secretKey: string;
  token: string;
};

export class AuthJwtError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AuthJwtError";
  }
}

function getSecretKeyBytes(secretKey: string) {
  const trimmed = secretKey.trim();
  if (!trimmed) {
    throw new AuthJwtError("AUTH_SECRET_KEY is not configured.");
  }

  return new TextEncoder().encode(trimmed);
}

export async function mintProjectJwt({
  email,
  expiresInDays,
  name,
  now = () => new Date(),
  picture,
  secretKey,
  sub,
}: MintProjectJwtInput): Promise<{ exp: number; token: string }> {
  const issuedAt = now();
  const expSeconds = Math.floor(issuedAt.getTime() / 1000) + expiresInDays * 24 * 60 * 60;

  const token = await new SignJWT({
    email,
    name,
    picture,
  })
    .setProtectedHeader({ alg: "HS256" })
    .setSubject(sub)
    .setIssuedAt(Math.floor(issuedAt.getTime() / 1000))
    .setExpirationTime(expSeconds)
    .sign(getSecretKeyBytes(secretKey));

  return { exp: expSeconds, token };
}

export async function verifyProjectJwt({
  secretKey,
  token,
}: VerifyProjectJwtInput): Promise<AuthenticatedUser> {
  const trimmedToken = token.trim();
  if (!trimmedToken) {
    throw new AuthJwtError("Authentication token is missing.");
  }

  try {
    const { payload } = await jwtVerify(trimmedToken, getSecretKeyBytes(secretKey), {
      algorithms: ["HS256"],
    });

    const sub = typeof payload.sub === "string" ? payload.sub : "";
    const email = typeof payload.email === "string" ? payload.email : "";
    const name = typeof payload.name === "string" ? payload.name : "";
    const picture = typeof payload.picture === "string" ? payload.picture : "";
    const exp = typeof payload.exp === "number" ? payload.exp : undefined;

    if (!sub || !email) {
      throw new AuthJwtError("Authentication token is missing required claims.");
    }

    return {
      email,
      exp,
      name: name || email,
      picture,
      sub,
    };
  } catch (error) {
    if (error instanceof AuthJwtError) {
      throw error;
    }

    throw new AuthJwtError("Authentication token is invalid or expired.");
  }
}
