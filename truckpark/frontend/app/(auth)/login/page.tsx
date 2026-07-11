"use client";

import { FormEvent, useState } from "react";
import { ShieldCheck, Truck, UserRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Input";
import { useAuth } from "@/lib/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [role, setRole] = useState<"admin" | "gatekeeper">("admin");
  const [mobile, setMobile] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(mobile, password);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function useDemoLogin(nextRole: "admin" | "gatekeeper") {
    setRole(nextRole);
    setError(null);
    if (nextRole === "admin") {
      setMobile("7200775876");
      setPassword("0000");
    } else {
      setMobile("8888888888");
      setPassword("0000");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-yard-900 px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-white">
          <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-xl bg-signal text-yard-950">
            <Truck size={28} strokeWidth={2.5} />
          </div>
          <h1 className="text-xl font-bold tracking-tight">TruckPark</h1>
          <p className="text-sm text-yard-100/60">Truck Parking Management System</p>
        </div>

        <form onSubmit={handleSubmit} className="card space-y-4 p-6">
          <div className="grid grid-cols-2 gap-2 rounded bg-yard-50 p-1">
            <button
              type="button"
              onClick={() => useDemoLogin("admin")}
              className={`flex h-12 items-center justify-center gap-2 rounded text-sm font-semibold transition ${
                role === "admin" ? "bg-white text-yard-900 shadow-sm" : "text-yard-600 hover:bg-white/70"
              }`}
            >
              <ShieldCheck size={17} />
              Admin Login
            </button>
            <button
              type="button"
              onClick={() => useDemoLogin("gatekeeper")}
              className={`flex h-12 items-center justify-center gap-2 rounded text-sm font-semibold transition ${
                role === "gatekeeper" ? "bg-white text-yard-900 shadow-sm" : "text-yard-600 hover:bg-white/70"
              }`}
            >
              <UserRound size={17} />
              Gatekeeper Login
            </button>
          </div>

          <div className="rounded border border-yard-100 bg-yard-50 px-3 py-2 text-xs text-yard-600">
            {role === "admin"
              ? "Admin opens dashboard, billing, users, sessions, and reports."
              : "Gatekeeper opens truck entry, exit, and history screens."}
          </div>

          <Field label="Mobile Number" required>
            <Input
              type="tel"
              inputMode="numeric"
              autoFocus
              placeholder="10-digit mobile number"
              value={mobile}
              onChange={(e) => setMobile(e.target.value)}
              required
            />
          </Field>
          <Field label="Password" required>
            <Input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </Field>

          {error && (
            <p className="rounded bg-warn-light px-3 py-2 text-sm text-warn">{error}</p>
          )}

          <Button type="submit" size="lg" className="w-full" loading={loading}>
            Log In as {role === "admin" ? "Admin" : "Gatekeeper"}
          </Button>
        </form>

        <p className="mt-6 text-center text-xs text-yard-100/40">
          Local admin: 7200775876 / 0000. Gatekeeper: 8888888888 / 0000.
        </p>
      </div>
    </div>
  );
}
