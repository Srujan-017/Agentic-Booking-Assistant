import type { BookingOut, SlotOut } from "../api/types";

interface Props {
  slots: SlotOut[];
  booking: BookingOut | null;
  open: boolean;
  onClose: () => void;
}

function ProgressRow({ label, done }: { label: string; done: boolean }) {
  return (
    <li className="flex items-center gap-2 text-sm">
      <span
        className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] ${
          done ? "bg-emerald-500 text-white" : "bg-slate-200 text-slate-400"
        }`}
        aria-hidden
      >
        {done ? "✓" : ""}
      </span>
      <span className={done ? "text-slate-700" : "text-slate-400"}>{label}</span>
    </li>
  );
}

function PanelContent({ slots, booking }: { slots: SlotOut[]; booking: BookingOut | null }) {
  const isBooking = booking && booking.status !== "idle";

  return (
    <div className="flex h-full flex-col gap-6 overflow-y-auto p-4">
      {isBooking && (
        <section>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Current booking
          </h2>
          <ul className="space-y-1.5 rounded-xl bg-slate-50 p-3 ring-1 ring-slate-200">
            <ProgressRow label="Full name" done={!!booking?.name} />
            <ProgressRow label="Email" done={!!booking?.email} />
            <ProgressRow label="Slot chosen" done={!!booking?.slot_id} />
            <ProgressRow label="Confirmed" done={booking?.status === "confirmed"} />
          </ul>
        </section>
      )}

      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
          Available slots
        </h2>
        {slots.length === 0 ? (
          <p className="text-sm text-slate-400">No slots available right now.</p>
        ) : (
          <ul className="space-y-1.5">
            {slots.map((slot) => (
              <li
                key={slot.id}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700"
              >
                {slot.label}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export function SlotsPanel({ slots, booking, open, onClose }: Props) {
  return (
    <>
      {/* Desktop: persistent sidebar */}
      <aside className="hidden lg:block lg:w-72 lg:shrink-0 lg:border-l lg:border-slate-200 lg:bg-white">
        <PanelContent slots={slots} booking={booking} />
      </aside>

      {/* Mobile: slide-over drawer */}
      {open && (
        <div className="fixed inset-0 z-20 lg:hidden">
          <button
            type="button"
            aria-label="Close slots panel"
            onClick={onClose}
            className="absolute inset-0 bg-black/30"
          />
          <div className="absolute right-0 top-0 h-full w-80 max-w-[85vw] bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-200 p-4">
              <span className="text-sm font-semibold text-slate-700">Booking info</span>
              <button
                type="button"
                onClick={onClose}
                className="text-slate-400 hover:text-slate-600"
                aria-label="Close"
              >
                ✕
              </button>
            </div>
            <div className="h-[calc(100%-57px)]">
              <PanelContent slots={slots} booking={booking} />
            </div>
          </div>
        </div>
      )}
    </>
  );
}
