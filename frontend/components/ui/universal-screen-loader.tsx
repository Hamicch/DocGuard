import { Spinner } from "@/components/ui/spinner";
import { cn } from "@/lib/utils";

export type UniversalScreenLoaderVariant = "page" | "panel" | "inline";

export type UniversalScreenLoaderProps = {
  message?: string;
  submessage?: string;
  /**
   * - `page` — route `loading.tsx`: compact centered block (not full-viewport bleed).
   * - `panel` — `absolute inset-0` over a **relative** parent (card, form). Does not cover the whole window.
   * - `inline` — spinner + text in a row (headers, button rows).
   */
  variant?: UniversalScreenLoaderVariant;
  className?: string;
  spinnerClassName?: string;
};

export function UniversalScreenLoader({
  message = "Loading…",
  submessage,
  variant = "page",
  className,
  spinnerClassName = "h-8 w-8",
}: UniversalScreenLoaderProps) {
  const body = (
    <div className="flex flex-col items-center justify-center gap-2 text-center">
      <Spinner className={spinnerClassName} />
      <p className="text-sm font-medium text-gray-800">{message}</p>
      {submessage ? (
        <p className="max-w-xs text-xs leading-relaxed text-gray-500">{submessage}</p>
      ) : null}
    </div>
  );

  if (variant === "inline") {
    return (
      <span
        className={cn("inline-flex items-center gap-2 text-sm text-gray-600", className)}
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <Spinner className={spinnerClassName} />
        <span>{message}</span>
      </span>
    );
  }

  if (variant === "panel") {
    return (
      <div
        className={cn(
          "absolute inset-0 z-10 flex flex-col items-center justify-center rounded-[inherit] bg-white/85 px-3 backdrop-blur-[0.5px]",
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
    <div
      className={cn(
        "flex w-full flex-col items-center justify-center py-16 text-gray-900",
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="rounded-lg border border-gray-200 bg-white px-8 py-10 shadow-sm">{body}</div>
    </div>
  );
}
