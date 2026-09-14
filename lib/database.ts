import { Pool, type QueryResultRow } from "pg";

const globalForDatabase = globalThis as unknown as { macroPool?: Pool };

function getPool() {
  if (globalForDatabase.macroPool) return globalForDatabase.macroPool;
  const databaseUrl = process.env.DATABASE_URL;
  if (!databaseUrl) throw new Error("DATABASE_URL is required to read macro data. Copy .env.local.example to .env.local.");
  const pool = new Pool({ connectionString: databaseUrl });
  if (process.env.NODE_ENV !== "production") globalForDatabase.macroPool = pool;
  return pool;
}

export async function query<T extends QueryResultRow>(text: string, values: unknown[] = []) {
  return getPool().query<T>(text, values);
}
