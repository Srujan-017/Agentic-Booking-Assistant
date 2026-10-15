import type { CitationOut } from "../api/types";

export function CitationChips({ citations }: { citations: CitationOut[] }) {
  if (!citations.length) return null;

  const pages = Array.from(new Set(citations.map((c) => c.page))).sort((a, b) => a - b);

  return (
    <div className="mt-1.5 flex flex-wrap gap-1.5">
      {pages.map((page) => (
        <span
          key={page}
          className="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-600 ring-1 ring-inset ring-indigo-200"
        >
          Employee Handbook, p. {page}
        </span>
      ))}
    </div>
  );
}
