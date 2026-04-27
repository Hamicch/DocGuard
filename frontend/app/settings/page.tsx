import Link from "next/link";
import { redirect } from "next/navigation";

import { MissingSupabaseEnv } from "@/components/auth/missing-supabase-env";
import { LogoutButton } from "@/components/auth/logout-button";
import { ConnectRepoForm } from "@/components/settings/connect-repo-form";
import { hasSupabaseEnv } from "@/lib/env";
import { getRepos } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

export default async function SettingsPage() {
  if (!hasSupabaseEnv) {
    return <MissingSupabaseEnv />;
  }

  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  const repos = await getRepos(session.access_token);

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-6">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/runs" className="cursor-pointer text-sm text-gray-500 hover:text-gray-900">
            ← Back
          </Link>
          <h1 className="text-2xl font-semibold">Settings</h1>
        </div>
        <LogoutButton />
      </header>
      <ConnectRepoForm />

      <section className="rounded-lg border bg-white p-4">
        <h2 className="mb-3 text-lg font-semibold">Connected Repositories</h2>
        {repos.length === 0 ? (
          <p className="text-sm text-gray-500">No repositories connected yet.</p>
        ) : (
          <ul className="space-y-2">
            {repos.map((repo) => (
              <li key={repo.id} className="flex items-center justify-between rounded border p-3 text-sm">
                <span className="font-medium">{repo.full_name}</span>
                <span className="text-gray-500">Install ID: {repo.github_installation_id}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
