import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { ApiError, createProject } from "@/lib/api";

export const Route = createFileRoute("/projects/new")({
  head: () => ({
    meta: [
      { title: "Novo projeto — spec-monitor" },
      { name: "description", content: "Conecte um repositório do GitHub ao spec-monitor." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: NewProjectPage,
});

function Field({
  label,
  hint,
  children,
  mono,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      <div className={mono ? "font-mono" : undefined}>{children}</div>
      {hint && <p className="mt-1.5 text-xs text-muted-foreground">{hint}</p>}
    </div>
  );
}

const inputClass =
  "w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/30";

function NewProjectPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    name: "",
    repo: "",
    branch: "main",
    specsDir: "specs",
    statusPath: "STATUS.md",
    token: "",
  });

  const mutation = useMutation({
    mutationFn: () =>
      createProject({
        name: form.name,
        repo: form.repo,
        branch: form.branch,
        specsDir: form.specsDir,
        statusPath: form.statusPath,
        token: form.token || undefined,
      }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      navigate({ to: "/projects/$projectId", params: { projectId: project.id } });
    },
  });
  const errorMsg =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.isError
        ? "Não foi possível cadastrar o projeto."
        : null;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  return (
    <AppShell>
      <div className="mx-auto max-w-2xl">
        <nav className="mb-2 font-mono text-xs text-muted-foreground">
          <Link to="/" className="hover:text-foreground">
            projetos
          </Link>
          <span className="mx-2">/</span>
          <span className="text-foreground">novo</span>
        </nav>
        <h1 className="text-2xl font-semibold tracking-tight">Conectar novo projeto</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          O spec-monitor vai sincronizar os arquivos <code className="font-mono">.md</code> da pasta
          de specs e o <code className="font-mono">STATUS.md</code> a cada 15 minutos.
        </p>

        <form
          onSubmit={onSubmit}
          className="mt-8 space-y-5 rounded-lg border border-border bg-card p-6"
        >
          <Field label="Nome do projeto">
            <input
              className={inputClass}
              placeholder="LitiSense"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </Field>

          <div className="grid gap-5 sm:grid-cols-[1fr_180px]">
            <Field label="Repositório" hint="Formato dono/repo — apenas o path, sem URL." mono>
              <input
                className={inputClass}
                placeholder="lucasfbb/litisense"
                value={form.repo}
                onChange={(e) => setForm({ ...form, repo: e.target.value })}
                required
              />
            </Field>
            <Field label="Branch" mono>
              <input
                className={inputClass}
                value={form.branch}
                onChange={(e) => setForm({ ...form, branch: e.target.value })}
                required
              />
            </Field>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Pasta de specs" hint="Onde ficam os arquivos numerados 00, 01, 02…" mono>
              <input
                className={inputClass}
                value={form.specsDir}
                onChange={(e) => setForm({ ...form, specsDir: e.target.value })}
                required
              />
            </Field>
            <Field label="Arquivo de status" mono>
              <input
                className={inputClass}
                value={form.statusPath}
                onChange={(e) => setForm({ ...form, statusPath: e.target.value })}
                required
              />
            </Field>
          </div>

          <Field
            label="Token de acesso ao GitHub"
            hint="Necessário para repositórios privados — use um fine-grained PAT com permissão apenas de leitura (Contents: Read). Fica guardado no banco do seu servidor."
            mono
          >
            <input
              type="password"
              className={inputClass}
              placeholder="ghp_••••••••••••••••••••••••"
              value={form.token}
              onChange={(e) => setForm({ ...form, token: e.target.value })}
              autoComplete="off"
            />
          </Field>

          {errorMsg && (
            <p className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {errorMsg}
            </p>
          )}
          <div className="flex items-center justify-end gap-2 border-t border-border pt-5">
            <Link
              to="/"
              className="rounded-md border border-border bg-background px-3.5 py-2 text-sm font-medium text-foreground transition-colors hover:bg-accent"
            >
              Cancelar
            </Link>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {mutation.isPending ? "Conectando e sincronizando…" : "Conectar e sincronizar"}
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
