"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { fetchHistory } from "@/lib/sessions";
import { formatDateTime, formatDuration, formatCurrency } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";

export default function AdminSessionsPage() {
  const [rows,        setRows]        = useState<any[]>([]);
  const [total,       setTotal]       = useState(0);
  const [page,        setPage]        = useState(1);
  const [truckNumber, setTruckNumber] = useState("");
  const [driverMobile,setDriverMobile]= useState("");
  const [fromDate,    setFromDate]    = useState("");
  const [toDate,      setToDate]      = useState("");
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);

  const PAGE_SIZE = 20;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchHistory({
        truck_number:  truckNumber  || undefined,
        driver_mobile: driverMobile || undefined,
        from_date:     fromDate     || undefined,
        to_date:       toDate       || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setRows(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load sessions"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [page, truckNumber, driverMobile, fromDate, toDate]); // eslint-disable-line

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-yard-900">Sessions &amp; History</h1>

      {/* Filters */}
      <div className="card mb-6 grid grid-cols-2 gap-3 p-4 sm:grid-cols-4">
        <Input
          placeholder="Truck number"
          value={truckNumber}
          onChange={(e) => { setTruckNumber(e.target.value.toUpperCase()); setPage(1); }}
          className="plate"
        />
        <Input
          placeholder="Driver mobile"
          type="tel"
          inputMode="numeric"
          value={driverMobile}
          onChange={(e) => { setDriverMobile(e.target.value); setPage(1); }}
        />
        <Input
          type="date"
          value={fromDate}
          onChange={(e) => { setFromDate(e.target.value); setPage(1); }}
          placeholder="From date"
        />
        <Input
          type="date"
          value={toDate}
          onChange={(e) => { setToDate(e.target.value); setPage(1); }}
          placeholder="To date"
        />
      </div>

      {error && <p className="mb-4 rounded bg-warn-light px-4 py-3 text-sm text-warn">{error}</p>}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-yard-100 text-xs font-semibold uppercase tracking-wide text-yard-500">
              <th className="px-4 py-3 text-left">Truck #</th>
              <th className="px-4 py-3 text-left">Driver</th>
              <th className="px-4 py-3 text-left">Entry</th>
              <th className="px-4 py-3 text-left">Exit</th>
              <th className="px-4 py-3 text-left">Duration</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Payment</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-yard-50">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 w-20 animate-pulse rounded bg-yard-100" />
                    </td>
                  ))}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-12 text-center text-yard-500">
                  No sessions match the current filters.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id} className="border-b border-yard-50 hover:bg-yard-50">
                  <td className="plate px-4 py-3 font-bold text-yard-900">{row.truck_number}</td>
                  <td className="px-4 py-3 text-yard-700">{row.driver_mobile}</td>
                  <td className="px-4 py-3 text-yard-600">{formatDateTime(row.entry_time)}</td>
                  <td className="px-4 py-3 text-yard-600">{row.exit_time ? formatDateTime(row.exit_time) : "—"}</td>
                  <td className="px-4 py-3">{formatDuration(row.duration_hours)}</td>
                  <td className="px-4 py-3"><Badge status={row.status}>{row.status}</Badge></td>
                  <td className="px-4 py-3">
                    {row.payment_status ? (
                      <Badge status={row.payment_status}>{row.payment_status}</Badge>
                    ) : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between text-sm text-yard-600">
        <span>{total.toLocaleString()} sessions</span>
        <div className="flex items-center gap-2">
          <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
            className="rounded p-1.5 hover:bg-yard-100 disabled:opacity-30"><ChevronLeft size={18} /></button>
          <span>{page} / {totalPages}</span>
          <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="rounded p-1.5 hover:bg-yard-100 disabled:opacity-30"><ChevronRight size={18} /></button>
        </div>
      </div>
    </div>
  );
}
