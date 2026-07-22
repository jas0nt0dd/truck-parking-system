"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowLeft, CheckCircle2, Truck } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field, Input, Textarea } from "@/components/ui/Input";
import { apiErrorMessage } from "@/lib/api";
import { createSubscriptionRequest } from "@/lib/subscriptions";

export default function SubscribePage() {
  const [form, setForm] = useState({
    parking_name: "",
    owner_name: "",
    owner_mobile: "",
    owner_email: "",
    parking_location: "",
    expected_trucks_per_day: "",
    message: "",
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await createSubscriptionRequest({
        parking_name: form.parking_name,
        owner_name: form.owner_name,
        owner_mobile: form.owner_mobile,
        owner_email: form.owner_email || undefined,
        parking_location: form.parking_location || undefined,
        expected_trucks_per_day: form.expected_trucks_per_day
          ? Number(form.expected_trucks_per_day)
          : undefined,
        message: form.message || undefined,
      });
      setSubmitted(true);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not submit subscription request"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-yard-900 px-4 py-8 text-yard-900">
      <div className="mx-auto w-full max-w-2xl">
        <Link href="/login" className="mb-6 inline-flex items-center gap-2 text-sm text-yard-100/70 hover:text-white">
          <ArrowLeft size={16} />
          Back to login
        </Link>

        <div className="mb-8 flex flex-col items-center text-white">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-signal text-yard-950">
            <Truck size={28} strokeWidth={2.5} />
          </div>
          <h1 className="text-xl font-bold tracking-tight">Start TruckPark</h1>
          <p className="text-sm text-yard-100/60">Request access for your truck parking business</p>
        </div>

        <div className="card p-6">
          {submitted ? (
            <div className="py-10 text-center">
              <CheckCircle2 className="mx-auto mb-4 text-ok" size={42} />
              <h2 className="text-xl font-bold text-yard-900">Request sent</h2>
              <p className="mx-auto mt-2 max-w-md text-sm text-yard-600">
                Our admin will verify your subscription manually and share your owner login credentials.
              </p>
              <Link href="/login" className="mt-6 inline-flex">
                <Button type="button">Go to Login</Button>
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="grid gap-4">
              <Field label="Truck Parking Name" required>
                <Input value={form.parking_name} onChange={(e) => update("parking_name", e.target.value)} required />
              </Field>
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Owner Name" required>
                  <Input value={form.owner_name} onChange={(e) => update("owner_name", e.target.value)} required />
                </Field>
                <Field label="Owner Mobile" required>
                  <Input
                    type="tel"
                    inputMode="numeric"
                    value={form.owner_mobile}
                    onChange={(e) => update("owner_mobile", e.target.value)}
                    required
                  />
                </Field>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <Field label="Owner Email">
                  <Input type="email" value={form.owner_email} onChange={(e) => update("owner_email", e.target.value)} />
                </Field>
                <Field label="Expected Trucks Per Day">
                  <Input
                    type="number"
                    min={0}
                    value={form.expected_trucks_per_day}
                    onChange={(e) => update("expected_trucks_per_day", e.target.value)}
                  />
                </Field>
              </div>
              <Field label="Parking Location">
                <Input value={form.parking_location} onChange={(e) => update("parking_location", e.target.value)} />
              </Field>
              <Field label="Message">
                <Textarea value={form.message} onChange={(e) => update("message", e.target.value)} />
              </Field>

              {error && <p className="rounded bg-warn-light px-3 py-2 text-sm text-warn">{error}</p>}

              <Button type="submit" size="lg" loading={loading}>
                Send Subscription Request
              </Button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
