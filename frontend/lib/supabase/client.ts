"use client";

import { createBrowserClient } from "@supabase/ssr";

import { env, hasSupabaseEnv } from "@/lib/env";

export function createClient() {
  if (!hasSupabaseEnv) {
    throw new Error(
      "Missing Supabase env. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.",
    );
  }

  return createBrowserClient(env.supabaseUrl, env.supabaseAnonKey);
}
