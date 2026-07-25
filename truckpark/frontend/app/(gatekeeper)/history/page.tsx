"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { downloadBillPdf, fetchHistory, markPaid, sendBillLink } from "@/lib/sessions";
import { formatCurrency, formatDateTime, formatDuration } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";

interface SessionRow {
  id: string;
  truck_number: string;
  driver_mobile: string;
  entry_time: string;
  exit_time?: string | null;
  status: "inside" | "exited";
  payment_status?: string | null;
  payment_mode?: "cash" | "upi" | null;
  payment_amount?: string | null;
  duration_hours?: number | null;
}

export default function GatekeeperHistoryPage() {
  const [rows, setRows] = useState<SessionRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [truckNumber, setTruckNumber] = useState("");
  const [driverMobile, setDriverMobile] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeActionId, setActiveActionId] = useState<string | null>(null);

  const PAGE_SIZE = 20;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchHistory({
        truck_number: truckNumber || undefined,
        driver_mobile: driverMobile || undefined,
        page,
        page_size: PAGE_SIZE,
      });
      setRows(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load history"));
    } finally {
      setLoading(false);
    }
  }

  async function handleSendBillLink(sessionId: string) {
    setActionLoading(true);
    setActiveActionId(sessionId);
    setError(null);
    try {
      await sendBillLink(sessionId);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not send bill link"));
    } finally {
      setActionLoading(false);
      setActiveActionId(null);
    }
  }

  async function handleDownloadBill(sessionId: string, truckNumber: string) {
    setActionLoading(true);
    setActiveActionId(sessionId);
    setError(null);
    try {
      const blob = await downloadBillPdf(sessionId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `truckpark_bill_${truckNumber}_${sessionId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not download bill"));
    } finally {
      setActionLoading(false);
      setActiveActionId(null);
    }
  }

  async function handleMarkPaid(sessionId: string) {
    setActionLoading(true);
    setActiveActionId(sessionId);
    setError(null);
    try {
      await markPaid(sessionId, "cash");
      await load();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not mark payment as paid"));
    } finally {
      setActionLoading(false);
      setActiveActionId(null);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, truckNumber, driverMobile]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-3 text-lg font-bold text-yard-900">Session History</h1>

      <div className="mb-4 grid grid-cols-2 gap-2">
        <Input
          placeholder="Truck number"
          value={truckNumber}
          onChange={(e) => { setTruckNumber(e.target.value.toUpperCase()); setPage(1); }}
          className="plate"
        />
        <Input
          placeholder="Driver mobile"
          value={driverMobile}
          onChange={(e) => { setDriverMobile(e.target.value); setPage(1); }}
          type="tel"
          inputMode="numeric"
        />
      </div>

      {error && <p className="mb-3 rounded bg-warn-light px-3 py-2 text-sm text-warn">{error}</p>}

      {loading ? (
        <div className="py-10 text-center text-sm text-yard-500">Loading…</div>
      ) : rows.length === 0 ? (
        <p className="py-10 text-center text-sm text-yard-500">No sessions found.</p>
      ) : (
        <div className="space-y-2">
          {rows.map((row) => (
            <div
              key={row.id}
              className={row.payment_status === "pending" ? "card p-3.5 border border-warn-200 bg-warn/5" : "card p-3.5"}
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="plate font-bold text-yard-900">{row.truck_number}</p>
                  <p className="text-xs text-yard-500">{row.driver_mobile}</p>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Badge status={row.status}>{row.status}</Badge>
                  {row.payment_status && (
                    <Badge status={row.payment_status}>{row.payment_status}</Badge>
                  )}
                </div>
              </div>

              {(row.payment_amount || row.payment_status) && (
                <div className="mt-3 rounded-2xl border border-yard-100 bg-white p-3 shadow-sm">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-yard-400">
                        Bill Summary
                      </p>
                      {row.payment_amount ? (
                        <p className="mt-2 text-2xl font-bold text-yard-900">
                          {formatCurrency(row.payment_amount)}
                        </p>
                      ) : (
                        <p className="mt-2 text-lg font-semibold text-yard-700">Amount not yet finalized</p>
                      )}
                    </div>
                    <div className="text-right">
                      {row.payment_mode ? (
                        <p className="text-xs uppercase tracking-[0.24em] text-yard-400">
                          {row.payment_mode}
                        </p>
                      ) : null}
                      {row.payment_status ? (
                        <p
                          className={`mt-2 text-sm font-semibold ${
                            row.payment_status === "pending" ? "text-warn" : "text-ok"
                          }`}
                        >
                          {row.payment_status === "pending" ? "Pending Payment" : "Paid"}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              )}

              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-yard-500">
                <div>
                  <span className="text-yard-400">In: </span>
                  {formatDateTime(row.entry_time)}
                </div>
                <div>
                  <span className="text-yard-400">Out: </span>
                  {row.exit_time ? formatDateTime(row.exit_time) : "—"}
                </div>
                <div>
                  <span className="text-yard-400">Duration: </span>
                  {formatDuration(row.duration_hours)}
                </div>
                {row.payment_amount && (
                  <div>
                    <span className="text-yard-400">Bill: </span>
                    <span className="text-yard-700">{formatCurrency(row.payment_amount)}</span>
                  </div>
                )}
                {row.payment_mode && (
                  <div>
                    <span className="text-yard-400">Mode: </span>
                    <span className="text-yard-700">{row.payment_mode.toUpperCase()}</span>
                  </div>
                )}
              </div>
              {row.status === "exited" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {row.payment_status === "pending" && (
                    <button
                      type="button"
                      onClick={() => handleMarkPaid(row.id)}
                      disabled={actionLoading && activeActionId === row.id}
                      className="rounded-lg border border-yard-200 bg-ok-light px-3 py-2 text-xs font-semibold text-ok transition hover:bg-ok/10 disabled:opacity-50"
                    >
                      {actionLoading && activeActionId === row.id ? "Marking…" : "Mark Paid"}
                    </button>
                  )}
                  {row.payment_status === "pending" && (
                    <button
                      type="button"
                      onClick={() => handleSendBillLink(row.id)}
                      disabled={actionLoading && activeActionId === row.id}
                      className="rounded-lg border border-yard-200 bg-yard-50 px-3 py-2 text-xs font-semibold text-yard-700 transition hover:bg-yard-100 disabled:opacity-50"
                    >
                      {actionLoading && activeActionId === row.id ? "Sending…" : "Send Bill Link"}
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleDownloadBill(row.id, row.truck_number)}
                    disabled={actionLoading && activeActionId === row.id}
                    className="rounded-lg border border-yard-200 bg-transparent px-3 py-2 text-xs font-semibold text-yard-700 transition hover:bg-yard-100 disabled:opacity-50"
                  >
                    {actionLoading && activeActionId === row.id ? "Downloading…" : "Download Bill"}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-yard-500">{total} sessions</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="rounded p-1.5 hover:bg-yard-100 disabled:opacity-30"
            >
              <ChevronLeft size={18} />
            </button>
            <span className="text-yard-700">{page} / {totalPages}</span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="rounded p-1.5 hover:bg-yard-100 disabled:opacity-30"
            >
              <ChevronRight size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
