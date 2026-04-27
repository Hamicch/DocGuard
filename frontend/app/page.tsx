import { redirect } from "next/navigation";

import { MissingSupabaseEnv } from "@/components/auth/missing-supabase-env";
import { hasSupabaseEnv } from "@/lib/env";
import { createClient } from "@/lib/supabase/server";

export default async function Home() {
  if (!hasSupabaseEnv) {
    return <MissingSupabaseEnv />;
  }

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  redirect(session ? "/runs" : "/login");
}
