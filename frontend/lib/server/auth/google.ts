export type GoogleIdTokenProfile = {
  email: string;
  emailVerified: boolean;
  name: string;
  picture: string;
  sub: string;
};

export class GoogleTokenVerificationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GoogleTokenVerificationError";
  }
}

type VerifyGoogleIdTokenOptions = {
  audience: string;
  credential: string;
  fetchImpl?: typeof fetch;
  tokenInfoUrl?: string;
};

export async function verifyGoogleIdToken({
  audience,
  credential,
  fetchImpl = fetch,
  tokenInfoUrl = "https://oauth2.googleapis.com/tokeninfo",
}: VerifyGoogleIdTokenOptions): Promise<GoogleIdTokenProfile> {
  const trimmedCredential = credential.trim();
  if (!trimmedCredential) {
    throw new GoogleTokenVerificationError("Google credential is required.");
  }

  if (!audience.trim()) {
    throw new GoogleTokenVerificationError("Google client audience is not configured.");
  }

  const url = new URL(tokenInfoUrl);
  url.searchParams.set("id_token", trimmedCredential);

  let response: Response;
  try {
    response = await fetchImpl(url.toString(), {
      cache: "no-store",
      method: "GET",
    });
  } catch {
    throw new GoogleTokenVerificationError("Unable to reach Google token verification.");
  }

  if (!response.ok) {
    throw new GoogleTokenVerificationError("Google authentication failed.");
  }

  const payload = (await response.json().catch(() => null)) as Record<
    string,
    unknown
  > | null;

  if (!payload || typeof payload !== "object") {
    throw new GoogleTokenVerificationError("Google token payload was empty.");
  }

  const sub = typeof payload.sub === "string" ? payload.sub.trim() : "";
  const email = typeof payload.email === "string" ? payload.email.trim() : "";
  const name = typeof payload.name === "string" ? payload.name.trim() : "";
  const picture =
    typeof payload.picture === "string" ? payload.picture.trim() : "";
  const aud = typeof payload.aud === "string" ? payload.aud.trim() : "";
  const emailVerifiedRaw = payload.email_verified;
  const emailVerified =
    emailVerifiedRaw === true ||
    emailVerifiedRaw === "true" ||
    emailVerifiedRaw === "True";

  if (!sub || !email) {
    throw new GoogleTokenVerificationError("Google token is missing required claims.");
  }

  if (aud !== audience) {
    throw new GoogleTokenVerificationError("Google token audience mismatch.");
  }

  if (!emailVerified) {
    throw new GoogleTokenVerificationError("Google email is not verified.");
  }

  return {
    email,
    emailVerified,
    name: name || email,
    picture,
    sub,
  };
}
