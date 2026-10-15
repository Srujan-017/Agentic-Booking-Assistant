import type { BookingOut } from "../api/types";

export function BookingCard({ booking }: { booking: BookingOut }) {
  if (booking.status !== "confirmed") return null;

  return (
    <div className="mt-2 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm">
      <div className="flex items-center gap-2 font-semibold text-emerald-700">
        <span
          className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white text-xs"
          aria-hidden
        >
          ✓
        </span>
        Booking confirmed
      </div>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-emerald-900">
        <dt className="text-emerald-600">Service</dt>
        <dd>{booking.service_type}</dd>
        <dt className="text-emerald-600">When</dt>
        <dd>{booking.slot_label} IST</dd>
        <dt className="text-emerald-600">Reference</dt>
        <dd className="font-mono">#{booking.reference_id}</dd>
      </dl>
    </div>
  );
}
