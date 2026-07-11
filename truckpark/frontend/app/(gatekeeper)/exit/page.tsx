"use client";

import { useState } from "react";
import { SessionSearchItem } from "@/lib/sessions";
import { TruckExitSearch } from "@/components/TruckExitSearch";
import { TruckExitDetails } from "@/components/TruckExitDetails";

export default function ExitPage() {
  const [selected, setSelected] = useState<SessionSearchItem | null>(null);

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-4 text-lg font-bold text-yard-900">Truck Exit</h1>
      {selected ? (
        <TruckExitDetails
          sessionItem={selected}
          onBack={() => setSelected(null)}
          onComplete={() => setSelected(null)}
        />
      ) : (
        <TruckExitSearch onSelect={setSelected} />
      )}
    </div>
  );
}
