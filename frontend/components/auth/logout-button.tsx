"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { UniversalScreenLoader } from "@/components/ui/universal-screen-loader";
import { createClient } from "@/lib/supabase/client";

export function LogoutButton() {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onLogout = async () => {
    setLoading(true);
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
      router.replace("/login");
      router.refresh();
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {loading ? <UniversalScreenLoader variant="overlay" message="Signing out…" /> : null}
      <button
        type="button"
        onClick={onLogout}
        disabled={loading}
        className="rounded border px-3 py-1 text-sm hover:bg-gray-50 disabled:opacity-50"
      >
        {loading ? "Signing out…" : "Log out"}
      </button>
    </>
  );
}
