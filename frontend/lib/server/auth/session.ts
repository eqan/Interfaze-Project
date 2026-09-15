import type { AuthenticatedUser } from "@/types/auth";

import { getAuthServerEnv, hasAuthSecretKey } from "@/lib/server/auth-env";
import {
  GoogleTokenVerificationError,
  verifyGoogleIdToken,
  type GoogleIdTokenProfile,
} from "@/lib/server/auth/google";
import {
  AuthJwtError,
  mintProjectJwt,
  verifyProjectJwt,
} from "@/lib/server/auth/jwt";
import {
  getUserByEmail,
  touchLastUsed,
  upsertGoogleUser,
  type AuthUserRecord,
} from "@/lib/server/auth/users";
import {
  buildAuthSessionCookie,
  buildClearedAuthSessionCookie,
  getCookieMaxAgeSeconds,
  type AuthCookieDescriptor,
} from "@/lib/server/auth/cookies";

export type AuthSessionCookie = {
  maxAgeSeconds: number;
  name: string;
  secure: boolean;
  value: string;
};

export type AuthSessionOutcome = {
  body: {
    message?: string;
    status: boolean;
    user?: AuthenticatedUser | null;
  };
  clearCookie: boolean;
  cookie: AuthSessionCookie | null;
  statusCode: number;
};

export type AuthSessionContext = {
  getUserByEmail?: (email: string) => Promise<AuthUserRecord | null>;
  mintJwt?: typeof mintProjectJwt;
  now?: () => Date;
  secretKey?: string;
  secureCookies?: boolean;
  touchLastUsed?: (email: string, now?: Date) => Promise<void>;
  upsertGoogleUser?: typeof upsertGoogleUser;
  verifyGoogleIdToken?: typeof verifyGoogleIdToken;
  verifyJwt?: typeof verifyProjectJwt;
};

function toSessionCookie(cookie: AuthCookieDescriptor): AuthSessionCookie {
  return {
    maxAgeSeconds: cookie.options.maxAge,
    name: cookie.name,
    secure: cookie.options.secure,
    value: cookie.value,
  };
}

