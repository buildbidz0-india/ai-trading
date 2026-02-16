"use server";
import { neon } from "@neondatabase/serverless";

export async function getData() {
    if (!process.env.DATABASE_URL) {
        throw new Error("DATABASE_URL is not defined");
    }
    const sql = neon(process.env.DATABASE_URL);
    // Note: The user provided "..." which I'll keep as a placeholder or replace with a generic query if needed.
    // For now, I'll use a simple query to ensure syntax is correct, but keep it minimal.
    const data = await sql`SELECT NOW()`;
    return data;
}
