import { Spinner } from "@/components/ui/spinner";

type RouteAuthLoadingProps = {
  message?: string;
};

export function RouteAuthLoading({ message = "Loading…" }: RouteAuthLoadingProps) {
  return (
    <main className="flex min-h-[55vh] flex-col items-center justify-center gap-3 p-6">
      <Spinner className="h-8 w-8" />
      <p className="text-center text-sm text-gray-600">{message}</p>
    </main>
  );
}
