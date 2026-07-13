import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { Markdown } from "@/components/markdown";
import { ErrorState, LoadingState } from "@/components/query-states";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getSpecDetail } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

// Visualização rápida de uma spec num modal (última versão renderizada).
// Para histórico de versões e diff, o rodapé leva à página completa da spec.
export function SpecViewerModal({
  projectId,
  specId,
  onClose,
}: {
  projectId: string;
  specId: string | null;
  onClose: () => void;
}) {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["spec", projectId, specId],
    queryFn: () => getSpecDetail(projectId, specId as string),
    enabled: specId !== null, // só busca quando o modal está aberto
  });

  const latest = data?.versions[0];

  return (
    <Dialog open={specId !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex max-h-[85vh] max-w-3xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4">
          <DialogTitle className="pr-8 text-left text-lg">{data?.spec.title ?? "Spec"}</DialogTitle>
          <DialogDescription className="text-left font-mono text-xs">
            {data?.spec.path}
            {latest && (
              <>
                {" · "}
                {formatDateTime(latest.commitDate)} ·{" "}
                <span className="rounded bg-muted px-1 py-0.5 text-foreground">
                  {latest.commitSha.slice(0, 7)}
                </span>
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
          {isLoading && <LoadingState label="Carregando spec…" />}
          {isError && <ErrorState message={error instanceof Error ? error.message : undefined} />}
          {latest && <Markdown>{latest.content}</Markdown>}
        </div>

        {data && (
          <div className="flex items-center justify-between gap-3 border-t border-border px-6 py-3">
            <span className="font-mono text-xs text-muted-foreground">
              {data.versions.length} versão(ões)
            </span>
            <Link
              to="/projects/$projectId/specs/$specId"
              params={{ projectId, specId: data.spec.id }}
              className="rounded-md border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground transition-colors hover:border-primary/40 hover:text-primary"
            >
              Ver histórico e diff →
            </Link>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
