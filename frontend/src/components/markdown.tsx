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

// Fallback por palavra (só em linhas de TABELA — decisões costumam usar texto
// puro tipo "Aberta"/"Consolidada"/"Bloqueada"). Não vale para listas: texto
// corrido menciona essas palavras sem que sejam o estado do item.
const WORD_TINTS: Array<{ pattern: RegExp; className: string }> = [
  { pattern: /\b(bloquead[ao]s?|blocked)\b/i, className: "status-row-red" },
  {
    pattern: /\b(consolidad[ao]s?|conclu[íi]d[ao]s?|resolvid[ao]s?|entregues?|done|feit[ao]s?)\b/i,
    className: "status-row-green",
  },
  {
    pattern: /\b(abert[ao]s?|pendentes?|em andamento|em an[áa]lise|parcial|aguardando)\b/i,
    className: "status-row-amber",
  },
];

function rowStatusClass(text: string): string {
  const byEmoji = statusClass(text);
  if (byEmoji) return byEmoji;
  for (const { pattern, className } of WORD_TINTS) {
    if (pattern.test(text)) return className;
  }
  return "";
}

const components: Components = {
  // Linhas de tabela (decisões, status por spec): fundo tingido pelo status —
  // por emoji da convenção ou, na falta dele, por palavra de estado.
  // Cabeçalho não tem marcador, então nunca é tingido.
  tr({ node, children, ...props }) {
    const cls = rowStatusClass(hastText(node));
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
