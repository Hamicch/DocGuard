export function MissingSupabaseEnv() {
  return (
    <main className="mx-auto max-w-2xl p-6">
      <div className="rounded-lg border border-amber-300 bg-amber-50 p-5">
        <h1 className="text-lg font-semibold text-amber-900">Supabase env vars are missing</h1>
        <p className="mt-2 text-sm text-amber-800">
          Add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` to
          `frontend/.env.local` to enable authentication pages.
        </p>
      </div>
    </main>
  );
}
