import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

export type UniversalScreenLoaderVariant = "page" | "overlay";

export type UniversalScreenLoaderProps = {
  message?: string;
  submessage?: string;
  variant?: UniversalScreenLoaderVariant;
  className?: string;
  spinnerClassName?: string;
};

/**
 * Full-viewport loading UI: `page` for route `loading.tsx`, `overlay` for client mutations (auth, forms).
 */
export function UniversalScreenLoader({
  message = "Loading…",
  submessage,
  variant = "page",
  className,
  spinnerClassName = "h-9 w-9",
}: UniversalScreenLoaderProps) {
  const body = (
    <div className="flex flex-col items-center justify-center gap-3 text-center">
      <Spinner className={spinnerClassName} />
      <p className="text-sm font-medium text-gray-800">{message}</p>
      {submessage ? (
        <p className="max-w-sm text-xs leading-relaxed text-gray-500">{submessage}</p>
      ) : null}
    </div>
  );

  if (variant === "overlay") {
    return (
      <div
        className={cn(
          "fixed inset-0 z-[100] flex flex-col items-center justify-center bg-white/90 px-6 backdrop-blur-[1px]",
          className,
        )}
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        {body}
      </div>
    );
  }

  return (
    <main
      className={cn(
        "flex min-h-[100dvh] w-full flex-col items-center justify-center bg-gray-50 p-6",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="rounded-lg border border-gray-200 bg-white px-10 py-12 shadow-sm">{body}</div>
    </main>
  );
}
