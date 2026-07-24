import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { AppShell } from "@/components/app-shell";
import { StaleBadge, SyncBadge } from "@/components/sync-badge";
import { Markdown } from "@/components/markdown";
import { ErrorState, LoadingState } from "@/components/query-states";
import { ProjectMembers } from "@/components/project-members";
import { SpecViewerModal } from "@/components/spec-viewer-modal";
import { CheckpointTimeline } from "@/components/checkpoint-timeline";
import { deleteProject, getMe, getProjectDetail, syncProject } from "@/lib/api";
import { formatDate, formatDateTime, formatRelative } from "@/lib/format";

export const Route = createFileRoute("/projects/$projectId")({
  head: () => ({
    meta: [{ title: "Projeto — spec-monitor" }],
  }),
  component: ProjectPage,
});

function GitHubIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 .5C5.65.5.5 5.65.5 12A11.5 11.5 0 0 0 8.36 22.94c.58.11.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.53-1.34-1.29-1.7-1.29-1.7-1.05-.72.08-.71.08-.71 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.51-1.47.11-3.06 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.24 2.77.12 3.06.74.81 1.19 1.83 1.19 3.09 0 4.41-2.69 5.38-5.26 5.67.41.36.77 1.06.77 2.14v3.17c0 .31.21.68.79.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

