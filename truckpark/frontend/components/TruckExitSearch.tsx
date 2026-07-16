"use client";

import { useRef, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { searchSessions, SessionSearchItem } from "@/lib/sessions";
import { formatDateTime, formatDuration } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";

export function TruckExitSearch({ onSelect }: { onSelect: (session: SessionSearchItem) => void }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SessionSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  function handleChange(value: string) {
    setQuery(value);
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }
    debounceTimer.current = setTimeout(() => runSearch(value), 350);
  }

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

      <div className="mt-3 space-y-2">
        {results.map((item) => (
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
        ))}
        {!searching && query.trim().length >= 2 && results.length === 0 && (
          <p className="py-6 text-center text-sm text-yard-500">No active trucks match "{query}"</p>
        )}
      </div>
    </div>
  );
}
