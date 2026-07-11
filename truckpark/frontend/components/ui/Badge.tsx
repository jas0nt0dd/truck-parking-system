import { cn } from "@/lib/utils";
import { statusBadgeClasses } from "@/lib/utils";

export function Badge({ status, children }: { status: string; children: React.ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize",
        statusBadgeClasses(status)
      )}
    >
      {children}
    </span>
  );
}
