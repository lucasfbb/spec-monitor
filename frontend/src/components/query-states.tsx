// Estados padrão de carregamento/erro para telas movidas a useQuery.

export function LoadingState({ label = "Carregando…" }: { label?: string }) {
  return (
    <div className="py-20 text-center">
      <div className="mx-auto h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      <p className="mt-3 font-mono text-xs text-muted-foreground">{label}</p>
    </div>
  );
}

export function ErrorState({ message }: { message?: string }) {
  return (
    <div className="py-20 text-center">
      <p className="font-mono text-xs uppercase tracking-widest text-destructive">Erro</p>
      <p className="mt-2 text-sm text-muted-foreground">
        {message ?? "Não foi possível carregar os dados."}
      </p>
    </div>
  );
}
