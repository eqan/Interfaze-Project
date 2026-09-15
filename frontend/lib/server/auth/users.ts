import { query } from "@/lib/server/db";

export const REGULAR_USER_TYPE = "regular_user";

export type AuthUserRecord = {
  blackListed: boolean;
  email: string;
  id: number;
  name: string;
  profileUrl: string | null;
  type: string;
};

type UserRow = {
  blackListed: boolean;
  email: string;
  id: number;
  name: string;
  profile_url: string | null;
  type: string;
};

function mapUserRow(row: UserRow): AuthUserRecord {
  return {
    blackListed: Boolean(row.blackListed),
    email: row.email,
    id: row.id,
    name: row.name,
    profileUrl: row.profile_url,
    type: row.type,
  };
}

export async function getUserByEmail(email: string): Promise<AuthUserRecord | null> {
  const result = await query<UserRow>(
    `SELECT id, name, email, type, "blackListed", profile_url
     FROM users
     WHERE email = $1
     LIMIT 1`,
    [email],
  );

  const row = result.rows[0];
  return row ? mapUserRow(row) : null;
}

export async function upsertGoogleUser(input: {
  email: string;
  name: string;
  now?: () => Date;
  profileUrl: string;
}): Promise<AuthUserRecord> {
  const now = input.now?.() ?? new Date();
  const existing = await getUserByEmail(input.email);

  if (!existing) {
    const inserted = await query<UserRow>(
      `INSERT INTO users (name, email, type, "blackListed", profile_url, last_time_service_used, notes)
       VALUES ($1, $2, $3, false, $4, $5, NULL)
       RETURNING id, name, email, type, "blackListed", profile_url`,
      [input.name, input.email, REGULAR_USER_TYPE, input.profileUrl || null, now],
    );

    const row = inserted.rows[0];
    if (!row) {
      throw new Error("Failed to create user record.");
    }

    return mapUserRow(row);
  }

  const updated = await query<UserRow>(
    `UPDATE users
     SET name = $2,
         profile_url = $3,
         last_time_service_used = $4
     WHERE email = $1
     RETURNING id, name, email, type, "blackListed", profile_url`,
    [input.email, input.name, input.profileUrl || existing.profileUrl, now],
  );

  const row = updated.rows[0];
  if (!row) {
    throw new Error("Failed to update user record.");
  }

  return mapUserRow(row);
}

export async function touchLastUsed(email: string, now: Date = new Date()) {
  await query(
    `UPDATE users
     SET last_time_service_used = $2
     WHERE email = $1`,
    [email, now],
  );
}
