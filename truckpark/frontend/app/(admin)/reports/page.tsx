"use client";

import { useState } from "react";
import { Download, FileSpreadsheet, FileText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Input";
import { downloadReport } from "@/lib/admin";
import { apiErrorMessage } from "@/lib/api";

export default function ReportsPage() {
  const today = new Date().toISOString().split("T")[0];
  const firstOfMonth = today.slice(0, 7) + "-01";

  const [fromDate,     setFromDate]     = useState(firstOfMonth);
  const [toDate,       setToDate]       = useState(today);
  const [truckNumber,  setTruckNumber]  = useState("");
  const [driverMobile, setDriverMobile] = useState("");
  const [format,       setFormat]       = useState<"excel" | "pdf">("excel");
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState<string | null>(null);

  async function handleExport() {
    setLoading(true);
    setError(null);
    try {
      await downloadReport({
        from_date:     fromDate,
        to_date:       toDate,
        truck_number:  truckNumber  || undefined,
        driver_mobile: driverMobile || undefined,
        format,
      });
    } catch (err) {
      setError(apiErrorMessage(err, "Export failed. Try again."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="mb-1 text-2xl font-bold text-yard-900">Reports</h1>
      <p className="mb-6 text-sm text-yard-500">Export session history to Excel or PDF for any date range.</p>

      <div className="card space-y-4 p-6">
        <div className="grid grid-cols-2 gap-3">
          <Field label="From Date" required>
            <Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
          </Field>
          <Field label="To Date" required>
            <Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
          </Field>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Truck Number (optional)">
            <Input placeholder="Filter by truck" value={truckNumber} onChange={(e) => setTruckNumber(e.target.value.toUpperCase())} className="plate" />
          </Field>
          <Field label="Driver Mobile (optional)">
            <Input placeholder="Filter by mobile" type="tel" inputMode="numeric" value={driverMobile} onChange={(e) => setDriverMobile(e.target.value)} />
          </Field>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-yard-700">Export Format</p>
          <div className="flex gap-3">
            {[
              { value: "excel" as const, label: "Excel (.xlsx)", icon: FileSpreadsheet },
              { value: "pdf"   as const, label: "PDF",           icon: FileText },
            ].map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                onClick={() => setFormat(value)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg border-2 py-3 text-sm font-medium transition ${
                  format === value
                    ? "border-signal bg-signal/10 text-signal-dark"
                    : "border-yard-100 text-yard-700"
                }`}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="rounded bg-warn-light px-3 py-2 text-sm text-warn">{error}</p>}

        <Button onClick={handleExport} loading={loading} size="lg" className="w-full">
          <Download size={18} />
          Export Report
        </Button>
      </div>

      <div className="mt-6 rounded bg-yard-100 px-4 py-3 text-sm text-yard-600">
        <strong>Tip:</strong> Leave truck number and driver mobile blank to export all sessions for the selected date range.
      </div>
    </div>
  );
}
