import Link from "next/link";
import { redirect } from "next/navigation";

import { MissingSupabaseEnv } from "@/components/auth/missing-supabase-env";
import { LogoutButton } from "@/components/auth/logout-button";
import { hasSupabaseEnv } from "@/lib/env";
import { getRuns } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

function statusClass(status: string) {
  switch (status) {
    case "completed":
      return "bg-green-100 text-green-800";
    case "failed":
      return "bg-red-100 text-red-800";
    case "running":
      return "bg-blue-100 text-blue-800";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

export default async function RunsPage() {
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

  const runs = await getRuns(session.access_token, 1);

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Audit Runs</h1>
        <div className="flex items-center gap-2">
          <Link href="/settings" className="rounded border px-3 py-1 text-sm hover:bg-gray-50">
            Settings
          </Link>
          <LogoutButton />
        </div>
      </header>

      {runs.items.length === 0 ? (
        <div className="rounded-lg border border-dashed p-8 text-center text-sm text-gray-500">
          No audit runs yet. Open or synchronize a PR to trigger your first run.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="px-4 py-3">PR</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Findings</th>
                <th className="px-4 py-3">Started</th>
              </tr>
            </thead>
            <tbody>
              {runs.items.map((run) => (
                <tr key={run.id} className="border-t">
                  <td className="px-4 py-3">
                    <Link href={`/runs/${run.id}`} className="font-medium hover:underline">
                      #{run.pr_number} {run.pr_title || "(no title)"}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`rounded px-2 py-1 text-xs font-medium ${statusClass(run.status)}`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">{run.finding_count}</td>
                  <td className="px-4 py-3">
                    {new Date(run.started_at).toLocaleString(undefined, {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
