import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { addMember, listMembers, listUsers, removeMember } from "@/lib/api";

// Card de membros do projeto — só o admin vê e usa. Controla quem enxerga
// este projeto no painel (o backend filtra a listagem por membro).
export function ProjectMembers({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const membersQuery = useQuery({
    queryKey: ["members", projectId],
    queryFn: () => listMembers(projectId),
  });
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: listUsers });
  const [selected, setSelected] = useState("");

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["members", projectId] });
  const add = useMutation({
    mutationFn: (userId: string) => addMember(projectId, userId),
    onSuccess: () => {
      setSelected("");
      invalidate();
    },
  });
  const remove = useMutation({
    mutationFn: (userId: string) => removeMember(projectId, userId),
    onSuccess: invalidate,
  });

  const members = membersQuery.data ?? [];
  const memberIds = new Set(members.map((m) => m.id));
  // Candidatos: usuários que ainda não são membros e não são admin (admin já vê tudo).
  const candidates = (usersQuery.data ?? []).filter(
    (u) => !memberIds.has(u.id) && u.role !== "admin",
  );

  return (
    <div className="rounded-lg border border-border bg-card">
      <header className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Membros
        </div>
        <div className="font-mono text-xs text-muted-foreground">{members.length}</div>
      </header>

      <ul className="divide-y divide-border">
        {members.length === 0 && (
          <li className="px-4 py-3 text-xs text-muted-foreground">
            Só você (admin) vê este projeto. Adicione usuários abaixo para dar acesso.
          </li>
        )}
        {members.map((m) => (
          <li key={m.id} className="flex items-center justify-between gap-2 px-4 py-2.5">
            <span className="truncate font-mono text-[13px] text-foreground">{m.email}</span>
            <button
              type="button"
              onClick={() => remove.mutate(m.id)}
              disabled={remove.isPending}
              className="shrink-0 text-xs text-muted-foreground transition-colors hover:text-destructive disabled:opacity-60"
            >
              remover
            </button>
          </li>
        ))}
      </ul>

      <div className="border-t border-border p-3">
        {candidates.length === 0 ? (
          <p className="text-xs text-muted-foreground">
            Nenhum usuário disponível.{" "}
            <a href="/users" className="text-primary hover:underline">
              Criar usuário
            </a>
          </p>
        ) : (
          <div className="flex gap-2">
            <select
              value={selected}
              onChange={(e) => setSelected(e.target.value)}
              className="min-w-0 flex-1 rounded-md border border-border bg-input px-2 py-1.5 text-sm text-foreground outline-none focus:border-primary"
            >
              <option value="">Adicionar usuário…</option>
              {candidates.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.email}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => selected && add.mutate(selected)}
              disabled={!selected || add.isPending}
              className="shrink-0 rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {add.isPending ? "…" : "Add"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
