type SpinnerProps = {
  className?: string;
};

export function Spinner({ className = "h-5 w-5" }: SpinnerProps) {
  return (
    <span
      className={`inline-block shrink-0 animate-spin rounded-full border-2 border-gray-200 border-t-gray-900 ${className}`}
      role="status"
      aria-label="Loading"
    />
  );
}
