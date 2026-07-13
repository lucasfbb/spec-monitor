import { cn } from "@/lib/utils";
import type { SyncStatus } from "@/lib/api";

export function SyncBadge({ status, className }: { status: SyncStatus; className?: string }) {
  const map: Record<SyncStatus, { label: string; classes: string; dot: string }> = {
    ok: {
      label: "sync ok",
      classes: "border-success/30 bg-success/10 text-success",
      dot: "bg-success",
    },
    failed: {
      label: "sync falhou",
      classes: "border-destructive/40 bg-destructive/10 text-destructive",
      dot: "bg-destructive",
    },
    never: {
      label: "nunca sincronizado",
      classes: "border-border bg-muted text-muted-foreground",
      dot: "bg-muted-foreground",
    },
  };
  const it = map[status];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs font-medium",
        it.classes,
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", it.dot)} />
      {it.label}
    </span>
  );
}
