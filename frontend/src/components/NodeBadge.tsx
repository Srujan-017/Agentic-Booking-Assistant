const NODE_LABELS: Record<string, string> = {
  guardrail: "Guardrail",
  router: "Router",
  rag: "FAQ RAG",
  booking_extract: "Extract",
  booking: "Booking",
  general: "General",
};

function label(node: string): string {
  return NODE_LABELS[node] ?? node;
}

export function NodeBadge({ path, live = false }: { path: string[]; live?: boolean }) {
  if (path.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1 text-[11px] text-slate-400">
      {path.map((node, i) => (
        <span key={`${node}-${i}`} className="flex items-center gap-1">
          {i > 0 && <span aria-hidden>→</span>}
          <span
            className={`rounded-full px-1.5 py-0.5 ${
              live && i === path.length - 1
                ? "bg-indigo-100 text-indigo-600 font-medium"
                : "bg-slate-100 text-slate-500"
            }`}
          >
            {label(node)}
          </span>
        </span>
      ))}
    </div>
  );
}
