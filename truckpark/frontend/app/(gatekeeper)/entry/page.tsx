import React from "react";
import { TruckEntryForm } from "@/components/TruckEntryForm";

export default function EntryPage() {
  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-4 text-lg font-bold text-yard-900">New Truck Entry</h1>
      <TruckEntryForm />
    </div>
  );
}
