import { useState } from "react";
import { Markdown } from "@/components/markdown";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Checkpoint } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";

// Linha do tempo dos checkpoints (docs/checkpoints/ — convenção padrao-specs).
// Mais recente no topo; clicar abre o conteúdo num modal (já vem no payload
// do detalhe do projeto, sem fetch extra).
export function CheckpointTimeline({ checkpoints }: { checkpoints: Checkpoint[] }) {
  const [open, setOpen] = useState<Checkpoint | null>(null);

  if (checkpoints.length === 0) return null;

  return (
    <div className="rounded-lg border border-border bg-card">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Linha do tempo — checkpoints
        </div>
        <div className="font-mono text-xs text-muted-foreground">{checkpoints.length}</div>
      </header>

      <ol className="relative px-4 py-3">
        {/* trilho vertical */}
        <div aria-hidden className="absolute bottom-5 left-[27px] top-5 w-px bg-border" />
        {checkpoints.map((c, i) => (
          <li key={c.id} className="relative">
            <button
              type="button"
              onClick={() => setOpen(c)}
              className="group flex w-full items-start gap-3 rounded-md px-1 py-2 text-left transition-colors hover:bg-accent/50"
            >
              {/* nó da timeline: número do checkpoint */}
              <span
                className={`relative z-10 mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full border font-mono text-[11px] font-semibold ${
                  i === 0
                    ? "border-primary/60 bg-primary/15 text-primary"
                    : "border-border bg-muted text-muted-foreground group-hover:border-primary/40 group-hover:text-foreground"
                }`}
              >
                {c.number || "•"}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm text-foreground group-hover:text-primary">
                  {c.title.replace(/^Checkpoint\s*#?\d+\s*[—–-]\s*/i, "")}
                </span>
                <span className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span>{formatDate(c.date)}</span>
                  {i === 0 && (
                    <span className="rounded bg-primary/15 px-1.5 py-0.5 font-medium text-primary">
                      mais recente
                    </span>
                  )}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ol>

      <Dialog open={open !== null} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="flex max-h-[85vh] max-w-3xl flex-col gap-0 overflow-hidden p-0">
          <DialogHeader className="border-b border-border px-6 py-4">
            <DialogTitle className="pr-8 text-left text-lg">{open?.title}</DialogTitle>
            <DialogDescription className="text-left font-mono text-xs">
              {open?.path}
              {open?.commitDate && (
                <>
                  {" · "}
                  {formatDateTime(open.commitDate)} ·{" "}
                  <span className="rounded bg-muted px-1 py-0.5 text-foreground">
                    {open.commitSha.slice(0, 7)}
                  </span>
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
            {open && <Markdown>{open.content}</Markdown>}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