function mapAuthErrorMessage(error: unknown, fallback: string) {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

function toAuthenticatedUser(
  profile: Pick<GoogleIdTokenProfile, "email" | "name" | "picture" | "sub">,
  exp: number,
): AuthenticatedUser {
  return {
    email: profile.email,
    exp,
    name: profile.name,
    picture: profile.picture,
    sub: profile.sub,
  };
}

export async function handleGoogleLoginRequest(
  body: unknown,
  context: AuthSessionContext = {},
): Promise<AuthSessionOutcome> {
  const env = getAuthServerEnv();
  const secretKey = context.secretKey ?? env.secretKey;
  const secureCookies = context.secureCookies ?? false;
  const now = context.now ?? (() => new Date());
  const verifyGoogle = context.verifyGoogleIdToken ?? verifyGoogleIdToken;
  const upsertUser = context.upsertGoogleUser ?? upsertGoogleUser;
  const mintJwt = context.mintJwt ?? mintProjectJwt;

  if (!hasAuthSecretKey({ ...env, secretKey })) {
    return {
      body: {
        message: "Authentication is not configured.",
        status: false,
        user: null,
      },
      clearCookie: false,
      cookie: null,
      statusCode: 500,
    };
  }

  if (!body || typeof body !== "object") {
    return {
      body: {
        message: "Google credential is required.",
        status: false,
        user: null,
      },
      clearCookie: false,
      cookie: null,
      statusCode: 400,
    };
  }

  const credential = (body as Record<string, unknown>).credential;
  if (typeof credential !== "string" || !credential.trim()) {
    return {
      body: {
        message: "Google credential is required.",
        status: false,
        user: null,
      },
      clearCookie: false,
      cookie: null,
      statusCode: 400,
    };
  }

  try {
    const profile = await verifyGoogle({
      audience: env.googleClientId,
      credential,
      tokenInfoUrl: env.googleOAuthUrl,
    });

    const userRecord = await upsertUser({
      email: profile.email,
      name: profile.name,
      now,
      profileUrl: profile.picture,
    });

    if (userRecord.blackListed) {
      return {
        body: {
          message: "This account is not allowed to sign in.",
          status: false,
          user: null,
        },
        clearCookie: true,
        cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
        statusCode: 403,
      };
    }

    const minted = await mintJwt({
      email: profile.email,
      expiresInDays: env.accessTokenExpireDays,
      name: profile.name,
      now,
      picture: profile.picture,
      secretKey,
      sub: profile.sub,
    });

    const user = toAuthenticatedUser(profile, minted.exp);
    const cookie = buildAuthSessionCookie({
      maxAgeSeconds: getCookieMaxAgeSeconds(minted.exp, now().getTime()),
      secure: secureCookies,
      value: minted.token,
    });

    return {
      body: {
        message: "Google Authentication Successful!",
        status: true,
        user,
      },
      clearCookie: false,
      cookie: toSessionCookie(cookie),
      statusCode: 200,
    };
  } catch (error) {
    if (error instanceof GoogleTokenVerificationError) {
      return {
        body: {
          message: mapAuthErrorMessage(error, "Google authentication failed."),
          status: false,
          user: null,
        },
        clearCookie: false,
        cookie: null,
        statusCode: 400,
      };
    }

    return {
      body: {
        message: mapAuthErrorMessage(error, "Authentication failed."),
        status: false,
        user: null,
      },
      clearCookie: false,
      cookie: null,
      statusCode: 500,
    };
  }
}

export async function handleSessionRequest(
  token: string | undefined,
  context: AuthSessionContext = {},
): Promise<AuthSessionOutcome> {
  const env = getAuthServerEnv();
  const secretKey = context.secretKey ?? env.secretKey;
  const secureCookies = context.secureCookies ?? false;
  const now = context.now ?? (() => new Date());
  const verifyJwt = context.verifyJwt ?? verifyProjectJwt;
  const findUser = context.getUserByEmail ?? getUserByEmail;
  const touchUser = context.touchLastUsed ?? touchLastUsed;

  if (!token?.trim()) {
    return {
      body: {
        message: "Unauthorized",
        status: false,
        user: null,
      },
      clearCookie: false,
      cookie: null,
      statusCode: 401,
    };
  }

  if (!hasAuthSecretKey({ ...env, secretKey })) {
    return {
      body: {
        message: "Authentication is not configured.",
        status: false,
        user: null,
      },
      clearCookie: true,
      cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
      statusCode: 500,
    };
  }

  try {
    const user = await verifyJwt({
      secretKey,
      token,
    });

    const record = await findUser(user.email);
    if (!record) {
      return {
        body: {
          message: "Unauthorized",
          status: false,
          user: null,
        },
        clearCookie: true,
        cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
        statusCode: 401,
      };
    }

    if (record.blackListed) {
      return {
        body: {
          message: "This account is not allowed to sign in.",
          status: false,
          user: null,
        },
        clearCookie: true,
        cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
        statusCode: 403,
      };
    }

    await touchUser(user.email, now());

    return {
      body: {
        status: true,
        user,
      },
      clearCookie: false,
      cookie: null,
      statusCode: 200,
    };
  } catch (error) {
    if (error instanceof AuthJwtError) {
      return {
        body: {
          message: mapAuthErrorMessage(error, "Unauthorized"),
          status: false,
          user: null,
        },
        clearCookie: true,
        cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
        statusCode: 401,
      };
    }

    return {
      body: {
        message: mapAuthErrorMessage(error, "Authentication failed."),
        status: false,
        user: null,
      },
      clearCookie: true,
      cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
      statusCode: 500,
    };
  }
}

export function handleLogoutRequest(
  context: Pick<AuthSessionContext, "secureCookies"> = {},
): AuthSessionOutcome {
  const secureCookies = context.secureCookies ?? false;

  return {
    body: {
      status: true,
    },
    clearCookie: true,
    cookie: toSessionCookie(buildClearedAuthSessionCookie(secureCookies)),
    statusCode: 200,
  };
}
