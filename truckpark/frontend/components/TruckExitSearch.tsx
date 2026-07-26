"use client";

import { useRef, useState, useEffect } from "react";
import { Search, RotateCw } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { searchSessions, SessionSearchItem, fetchSession } from "@/lib/sessions";
import { fetchLiveSessions } from "@/lib/admin";
import { formatDateTime, formatDuration } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";

export function TruckExitSearch({ onSelect }: { onSelect: (session: SessionSearchItem) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SessionSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [liveItems, setLiveItems] = useState<any[]>([]);
  const [loadingLive, setLoadingLive] = useState(true);
  const [filter, setFilter] = useState<"all" | "pending" | "longest" | "recent">("all");

  async function runSearch(value: string) {
    if (value.trim().length < 2) {
      setResults([]);
      return;
    }
    setSearching(true);
    setError(null);
    try {
      const items = await searchSessions(value.trim(), "inside");
      setResults(items);
    } catch (err) {
      setError(apiErrorMessage(err, "Search failed"));
    } finally {
      setSearching(false);
    }
  }

  async function loadLive() {
    setLoadingLive(true);
    setError(null);
    try {
      const items = await fetchLiveSessions();
      setLiveItems(items);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load active trucks"));
    } finally {
      setLoadingLive(false);
    }
  }

  async function handleSelectLive(sessionId: string) {
    setError(null);
    try {
      const detailed = await fetchSession(sessionId);
      // map ParkingSession to SessionSearchItem
      const item: SessionSearchItem = {
        id: detailed.id,
        truck_number: detailed.truck.truck_number,
        driver_mobile: detailed.truck.driver_mobile,
        entry_time: detailed.entry_time,
        exit_time: detailed.exit_time,
        status: detailed.status,
        payment_status: detailed.payment?.payment_status ?? null,
        payment_mode: detailed.payment?.payment_mode ?? null,
        payment_amount: detailed.payment?.amount ?? null,
        duration_hours: detailed.payment ? undefined : undefined,
      };
      onSelect(item);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load session details"));
    }
  }

  function handleChange(value: string) {
    setQuery(value);
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = setTimeout(() => runSearch(value), 350);
  }

  // load live items on mount
  useEffect(() => {
    loadLive();
  }, []);

  return (
    <div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-yard-500" size={18} />
        <Input
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Search by truck number or mobile"
          className="pl-10"
          autoFocus
        />
      </div>

      {error && <p className="mt-2 text-sm text-warn">{error}</p>}
      {searching && <p className="mt-3 text-sm text-yard-500">Searching…</p>}

      {/* Filters + Refresh */}
      <div className="mt-3 mb-2 flex items-center gap-2">
        <label className="text-xs text-yard-500">Show:</label>
        <select value={filter} onChange={(e) => setFilter(e.target.value as any)} className="rounded border px-2 py-1 text-sm">
          <option value="all">All inside</option>
          <option value="pending">Pending payment</option>
          <option value="longest">Longest inside</option>
          <option value="recent">Most recent</option>
        </select>
        <button onClick={loadLive} className="ml-auto rounded p-1.5 hover:bg-yard-100">
          <RotateCw size={16} />
        </button>
      </div>

      <div className="mt-2 space-y-2">
        {/* If user is searching, show search results; else show live list */}
        {query.trim().length >= 2 ? (
          results.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelect(item)}
              className="card flex w-full items-center justify-between p-3.5 text-left transition active:scale-[0.99]"
            >
              <div>
                <p className="plate text-base font-bold text-yard-900">{item.truck_number}</p>
                <p className="text-sm text-yard-500">
                  {item.driver_mobile} · In: {formatDateTime(item.entry_time)}
                </p>
              </div>
              <div className="text-right">
                <Badge status={item.status}>{item.status}</Badge>
                <p className="mt-1 text-xs text-yard-500">{formatDuration(item.duration_hours)}</p>
              </div>
            </button>
          ))
        ) : loadingLive ? (
          <p className="py-6 text-center text-sm text-yard-500">Loading active trucks…</p>
        ) : liveItems.length === 0 ? (
          <p className="py-6 text-center text-sm text-yard-500">No trucks currently inside</p>
        ) : (
          [...liveItems]
            .sort((a, b) => {
              if (filter === "longest") return b.duration_hours - a.duration_hours;
              if (filter === "recent") return new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime();
              return 0;
            })
            .filter((it) => (filter === "pending" ? it.payment_status === "pending" : true))
            .map((it) => (
              <button
                key={it.session_id}
                onClick={() => handleSelectLive(it.session_id)}
                className="card flex w-full items-center justify-between p-3.5 text-left transition active:scale-[0.99]"
              >
                <div>
                  <p className="plate text-base font-bold text-yard-900">{it.truck_number}</p>
                  <p className="text-sm text-yard-500">{it.driver_mobile} · In: {formatDateTime(it.entry_time)}</p>
                </div>
                <div className="text-right">
                  <Badge status="inside">inside</Badge>
                  <p className="mt-1 text-xs text-yard-500">{formatDuration(it.duration_hours)}</p>
                </div>
              </button>
            ))
        )}
      </div>
    </div>
  );
}
