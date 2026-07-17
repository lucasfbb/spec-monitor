import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

// Extrai o texto puro de um nó hast (linha de tabela, item de lista) para
// procurar o marcador de status da convenção de STATUS.md.
function hastText(node: unknown): string {
  if (!node || typeof node !== "object") return "";
  const n = node as { type?: string; value?: string; children?: unknown[] };
  if (n.type === "text") return n.value ?? "";
  if (Array.isArray(n.children)) return n.children.map(hastText).join("");
  return "";
}

// Legenda da convenção (specs/STATUS.md dos projetos): 🟢 feito · 🟡 parcial ·
// 🔴 não iniciado/bloqueado · 🟠 divergência · ⚪ ainda não é hora. Aceita
// também os marcadores equivalentes (✅/☐/🚧…) que os projetos usam na prática.
// Ordem = prioridade: o mais "grave" presente na linha vence, para que uma
// pendência nunca fique escondida atrás de um ✅ no mesmo texto.
const STATUS_TINTS: Array<{ emojis: string[]; className: string }> = [
  { emojis: ["🔴", "❌", "⛔", "🚫"], className: "status-row-red" },
  { emojis: ["🟠"], className: "status-row-orange" },
  { emojis: ["🟡", "🟨", "🚧", "📋", "📨", "⏳"], className: "status-row-amber" },
  { emojis: ["🟢", "🟩", "✅", "✔️", "☑️", "☑"], className: "status-row-green" },
  { emojis: ["⚪", "☐", "⬜"], className: "status-row-neutral" },
];

function statusClass(text: string): string {
  for (const { emojis, className } of STATUS_TINTS) {
    if (emojis.some((e) => text.includes(e))) return className;
  }
  return "";
}

const components: Components = {
  // Linhas de tabela (decisões, status por spec): fundo tingido pelo status.
  // Cabeçalho não tem emoji, então nunca é tingido.
  tr({ node, children, ...props }) {
    const cls = statusClass(hastText(node));
    return (
      <tr className={cls || undefined} {...props}>
        {children}
      </tr>
    );
  },
  // Itens de lista (ex.: próximos passos / decisões em bullets) só recebem cor
  // quando carregam um marcador — listas comuns ficam intactas.
  li({ node, children, ...props }) {
    const cls = statusClass(hastText(node));
    return (
      <li className={cls || undefined} {...props}>
        {children}
      </li>
    );
  },
};

export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div className={cn("prose-spec", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  );
}
