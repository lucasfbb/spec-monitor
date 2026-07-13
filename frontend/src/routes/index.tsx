import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { SyncBadge } from "@/components/sync-badge";
import { ErrorState, LoadingState } from "@/components/query-states";
import { listProjects } from "@/lib/api";
import { formatRelative } from "@/lib/format";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Projetos — spec-monitor" },
      {
        name: "description",
        content: "Painel de projetos monitorados pelo spec-monitor.",
      },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const {
    data: projects,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  if (isLoading) {
    return (
      <AppShell>
        <LoadingState label="Carregando projetos…" />
      </AppShell>
    );
  }
  if (isError || !projects) {
    return (
      <AppShell>
        <ErrorState message={error instanceof Error ? error.message : undefined} />
      </AppShell>
    );
  }

  const totalSpecs = projects.reduce((s, p) => s + p.specsCount, 0);
  const okCount = projects.filter((p) => p.lastSyncOk === "ok").length;
  const failedCount = projects.filter((p) => p.lastSyncOk === "failed").length;

  return (
    <AppShell>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Dashboard
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Projetos</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {projects.length} projetos · {totalSpecs} specs monitoradas ·{" "}
            <span className="text-success">{okCount} ok</span>
            {failedCount > 0 && (
              <>
                {" · "}
                <span className="text-destructive">{failedCount} com falha</span>
              </>
            )}
          </p>
        </div>
        <Link
          to="/projects/new"
          className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
        >
          <span className="text-base leading-none">+</span> Novo projeto
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => (
          <Link
            key={p.id}
            to="/projects/$projectId"
            params={{ projectId: p.id }}
            className="group flex flex-col rounded-lg border border-border bg-card p-5 transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-lg hover:shadow-primary/5"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate text-base font-semibold tracking-tight text-foreground group-hover:text-primary">
                  {p.name}
                </h3>
                <p className="mt-0.5 truncate font-mono text-xs text-muted-foreground">{p.repo}</p>
              </div>
              <SyncBadge status={p.lastSyncOk} />
            </div>

            <div className="mt-5 grid grid-cols-3 gap-2 border-t border-border pt-4 text-xs">
              <div>
                <div className="text-muted-foreground">Branch</div>
                <div className="mt-0.5 truncate font-mono text-foreground">{p.branch}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Specs</div>
                <div className="mt-0.5 font-mono text-foreground">{p.specsCount}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Último sync</div>
                <div className="mt-0.5 truncate text-foreground">
                  {formatRelative(p.lastSyncAt)}
                </div>
              </div>
            </div>
          </Link>
        ))}

        <Link
          to="/projects/new"
          className="flex min-h-[172px] flex-col items-center justify-center rounded-lg border border-dashed border-border bg-card/30 p-5 text-muted-foreground transition-colors hover:border-primary/50 hover:bg-card hover:text-foreground"
        >
          <div className="grid h-10 w-10 place-items-center rounded-full border border-dashed border-current text-xl">
            +
          </div>
          <div className="mt-3 text-sm font-medium">Adicionar projeto</div>
          <div className="mt-1 font-mono text-[11px] uppercase tracking-widest">
            conectar repo do github
          </div>
        </Link>
      </div>
    </AppShell>
  );
}
