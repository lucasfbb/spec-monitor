import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState, type FormEvent } from "react";
import { ApiError, login as apiLogin } from "@/lib/api";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Entrar — spec-monitor" },
      { name: "description", content: "Acesse o painel do spec-monitor." },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => apiLogin(email, password),
    onSuccess: (user) => {
      queryClient.setQueryData(["me"], user);
      navigate({ to: "/" });
    },
  });
  const loading = mutation.isPending;
  const errorMsg =
    mutation.error instanceof ApiError
      ? mutation.error.message
      : mutation.isError
        ? "Não foi possível entrar. Tente novamente."
        : null;

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  return (
    <div className="grid min-h-screen grid-cols-1 bg-background lg:grid-cols-2">
      {/* Left panel — brand + tagline */}
      <div className="relative hidden overflow-hidden border-r border-border bg-card p-10 lg:flex lg:flex-col lg:justify-between">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-md border border-primary/40 bg-primary/10 text-primary">
            <svg
              viewBox="0 0 20 20"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M4 6h12M4 10h8M4 14h12" strokeLinecap="round" />
            </svg>
          </div>
          <span className="font-mono text-sm font-semibold">spec-monitor</span>
        </div>

        <div>
          <h1 className="max-w-md text-3xl font-semibold leading-tight tracking-tight">
            Central de comando para specs
            <span className="text-primary"> de arquitetura</span>.
          </h1>
          <p className="mt-4 max-w-md text-sm text-muted-foreground">
            Sincroniza specs e <code className="font-mono">STATUS.md</code> dos seus repositórios do
            GitHub, guarda toda a linha do tempo de mudanças e mostra diffs entre versões.
          </p>

          <div className="mt-8 space-y-2 font-mono text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <span className="text-success">●</span> 4 projetos monitorados
            </div>
            <div className="flex items-center gap-2">
              <span className="text-success">●</span> 16 specs · 47 versões
            </div>
            <div className="flex items-center gap-2">
              <span className="text-warning">●</span> 1 sync com falha
            </div>
          </div>
        </div>

        <p className="font-mono text-[11px] text-muted-foreground">© 2026 · uso interno</p>
      </div>

      {/* Right panel — form */}
      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="lg:hidden">
            <div className="mb-6 flex items-center gap-2">
              <div className="grid h-8 w-8 place-items-center rounded-md border border-primary/40 bg-primary/10 text-primary">
                <svg
                  viewBox="0 0 20 20"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M4 6h12M4 10h8M4 14h12" strokeLinecap="round" />
                </svg>
              </div>
              <span className="font-mono text-sm font-semibold">spec-monitor</span>
            </div>
          </div>

          <h2 className="text-xl font-semibold tracking-tight">Entrar no painel</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Sem cadastro público — o acesso é por convite.
          </p>

          <form onSubmit={onSubmit} className="mt-8 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                E-mail
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-md border border-border bg-input px-3 py-2 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/30"
                placeholder="voce@empresa.com"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Senha
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-md border border-border bg-input px-3 py-2 font-mono text-sm text-foreground outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/30"
              />
            </div>
            {errorMsg && (
              <p className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                {errorMsg}
              </p>
            )}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {loading ? "Entrando…" : "Entrar"}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-muted-foreground">
            Problemas para acessar?{" "}
            <Link to="/" className="text-primary hover:underline">
              Fale com o admin
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
