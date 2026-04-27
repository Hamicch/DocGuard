"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ThemeSupa } from "@supabase/auth-ui-shared";

import { Spinner } from "@/components/ui/spinner";
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
  const authMountRef = useRef<HTMLDivElement>(null);
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

  useEffect(() => {
    const root = authMountRef.current;
    if (!root) {
      return;
    }
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as HTMLElement | null;
      const button = target?.closest("button");
      if (!button || !root.contains(button)) {
        return;
      }
      if (button.type === "submit" || button.type === "button") {
        setIsCompletingSignIn(true);
      }
    };
    root.addEventListener("pointerdown", onPointerDown, true);
    return () => root.removeEventListener("pointerdown", onPointerDown, true);
  }, []);

  return (
    <div className="relative w-full max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      {isCompletingSignIn ? (
        <div
          className="fixed inset-0 z-50 flex flex-col items-center justify-center gap-3 bg-white/90 px-6 text-center backdrop-blur-[1px]"
          role="status"
          aria-live="polite"
          aria-busy="true"
        >
          <Spinner className="h-9 w-9" />
          <p className="text-sm font-medium text-gray-800">Signing you in…</p>
          <p className="max-w-xs text-xs text-gray-500">
            Continue in your browser if a Google or GitHub window opened. This can take a few seconds.
          </p>
        </div>
      ) : null}
      <h1 className="mb-2 text-2xl font-semibold">Sign in to DocGuard</h1>
      <p className="mb-6 text-sm text-gray-500">
        Use email/password, Google, or GitHub to access your dashboard.
      </p>
      <div ref={authMountRef}>
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
