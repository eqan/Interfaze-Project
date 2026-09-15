import { Pool, type PoolClient, type QueryResult, type QueryResultRow } from "pg";

import { getAuthServerEnv, hasDatabaseConfig } from "@/lib/server/auth-env";

declare global {
  // eslint-disable-next-line no-var
  var __projectTemplatePgPool: Pool | undefined;
}

function buildDatabaseUrl() {
  const env = getAuthServerEnv();

  if (!hasDatabaseConfig(env)) {
    throw new Error(
      "Database configuration is incomplete. Set DB_USER, DB_HOST, DB_PORT, DB_PASSWORD, and DB_NAME.",
    );
  }

  const { database } = env;
  const encodedUser = encodeURIComponent(database.user);
  const encodedPassword = encodeURIComponent(database.password);
  const encodedName = encodeURIComponent(database.name);

  return `postgresql://${encodedUser}:${encodedPassword}@${database.host}:${database.port}/${encodedName}`;
}

export function getPool() {
  if (!globalThis.__projectTemplatePgPool) {
    globalThis.__projectTemplatePgPool = new Pool({
      connectionString: buildDatabaseUrl(),
      max: 10,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 10_000,
    });
  }

  return globalThis.__projectTemplatePgPool;
}

export async function query<T extends QueryResultRow = QueryResultRow>(
  text: string,
  params: unknown[] = [],
): Promise<QueryResult<T>> {
  return getPool().query<T>(text, params);
}

export async function withClient<T>(
  callback: (client: PoolClient) => Promise<T>,
): Promise<T> {
  const client = await getPool().connect();

  try {
    return await callback(client);
  } finally {
    client.release();
  }
}
