"use client";

import { useEffect, useState } from "react";
import { Truck, LogIn, LogOut, Banknote, AlertCircle, RefreshCw, type LucideIcon } from "lucide-react";
import { fetchDashboardSummary, fetchLiveSessions, DashboardSummary, LiveSessionItem } from "@/lib/admin";
import { formatCurrency, formatDuration, formatDateTime } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { apiErrorMessage } from "@/lib/api";

type KpiConfig = {
  key: keyof DashboardSummary;
  label: string;
  icon: LucideIcon;
  color: string;
  currency?: boolean;
};

const KPI_CONFIG: KpiConfig[] = [
  { key: "trucks_inside",    label: "Trucks Inside",      icon: Truck,     color: "text-signal" },
  { key: "entries_today",    label: "Entries Today",      icon: LogIn,     color: "text-yard-600" },
  { key: "exits_today",      label: "Exits Today",        icon: LogOut,    color: "text-ok" },
  { key: "revenue_today",    label: "Revenue Today",      icon: Banknote,  color: "text-ok", currency: true },
  { key: "pending_payments", label: "Pending Payments",   icon: AlertCircle, color: "text-warn" },
] as const;

export default function DashboardPage() {
  const [summary, setSummary]   = useState<DashboardSummary | null>(null);
  const [live,    setLive]      = useState<LiveSessionItem[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error,   setError]     = useState<string | null>(null);

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      const [s, l] = await Promise.all([fetchDashboardSummary(), fetchLiveSessions()]);
      setSummary(s);
      setLive(l);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load dashboard data"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  // Auto-refresh every 60 seconds
  useEffect(() => {
    const id = setInterval(loadAll, 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-yard-900">Dashboard</h1>
          <p className="text-sm text-yard-500">Live yard overview · refreshes every 60s</p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadAll} loading={loading}>
          <RefreshCw size={15} />
          Refresh
        </Button>
      </div>

      {error && (
        <p className="mb-4 rounded bg-warn-light px-4 py-3 text-sm text-warn">{error}</p>
      )}

      {/* KPI cards */}
      <div className="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {KPI_CONFIG.map(({ key, label, icon: Icon, color, currency }) => {
          const val = summary ? (summary as any)[key] : null;
          return (
            <div key={key} className="card flex flex-col gap-2 p-4">
              <div className={`${color}`}>
                <Icon size={22} />
              </div>
              <p className="text-2xl font-bold text-yard-900">
                {loading ? (
                  <span className="inline-block h-6 w-16 animate-pulse rounded bg-yard-100" />
                ) : currency ? (
                  formatCurrency(val)
                ) : (
                  val ?? "—"
                )}
              </p>
              <p className="text-xs text-yard-500">{label}</p>
            </div>
          );
        })}
      </div>

      {/* Live trucks table */}
      <div>
        <h2 className="mb-3 text-base font-semibold text-yard-900">
          Trucks Currently Inside
          {!loading && <span className="ml-2 text-sm font-normal text-yard-500">({live.length})</span>}
        </h2>

        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-yard-100 text-xs font-semibold uppercase tracking-wide text-yard-500">
                <th className="px-4 py-3 text-left">Truck #</th>
                <th className="px-4 py-3 text-left">Driver Mobile</th>
                <th className="px-4 py-3 text-left">Entry Time</th>
                <th className="px-4 py-3 text-left">Duration</th>
                <th className="px-4 py-3 text-left">Payment</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-yard-50">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 w-24 animate-pulse rounded bg-yard-100" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : live.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-yard-500">
                    No trucks inside the yard right now.
                  </td>
                </tr>
              ) : (
                live.map((item) => (
                  <tr key={item.session_id} className="border-b border-yard-50 hover:bg-yard-50">
                    <td className="plate px-4 py-3 font-bold text-yard-900">{item.truck_number}</td>
                    <td className="px-4 py-3 text-yard-700">{item.driver_mobile}</td>
                    <td className="px-4 py-3 text-yard-600">{formatDateTime(item.entry_time)}</td>
                    <td className="px-4 py-3 font-medium text-yard-900">{formatDuration(item.duration_hours)}</td>
                    <td className="px-4 py-3">
                      {item.payment_status ? (
                        <Badge status={item.payment_status}>{item.payment_status}</Badge>
                      ) : (
                        <span className="text-yard-400">—</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
