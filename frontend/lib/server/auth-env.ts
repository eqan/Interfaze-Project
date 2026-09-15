export type AuthServerEnv = {
  accessTokenExpireDays: number;
  algorithm: "HS256";
  database: {
    host: string;
    name: string;
    password: string;
    port: number;
    user: string;
  };
  googleClientId: string;
  googleOAuthUrl: string;
  secretKey: string;
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

export function getAuthServerEnv(): AuthServerEnv {
  const secretKey =
    process.env.AUTH_SECRET_KEY?.trim() ||
    process.env.SECRET_KEY?.trim() ||
    "";
  const algorithm = (
    process.env.AUTH_ALGORITHM?.trim() ||
    process.env.ALGORITHM?.trim() ||
    "HS256"
  ) as "HS256";
  const googleClientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID?.trim() ?? "";
  const googleOAuthUrl =
    process.env.GOOGLE_OAUTH_URL?.trim() ||
    "https://oauth2.googleapis.com/tokeninfo";

  if (algorithm !== "HS256") {
    throw new Error("AUTH_ALGORITHM/ALGORITHM must be HS256.");
  }

  return {
    accessTokenExpireDays: parsePositiveInteger(
      process.env.AUTH_ACCESS_TOKEN_EXPIRE_DAYS ||
        process.env.ACCESS_TOKEN_EXPIRE_DAYS,
      7,
      "AUTH_ACCESS_TOKEN_EXPIRE_DAYS",
    ),
    algorithm,
    database: {
      host: process.env.DB_HOST?.trim() ?? "",
      name: process.env.DB_NAME?.trim() ?? "",
      password: process.env.DB_PASSWORD?.trim() ?? "",
      port: parsePositiveInteger(process.env.DB_PORT, 5432, "DB_PORT"),
      user: process.env.DB_USER?.trim() ?? "",
    },
    googleClientId,
    googleOAuthUrl,
    secretKey,
  };
}

export function hasAuthSecretKey(env = getAuthServerEnv()) {
  return env.secretKey.length > 0;
}

export function hasDatabaseConfig(env = getAuthServerEnv()) {
  const { database } = env;
  return Boolean(
    database.host && database.name && database.user && database.password !== undefined,
  );
}
