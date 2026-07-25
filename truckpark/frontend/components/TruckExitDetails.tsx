"use client";

import { useEffect, useState } from "react";
import { Banknote, Smartphone, Check, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { downloadBillPdf, exitSession, markPaid, sendBillLink, ExitResponse, SessionSearchItem } from "@/lib/sessions";
import { formatCurrency, formatDateTime, formatDuration, cn } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";

const PAYMENT_MODES = [
  { value: "cash" as const, label: "Cash", icon: Banknote },
  { value: "upi" as const, label: "UPI", icon: Smartphone },
];

export function TruckExitDetails({
  sessionItem,
  onBack,
  onComplete,
}: {
  sessionItem: SessionSearchItem;
  onBack: () => void;
  onComplete: () => void;
}) {
  const [exitData, setExitData] = useState<ExitResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [paymentMode, setPaymentMode] = useState<"cash" | "upi" | null>("cash");
  const [submitting, setSubmitting] = useState(false);
  const [sendingLink, setSendingLink] = useState(false);
  const [downloadingBill, setDownloadingBill] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await exitSession(sessionItem.id);
        if (!cancelled) setExitData(data);
      } catch (err) {
        if (!cancelled) setError(apiErrorMessage(err, "Could not calculate charges"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionItem.id]);

  async function handleMarkPaid() {
    if (!paymentMode) return;
    setSubmitting(true);
    setError(null);
    try {
      await markPaid(sessionItem.id, paymentMode);
      setDone(true);
      setTimeout(onComplete, 2000);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not mark as paid"));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSendBillLink() {
    setSendingLink(true);
    setError(null);
    try {
      await sendBillLink(sessionItem.id);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not send bill link"));
    } finally {
      setSendingLink(false);
    }
  }

  async function handleDownloadBill() {
    setDownloadingBill(true);
    setError(null);
    try {
      const blob = await downloadBillPdf(sessionItem.id);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `truckpark_bill_${sessionItem.truck_number}_${sessionItem.id}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not download bill"));
    } finally {
      setDownloadingBill(false);
    }
  }

  if (done) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center rounded-lg bg-ok-light text-ok">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-ok text-white">
          <Check size={40} strokeWidth={3} />
        </div>
        <p className="mt-4 text-xl font-bold">Exit Complete</p>
        <p className="text-sm text-ok/80">{sessionItem.truck_number} has left the yard</p>
      </div>
    );
  }

  return (
    <div>
      <button onClick={onBack} className="mb-4 flex items-center gap-1 text-sm font-medium text-yard-700">
        <ArrowLeft size={16} /> Back to search
      </button>

      <div className="card p-4">
        <p className="plate text-2xl font-bold text-yard-900">{sessionItem.truck_number}</p>
        <p className="text-sm text-yard-500">{sessionItem.driver_mobile}</p>

        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div>
            <p className="text-yard-500">Entry Time</p>
            <p className="font-medium text-yard-900">{formatDateTime(sessionItem.entry_time)}</p>
          </div>
          <div>
            <p className="text-yard-500">Duration</p>
            <p className="font-medium text-yard-900">
              {exitData ? formatDuration(exitData.duration_hours) : "Calculating…"}
            </p>
          </div>
        </div>

        {loading && <p className="mt-4 text-sm text-yard-500">Calculating parking charges…</p>}
        {error && <p className="mt-4 rounded bg-warn-light px-3 py-2 text-sm text-warn">{error}</p>}

        {exitData && (
          <>
            <div className="mt-4 rounded bg-yard-50 p-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-yard-500">Amount Due</p>
              <p className="mt-1 text-3xl font-bold text-yard-900">{formatCurrency(exitData.amount_due)}</p>
              <p className="mt-2 text-xs text-yard-500">
                This session is recorded as pending until payment is collected. You can mark paid now or send a bill link.
              </p>
              <ul className="mt-3 space-y-0.5 text-xs text-yard-500">
                {exitData.billing_breakdown.map((b, i) => (
                  <li key={i}>
                    {b.rule_name}: {formatCurrency(b.amount)}{b.days ? ` (${b.days} day${b.days > 1 ? "s" : ""})` : ""}
                  </li>
                ))}
              </ul>
            </div>

            <p className="mb-2 mt-4 text-sm font-medium text-yard-700">Payment Mode</p>
            <div className="grid grid-cols-2 gap-2">
              {PAYMENT_MODES.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  onClick={() => setPaymentMode(value)}
                  className={cn(
                    "flex flex-col items-center gap-1.5 rounded-lg border-2 py-3 text-sm font-medium transition",
                    paymentMode === value
                      ? "border-signal bg-signal/10 text-signal-dark"
                      : "border-yard-100 text-yard-700"
                  )}
                >
                  <Icon size={20} />
                  {label}
                </button>
              ))}
            </div>

            <div className="mt-5 grid gap-3">
              <Button
                size="lg"
                className="w-full"
                disabled={!paymentMode}
                loading={submitting}
                onClick={handleMarkPaid}
              >
                Mark as Paid &amp; Exit
              </Button>
              <Button
                variant="secondary"
                size="lg"
                className="w-full"
                onClick={handleSendBillLink}
                loading={sendingLink}
              >
                Send Bill Link via WhatsApp
              </Button>
              <Button
                variant="ghost"
                size="lg"
                className="w-full"
                onClick={handleDownloadBill}
                loading={downloadingBill}
              >
                Download Bill PDF
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
