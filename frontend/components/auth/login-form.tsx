"use client";

import { useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { Auth } from "@supabase/auth-ui-react";
import { ThemeSupa } from "@supabase/auth-ui-shared";

import { createClient } from "@/lib/supabase/client";

export function LoginForm() {
  const router = useRouter();
  const supabase = useMemo(() => createClient(), []);
  const redirectTo = useMemo(
    () => (typeof window !== "undefined" ? `${window.location.origin}/runs` : undefined),
    [],
  );

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") {
        router.replace("/runs");
        router.refresh();
      }
    });
    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  return (
    <div className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h1 className="mb-2 text-2xl font-semibold">Sign in to DocGuard</h1>
      <p className="mb-6 text-sm text-gray-500">
        Use email/password, Google, or GitHub to access your dashboard.
      </p>
      <Auth
        supabaseClient={supabase}
        appearance={{ theme: ThemeSupa }}
        providers={["google", "github"]}
        redirectTo={redirectTo}
        view="sign_in"
      />
    </div>
  );
}
