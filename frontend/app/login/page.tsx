import { redirect } from "next/navigation";

import { LoginForm } from "@/components/auth/login-form";
import { MissingSupabaseEnv } from "@/components/auth/missing-supabase-env";
import { hasSupabaseEnv } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";

export default async function LoginPage() {
  if (!hasSupabaseEnv) {
    return <MissingSupabaseEnv />;
  }

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session) {
    redirect("/runs");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
      <LoginForm />
    </main>
  );
}
