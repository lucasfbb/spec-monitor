import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { ErrorState, LoadingState } from "@/components/query-states";
import { getSpecDetail } from "@/lib/api";
import { diffLines, diffStats } from "@/lib/diff";
import { formatDateTime } from "@/lib/format";
import { z } from "zod";

const searchSchema = z.object({
  from: z.string(),
  to: z.string(),
});

export const Route = createFileRoute("/projects/$projectId/specs/$specId/diff")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Diff — spec-monitor" }, { name: "robots", content: "noindex" }],
  }),
  component: DiffPage,
});

function DiffPage() {
  const { projectId, specId } = Route.useParams();
  const { from, to } = Route.useSearch();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["spec", projectId, specId],
    queryFn: () => getSpecDetail(projectId, specId),
  });

  if (isLoading) {
    return (
      <AppShell>
        <LoadingState label="Carregando diff…" />
      </AppShell>
    );
  }
  if (isError || !data) {
    return (
      <AppShell>
        <ErrorState message={error instanceof Error ? error.message : undefined} />
      </AppShell>
    );
  }

  const { project, spec, versions } = data;
  const vFrom =
    versions.find((v: (typeof versions)[number]) => v.id === from) ?? versions[versions.length - 1];
  const vTo = versions.find((v: (typeof versions)[number]) => v.id === to) ?? versions[0];

  const lines = diffLines(vFrom.content, vTo.content);
  const stats = diffStats(lines);

  return (
    <AppShell>
      <nav className="mb-2 font-mono text-xs text-muted-foreground">
        <Link to="/" className="hover:text-foreground">
          projetos
        </Link>
        <span className="mx-2">/</span>
        <Link
          to="/projects/$projectId"
          params={{ projectId: project.id }}
          className="hover:text-foreground"
        >
          {project.id}
        </Link>
        <span className="mx-2">/</span>
        <Link
          to="/projects/$projectId/specs/$specId"
          params={{ projectId: project.id, specId: spec.id }}
          className="hover:text-foreground"
        >
          specs/{spec.id}
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">diff</span>
      </nav>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Diff — {spec.title}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-2 font-mono text-xs">
            <span className="rounded bg-muted px-1.5 py-0.5 text-foreground">
              {vFrom.commitSha.slice(0, 7)}
            </span>
            <span className="text-muted-foreground">→</span>
            <span className="rounded bg-muted px-1.5 py-0.5 text-foreground">
              {vTo.commitSha.slice(0, 7)}
            </span>
            <span className="ml-3 text-diff-add-fg">+{stats.add}</span>
            <span className="text-diff-del-fg">−{stats.del}</span>
          </div>
        </div>
        <Link
          to="/projects/$projectId/specs/$specId"
          params={{ projectId: project.id, specId: spec.id }}
          search={{ v: vTo.id }}
          className="rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/40 hover:text-primary"
        >
          ← Voltar para a spec
        </Link>
      </div>

      <div className="mt-6 grid gap-2 sm:grid-cols-2">
        <CommitCard label="antes" v={vFrom} accent="del" />
        <CommitCard label="depois" v={vTo} accent="add" />
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-border bg-card">
        <div className="max-h-[70vh] overflow-auto">
          <table className="w-full border-collapse font-mono text-[12.5px] leading-[1.55]">
            <tbody>
              {lines.map((l, i) => {
                const bg = l.kind === "add" ? "bg-diff-add" : l.kind === "del" ? "bg-diff-del" : "";
                const sign = l.kind === "add" ? "+" : l.kind === "del" ? "−" : " ";
                const signColor =
                  l.kind === "add"
                    ? "text-diff-add-fg"
                    : l.kind === "del"
                      ? "text-diff-del-fg"
                      : "text-muted-foreground";
                return (
                  <tr key={i} className={bg}>
                    <td className="w-12 select-none border-r border-border/60 px-2 py-0.5 text-right text-muted-foreground/70">
                      {l.oldNo ?? ""}
                    </td>
                    <td className="w-12 select-none border-r border-border/60 px-2 py-0.5 text-right text-muted-foreground/70">
                      {l.newNo ?? ""}
                    </td>
                    <td className={`w-6 select-none px-2 py-0.5 text-center ${signColor}`}>
                      {sign}
                    </td>
                    <td className="whitespace-pre-wrap break-words px-2 py-0.5 text-foreground">
                      {l.text || " "}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </AppShell>
  );
}

function CommitCard({
  label,
  v,
  accent,
}: {
  label: string;
  v: { commitSha: string; commitDate: string; commitMessage: string; author: string };
  accent: "add" | "del";
}) {
  const border = accent === "add" ? "border-diff-add-fg/30" : "border-diff-del-fg/30";
  return (
    <div className={`rounded-lg border ${border} bg-card p-4`}>
      <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className="mt-1 flex items-center gap-2 font-mono text-xs">
        <span className="rounded bg-muted px-1.5 py-0.5 text-foreground">
          {v.commitSha.slice(0, 7)}
        </span>
        <span className="text-muted-foreground">{formatDateTime(v.commitDate)}</span>
      </div>
      <div className="mt-1 text-sm text-foreground">{v.commitMessage}</div>
      <div className="text-[11px] text-muted-foreground">por {v.author}</div>
    </div>
  );
}
