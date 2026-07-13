import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/app-shell";
import { ErrorState, LoadingState } from "@/components/query-states";
import { ApiError, createUser, listUsers } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { useState, type FormEvent } from "react";

export const Route = createFileRoute("/users")({
  head: () => ({
    meta: [
      { title: "Usuários — spec-monitor" },
      { name: "description", content: "Gestão de usuários do spec-monitor." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: UsersPage,
});

function UsersPage() {
  const queryClient = useQueryClient();
  const {
    data: users,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["users"],
    queryFn: listUsers,
  });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "viewer">("viewer");

  const create = useMutation({
    mutationFn: () => createUser(email, password, role === "admin"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      setEmail("");
      setPassword("");
      setRole("viewer");
    },
  });
  const errorMsg =
    create.error instanceof ApiError
      ? create.error.message
      : create.isError
        ? "Não foi possível criar o usuário."
        : null;

  const invite = (e: FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;
    create.mutate();
  };

  if (isLoading) {
    return (
      <AppShell>
        <LoadingState label="Carregando usuários…" />
      </AppShell>
    );
  }
  if (isError || !users) {
    return (
      <AppShell>
        <ErrorState message={error instanceof Error ? error.message : undefined} />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div>
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Admin</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Usuários</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Só administradores podem cadastrar projetos e tokens. Viewers têm acesso somente leitura.
        </p>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="overflow-hidden rounded-lg border border-border bg-card">
          <table className="w-full text-sm">
            <thead className="bg-muted/60">
              <tr className="text-left text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                <th className="px-4 py-3">E-mail</th>
                <th className="px-4 py-3">Papel</th>
                <th className="px-4 py-3">Criado em</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-border">
                  <td className="px-4 py-3 font-mono text-[13px] text-foreground">{u.email}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${
                        u.role === "admin"
                          ? "border-primary/30 bg-primary/10 text-primary"
                          : "border-border bg-muted text-muted-foreground"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(u.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <form onSubmit={invite} className="h-fit rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold">Criar usuário</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            O usuário entra com o e-mail e a senha definidos aqui.
          </p>

          <label className="mt-4 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            E-mail
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="pessoa@empresa.com"
            className="mt-1.5 w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/30"
          />

          <label className="mt-4 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Senha
          </label>
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="mínimo 8 caracteres"
            autoComplete="new-password"
            className="mt-1.5 w-full rounded-md border border-border bg-input px-3 py-2 font-mono text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/30"
          />

          <label className="mt-4 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Papel
          </label>
          <div className="mt-1.5 grid grid-cols-2 gap-2">
            {(["viewer", "admin"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRole(r)}
                className={`rounded-md border px-3 py-2 text-sm capitalize transition-colors ${
                  role === r
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border bg-background text-muted-foreground hover:text-foreground"
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          {errorMsg && (
            <p className="mt-4 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
              {errorMsg}
            </p>
          )}
          <button
            type="submit"
            disabled={create.isPending}
            className="mt-5 w-full rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {create.isPending ? "Criando…" : "Criar usuário"}
          </button>
        </form>
      </div>
    </AppShell>
  );
}
