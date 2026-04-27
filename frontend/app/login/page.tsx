import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import { MissingSupabaseEnv } from "@/components/auth/missing-supabase-env";
import { hasSupabaseEnv } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";

type LoginSearchParams = Promise<{
  code?: string | string[];
  error?: string | string[];
}>;

export default async function LoginPage({ searchParams }: { searchParams: LoginSearchParams }) {
  if (!hasSupabaseEnv) {
    return <MissingSupabaseEnv />;
  }

  const sp = await searchParams;
  const code = sp.code;
  const hasPkceCode = typeof code === "string" ? code.length > 0 : Array.isArray(code) && code.length > 0;
  const authError = sp.error;
  const hasAuthError =
    typeof authError === "string"
      ? authError.length > 0
      : Array.isArray(authError) && authError.length > 0;
  const initialCompletingSignIn = hasPkceCode && !hasAuthError;

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session) {
    redirect("/runs");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <LoginForm initialCompletingSignIn={initialCompletingSignIn} />
    </main>
  );
}
