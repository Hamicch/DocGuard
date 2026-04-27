"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ThemeSupa } from "@supabase/auth-ui-shared";

import { UniversalScreenLoader } from "@/components/ui/universal-screen-loader";
import { createClient } from "@/lib/supabase/client";

function AuthLoadingSkeleton() {
  return (
    <div className="space-y-4" aria-hidden>
      <div className="h-10 w-full animate-pulse rounded-md bg-gray-100" />
      <div className="h-10 w-full animate-pulse rounded-md bg-gray-100" />
      <div className="h-10 w-full animate-pulse rounded-md bg-gray-100" />
      <div className="h-9 w-full animate-pulse rounded-md bg-gray-200" />
      <p className="text-center text-xs text-gray-400">Loading sign-in…</p>
    </div>
  );
}

/** Client-only Supabase Auth UI (avoids themed vs unstyled flash on first paint). */
const Auth = dynamic(() => import("@supabase/auth-ui-react").then((mod) => mod.Auth), {
  ssr: false,
  loading: () => <AuthLoadingSkeleton />,
});

type LoginFormProps = {
  /** True when the URL already contains a PKCE `code` (set by the server page). */
  initialCompletingSignIn?: boolean;
};

export function LoginForm({ initialCompletingSignIn = false }: LoginFormProps) {
  const router = useRouter();
  const supabase = useMemo(() => createClient(), []);
  const [isCompletingSignIn, setIsCompletingSignIn] = useState(initialCompletingSignIn);
  const redirectTo = useMemo(
    () => (typeof window !== "undefined" ? `${window.location.origin}/runs` : undefined),
    [],
  );

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    if (hash.get("error")) {
      return;
    }
    if (hash.has("access_token") || hash.has("refresh_token")) {
      const id = requestAnimationFrame(() => {
        setIsCompletingSignIn(true);
      });
      return () => cancelAnimationFrame(id);
    }
    return undefined;
  }, []);

  useEffect(() => {
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") {
        setIsCompletingSignIn(true);
        router.replace("/runs");
        router.refresh();
      }
    });
    return () => subscription.unsubscribe();
  }, [router, supabase.auth]);

  return (
    <div className="relative w-full max-w-md overflow-hidden rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      {isCompletingSignIn ? (
        <UniversalScreenLoader
          variant="panel"
          message="Signing you in…"
          submessage="Continue in your browser if a Google or GitHub window opened. This can take a few seconds."
        />
      ) : null}
      <h1 className="mb-2 text-2xl font-semibold">Sign in to DocGuard</h1>
      <p className="mb-6 text-sm text-gray-500">
        Use email/password, Google, or GitHub to access your dashboard.
      </p>
      <div>
        <Auth
          supabaseClient={supabase}
          appearance={{ theme: ThemeSupa }}
          providers={["google", "github"]}
          redirectTo={redirectTo}
          view="sign_in"
        />
      </div>
    </div>
  );
}