function ProjectPage() {
  const { projectId } = Route.useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProjectDetail(projectId),
  });
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: getMe, retry: false });
  const isAdmin = me?.role === "admin";
  const [openSpec, setOpenSpec] = useState<string | null>(null);

  const sync = useMutation({
    mutationFn: () => syncProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate({ to: "/" });
    },
  });

  if (isLoading) {
    return (
      <AppShell>
        <LoadingState label="Carregando projeto…" />
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

  const { project, specs, checkpoints, latestStatus: status, recentActivity: activity } = data;

  return (
    <AppShell>
      {/* Header */}
      <nav className="mb-2 font-mono text-xs text-muted-foreground">
        <Link to="/" className="hover:text-foreground">
          projetos
        </Link>
        <span className="mx-2">/</span>
        <span className="text-foreground">{project.id}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <h1 className="truncate text-2xl font-semibold tracking-tight">{project.name}</h1>
            <SyncBadge status={project.lastSyncOk} />
            <StaleBadge staleness={project.staleness} />
          </div>
          <a
            href={`https://github.com/${project.repo}`}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-primary"
          >
            <GitHubIcon className="h-3.5 w-3.5" />
            {project.repo}
            <span className="text-muted-foreground/60">·</span>
            <span>{project.branch}</span>
          </a>
        </div>

        <div className={`flex flex-wrap items-center gap-2 ${isAdmin ? "" : "hidden"}`}>
          <button
            type="button"
            onClick={() => sync.mutate()}
            disabled={sync.isPending}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            <svg
              viewBox="0 0 20 20"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className={`h-3.5 w-3.5 ${sync.isPending ? "animate-spin" : ""}`}
            >
              <path
                d="M4 10a6 6 0 0 1 10.24-4.24M16 10a6 6 0 0 1-10.24 4.24M14 4v4h-4M6 16v-4h4"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            {sync.isPending ? "Sincronizando…" : "Sincronizar agora"}
          </button>
          <button
            type="button"
            onClick={() => {
              if (confirm("Remover o projeto e todo o histórico monitorado?")) remove.mutate();
            }}
            disabled={remove.isPending}
            className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm font-medium text-destructive transition-colors hover:bg-destructive/10 disabled:opacity-60"
          >
            {remove.isPending ? "Removendo…" : "Remover projeto"}
          </button>
        </div>
      </div>

      {/* Stat strip */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Specs" value={String(project.specsCount)} />
        <Stat
          label="Versões totais"
          value={String(specs.reduce((s, x) => s + x.versionsCount, 0))}
        />
        <Stat label="Último sync" value={formatRelative(project.lastSyncAt)} />
        <Stat label="Status commit" value={status ? status.commitSha.slice(0, 7) : "—"} mono />
      </div>

      {/* Two-column body */}
      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        {/* Main column: STATUS.md */}
        <section className="rounded-lg border border-border bg-card">
          <header className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3">
            <div>
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                STATUS.md
              </div>
              <div className="mt-0.5 font-mono text-xs text-muted-foreground">
                {project.statusPath}
              </div>
            </div>
            {status && (
              <div className="text-right">
                <div className="font-mono text-xs">
                  <span className="rounded bg-muted px-1.5 py-0.5 text-foreground">
                    {status.commitSha.slice(0, 7)}
                  </span>
                </div>
                <div className="mt-0.5 text-[11px] text-muted-foreground">
                  {formatDateTime(status.commitDate)}
                </div>
              </div>
            )}
          </header>
          <div className="px-6 py-5">
            {status ? (
              <Markdown>{status.content}</Markdown>
            ) : (
              <div className="py-16 text-center text-sm text-muted-foreground">
                <div className="mx-auto grid h-10 w-10 place-items-center rounded-full border border-dashed border-border text-muted-foreground">
                  ?
                </div>
                <p className="mt-3">Este projeto ainda não foi sincronizado.</p>
                <p className="mt-1 text-xs">
                  Clique em <span className="text-foreground">Sincronizar agora</span> para buscar o
                  STATUS.md do repositório.
                </p>
              </div>
            )}
          </div>
        </section>

        {/* Side column */}
        <aside className="space-y-6">
          {/* Specs table */}
          <div className="rounded-lg border border-border bg-card">
            <header className="flex items-center justify-between border-b border-border px-4 py-3">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Specs
              </div>
              <div className="font-mono text-xs text-muted-foreground">{specs.length}</div>
            </header>
            <ul className="max-h-[480px] overflow-y-auto">
              {specs.map((s) => (
                <li key={s.id} className="border-b border-border last:border-b-0">
                  <button
                    type="button"
                    onClick={() => setOpenSpec(s.id)}
                    className="group flex w-full items-start gap-3 px-4 py-2.5 text-left transition-colors hover:bg-accent/50"
                  >
                    <span className="mt-0.5 font-mono text-xs text-muted-foreground">{s.id}</span>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm text-foreground group-hover:text-primary">
                        {s.title.replace(/^\d+\s*—\s*/, "")}
                      </div>
                      <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted-foreground">
                        <span>{formatDate(s.lastUpdated)}</span>
                        <span>·</span>
                        <span className="font-mono">{s.versionsCount} ver</span>
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          <CheckpointTimeline checkpoints={checkpoints ?? []} />

          {/* Activity */}
          <div className="rounded-lg border border-border bg-card">
            <header className="border-b border-border px-4 py-3">
              <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Atividade recente
              </div>
            </header>
            <ul className="divide-y divide-border">
              {activity.map((a, i) => (
                <li key={i} className="px-4 py-2.5">
                  <Link
                    to="/projects/$projectId/specs/$specId"
                    params={{ projectId: project.id, specId: a.specId }}
                    className="block group"
                  >
                    <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                      <span className="rounded bg-muted px-1 py-0.5 text-foreground">
                        {a.commitSha.slice(0, 7)}
                      </span>
                      <span>{formatRelative(a.date)}</span>
                      <span>·</span>
                      <span>spec-{a.specId}</span>
                    </div>
                    <div className="mt-1 text-sm text-foreground group-hover:text-primary">
                      {a.commitMessage}
                    </div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">por {a.author}</div>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {isAdmin && <ProjectMembers projectId={projectId} />}
        </aside>
      </div>

      <SpecViewerModal projectId={projectId} specId={openSpec} onClose={() => setOpenSpec(null)} />
    </AppShell>
  );
}

function Stat({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3">
      <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </div>
      <div className={`mt-1 text-lg font-semibold ${mono ? "font-mono" : ""}`}>{value}</div>
    </div>
  );
}
