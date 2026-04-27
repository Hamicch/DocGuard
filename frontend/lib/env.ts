export const env = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  backendApiBaseUrl:
    process.env.BACKEND_API_URL ?? process.env.NEXT_PUBLIC_BACKEND_API_URL ?? "http://localhost:8000",
};

export const hasSupabaseEnv = Boolean(env.supabaseUrl) && Boolean(env.supabaseAnonKey);
