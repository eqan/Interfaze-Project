export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export type AuthenticatedUser = {
  sub: string;
  email: string;
  name: string;
  picture: string;
  exp?: number;
};

export type AuthSessionResponse = {
  status: boolean;
  message?: string;
  user?: AuthenticatedUser | null;
};

export type GoogleLoginResponse = AuthSessionResponse;

export type VerifySessionResponse = AuthSessionResponse;
