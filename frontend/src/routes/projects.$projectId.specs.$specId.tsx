import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { Markdown } from "@/components/markdown";
import { ErrorState, LoadingState } from "@/components/query-states";
import { getSpecDetail } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { z } from "zod";

const searchSchema = z.object({
  v: z.string().optional(),
});

export const Route = createFileRoute("/projects/$projectId/specs/$specId")({
  validateSearch: searchSchema,
  head: () => ({
    meta: [{ title: "Spec — spec-monitor" }],
  }),
  component: SpecPage,
});

function SpecPage() {
  const { projectId, specId } = Route.useParams();
  const search = Route.useSearch();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["spec", projectId, specId],
    queryFn: () => getSpecDetail(projectId, specId),
  });

  if (isLoading) {
    return (
      <AppShell>
        <LoadingState label="Carregando spec…" />
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
  const selectedId = search.v ?? versions[0]?.id;
  const selectedIndex = versions.findIndex((v: (typeof versions)[number]) => v.id === selectedId);
  const selected = versions[selectedIndex] ?? versions[0];
  const previous = versions[selectedIndex + 1];

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
        <span className="text-foreground">specs/{spec.id}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight">{spec.title}</h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{spec.path}</p>
        </div>
        {previous && (
          <Link
            to="/projects/$projectId/specs/$specId/diff"
            params={{ projectId: project.id, specId: spec.id }}
            search={{ from: previous.id, to: selected.id }}
            className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground transition-colors hover:border-primary/40 hover:text-primary"
          >
            <span>Ver diff</span>
            <span className="font-mono text-xs text-muted-foreground">
              {previous.commitSha.slice(0, 7)} → {selected.commitSha.slice(0, 7)}
            </span>
          </Link>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        {/* Content */}
        <section className="rounded-lg border border-border bg-card">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
            <div>
              <div className="flex items-center gap-2 font-mono text-xs">
                <span className="rounded bg-muted px-1.5 py-0.5 text-foreground">
                  {selected.commitSha.slice(0, 7)}
                </span>
                <span className="text-muted-foreground">{formatDateTime(selected.commitDate)}</span>
              </div>
              <div className="mt-1 text-sm text-foreground">{selected.commitMessage}</div>
              <div className="text-[11px] text-muted-foreground">por {selected.author}</div>
            </div>
            {selectedIndex === 0 && (
              <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary">
                versão atual
              </span>
            )}
          </header>
          <div className="px-6 py-5">
            <Markdown>{selected.content}</Markdown>
          </div>
        </section>

        {/* Timeline */}
        <aside className="rounded-lg border border-border bg-card">
          <header className="flex items-center justify-between border-b border-border px-4 py-3">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Histórico
            </div>
            <div className="font-mono text-xs text-muted-foreground">{versions.length} versões</div>
          </header>

          <ol className="relative px-4 py-4">
            <div className="absolute left-[26px] top-6 bottom-6 w-px bg-border" />
            {versions.map((v: (typeof versions)[number], i: number) => {
              const isSelected = v.id === selected.id;
              const next = versions[i + 1];
              return (
                <li key={v.id} className="relative pb-4 pl-8 last:pb-0">
                  <span
                    className={`absolute left-[9px] top-1.5 h-3 w-3 rounded-full border-2 ${
                      isSelected ? "border-primary bg-primary" : "border-border bg-card"
                    }`}
                  />
                  <Link
                    to="/projects/$projectId/specs/$specId"
                    params={{ projectId: project.id, specId: spec.id }}
                    search={{ v: v.id }}
                    className={`block rounded-md p-2 transition-colors ${
                      isSelected ? "bg-primary/10 ring-1 ring-primary/30" : "hover:bg-accent/60"
                    }`}
                  >
                    <div className="flex items-center gap-2 font-mono text-[11px] text-muted-foreground">
                      <span
                        className={`rounded px-1 py-0.5 ${
                          isSelected ? "bg-primary/20 text-primary" : "bg-muted text-foreground"
                        }`}
                      >
                        {v.commitSha.slice(0, 7)}
                      </span>
                      <span>{formatDateTime(v.commitDate)}</span>
                    </div>
                    <div className="mt-1 line-clamp-2 text-sm text-foreground">
                      {v.commitMessage}
                    </div>
                    <div className="mt-0.5 text-[11px] text-muted-foreground">por {v.author}</div>
                  </Link>
                  {next && (
                    <Link
                      to="/projects/$projectId/specs/$specId/diff"
                      params={{ projectId: project.id, specId: spec.id }}
                      search={{ from: next.id, to: v.id }}
                      className="ml-2 mt-1 inline-block font-mono text-[10px] text-muted-foreground hover:text-primary"
                    >
                      ↕ ver diff com {next.commitSha.slice(0, 7)}
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        </aside>
      </div>
    </AppShell>
  );
}
