import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { getMe, logout as apiLogout } from "@/lib/api";
import { cn } from "@/lib/utils";

function LogoMark() {
  return (
    <div className="flex items-center gap-2">
      <div className="grid h-7 w-7 place-items-center rounded-md border border-primary/40 bg-primary/10 text-primary">
        <svg
          viewBox="0 0 20 20"
          className="h-3.5 w-3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d="M4 6h12M4 10h8M4 14h12" strokeLinecap="round" />
        </svg>
      </div>
      <div className="leading-tight">
        <div className="font-mono text-sm font-semibold tracking-tight">spec-monitor</div>
        <div className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          v0.1
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: me } = useQuery({ queryKey: ["me"], queryFn: getMe, retry: false });
  const logout = useMutation({
    mutationFn: apiLogout,
    onSuccess: () => {
      queryClient.clear();
      navigate({ to: "/login" });
    },
  });
  const initial = (me?.email ?? "?").charAt(0).toUpperCase();

  const nav: Array<{ to: string; label: string; match: (p: string) => boolean }> = [
    { to: "/", label: "Projetos", match: (p) => p === "/" || p.startsWith("/projects") },
    // Gestão de usuários é só para admin.
    ...(me?.role === "admin"
      ? [{ to: "/users", label: "Usuários", match: (p: string) => p.startsWith("/users") }]
      : []),
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-40 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-6 px-4 sm:px-6">
          <Link to="/" className="shrink-0">
            <LogoMark />
          </Link>
          <nav className="flex items-center gap-1">
            {nav.map((n) => {
              const active = n.match(pathname);
              return (
                <Link
                  key={n.to}
                  to={n.to}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-sm transition-colors",
                    active
                      ? "bg-accent text-foreground"
                      : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                  )}
                >
                  {n.label}
                </Link>
              );
            })}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            {me && (
              <span className="hidden font-mono text-xs text-muted-foreground sm:inline">
                {me.email}
              </span>
            )}
            <div className="grid h-7 w-7 place-items-center rounded-full bg-primary/20 font-mono text-xs font-semibold text-primary">
              {initial}
            </div>
            <button
              type="button"
              onClick={() => logout.mutate()}
              className="rounded-md px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
            >
              Sair
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-4 py-8 sm:px-6">{children}</main>
    </div>
  );
}
