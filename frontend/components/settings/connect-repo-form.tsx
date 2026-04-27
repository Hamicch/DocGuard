"use client";

import { FormEvent, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { UniversalScreenLoader } from "@/components/ui/universal-screen-loader";
import { connectRepo } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

export function ConnectRepoForm() {
  const [fullName, setFullName] = useState("");
  const [installationId, setInstallationId] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    startTransition(async () => {
      setError(null);
      setMessage(null);

      try {
        const installation = Number.parseInt(installationId, 10);
        if (!fullName.includes("/") || Number.isNaN(installation)) {
          setError("Enter full_name as owner/repo and a numeric installation ID.");
          return;
        }

        const supabase = createClient();
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (!session) {
          setError("Session expired. Please sign in again.");
          return;
        }

        await connectRepo(session.access_token, {
          full_name: fullName.trim(),
          github_installation_id: installation,
        });

        setMessage("Repository connected successfully.");
        setFullName("");
        setInstallationId("");
        router.refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to connect repository.");
      }
    });
  };

  return (
    <form onSubmit={onSubmit} className="relative overflow-hidden rounded-lg border bg-white p-4">
      {isPending ? (
        <UniversalScreenLoader
          variant="panel"
          message="Connecting repository…"
          submessage="Linking this installation to your DocGuard account."
        />
      ) : null}
      <h2 className="text-lg font-semibold">Connect Repository</h2>
      <div className="space-y-1">
        <label className="text-sm font-medium" htmlFor="fullName">
          Repository (owner/repo)
        </label>
        <input
          id="fullName"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          placeholder="owner/repo"
          className="w-full rounded border px-3 py-2 text-sm"
          required
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm font-medium" htmlFor="installationId">
          GitHub Installation ID
        </label>
        <input
          id="installationId"
          value={installationId}
          onChange={(e) => setInstallationId(e.target.value)}
          placeholder="12345678"
          className="w-full rounded border px-3 py-2 text-sm"
          required
        />
      </div>
      <button
        type="submit"
        disabled={isPending}
        className="cursor-pointer rounded bg-black px-4 py-2 text-sm text-white disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? "Connecting..." : "Connect"}
      </button>
      {message ? <p className="text-sm text-green-700">{message}</p> : null}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </form>
  );
}
