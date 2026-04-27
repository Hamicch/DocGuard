import Link from "next/link";
import { notFound, redirect } from "next/navigation";

import { MissingSupabaseEnv } from "@/components/auth/missing-supabase-env";
import { LogoutButton } from "@/components/auth/logout-button";
import { FindingActions } from "@/components/runs/finding-actions";
import { hasSupabaseEnv } from "@/lib/env";
import { getRun } from "@/lib/api";
import { createClient } from "@/lib/supabase/server";

function severityClass(severity: string) {
  switch (severity) {
    case "high":
      return "bg-red-100 text-red-700";
    case "medium":
      return "bg-amber-100 text-amber-700";
    default:
      return "bg-blue-100 text-blue-700";
  }
}

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  if (!hasSupabaseEnv) {
    return <MissingSupabaseEnv />;
  }

  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    redirect("/login");
  }

  let data;
  try {
    data = await getRun(session.access_token, id);
  } catch {
    notFound();
  }

  return (
    <main className="mx-auto max-w-5xl p-6">
      <header className="mb-6 flex items-start justify-between gap-3">
        <div>
          <Link href="/runs" className="text-sm text-gray-500 hover:underline">
            ← Back to runs
          </Link>
          <h1 className="mt-2 text-2xl font-semibold">
            Run for PR #{data.run.pr_number} {data.run.pr_title}
          </h1>
        </div>
        <LogoutButton />
      </header>

      <section className="space-y-4">
        {data.findings.length === 0 ? (
          <div className="rounded border border-dashed p-6 text-sm text-gray-500">
            This run completed without findings.
          </div>
        ) : (
          data.findings.map((finding) => (
            <article key={finding.id} className="rounded-lg border bg-white p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span
                  className={`rounded px-2 py-1 text-xs font-medium ${severityClass(finding.severity)}`}
                >
                  {finding.severity}
                </span>
                <span className="rounded bg-gray-100 px-2 py-1 text-xs">{finding.finding_type}</span>
                <span className="text-xs text-gray-500">
                  {finding.file_path}
                  {finding.line_start ? `:${finding.line_start}` : ""}
                </span>
              </div>

              <h2 className="text-base font-semibold">{finding.title}</h2>
              <p className="mt-2 text-sm text-gray-700">{finding.description}</p>

              {finding.proposed_fix ? (
                <div className="mt-3 rounded bg-gray-50 p-3 text-sm">
                  <p className="mb-1 font-medium">Proposed fix</p>
                  <p className="whitespace-pre-wrap text-gray-700">{finding.proposed_fix}</p>
                </div>
              ) : null}

              <p className="mt-3 text-xs text-gray-500">Current action: {finding.user_action}</p>
              <FindingActions findingId={finding.id} />
            </article>
          ))
        )}
      </section>
    </main>
  );
}
