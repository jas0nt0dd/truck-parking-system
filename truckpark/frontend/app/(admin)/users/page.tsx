"use client";

import { useEffect, useState } from "react";
import { Plus, ToggleLeft, ToggleRight, KeyRound, Copy } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Input";
import {
  fetchUsers,
  createUser,
  setUserStatus,
  resetUserPassword,
  ManagedUser,
} from "@/lib/admin";
import { formatDateTime } from "@/lib/utils";
import { apiErrorMessage } from "@/lib/api";
import { useAuth } from "@/lib/AuthContext";

const EMPTY_FORM = { name: "", mobile: "", email: "", role: "gatekeeper" as const, password: "" };

export default function UsersPage() {
  const { user: currentUser } = useAuth();
  const [users,    setUsers]    = useState<ManagedUser[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form,     setForm]     = useState(EMPTY_FORM);
  const [saving,   setSaving]   = useState(false);
  const [tempPwd,  setTempPwd]  = useState<{ name: string; pwd: string } | null>(null);

  async function load() {
    setLoading(true);
    try { setUsers(await fetchUsers()); }
    catch (err) { setError(apiErrorMessage(err)); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, []);

  function set<K extends keyof typeof EMPTY_FORM>(k: K, v: typeof EMPTY_FORM[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleCreate() {
    setSaving(true);
    setError(null);
    try {
      await createUser(form as any);
      setShowForm(false);
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(u: ManagedUser) {
    try {
      const updated = await setUserStatus(u.id, !u.is_active);
      setUsers((list) => list.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  async function handleResetPwd(u: ManagedUser) {
    if (!confirm(`Reset password for ${u.name}?`)) return;
    try {
      const res = await resetUserPassword(u.id);
      setTempPwd({ name: u.name, pwd: res.temporary_password ?? "" });
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-yard-900">Users</h1>
        <Button onClick={() => setShowForm(true)} size="sm"><Plus size={16} /> Add User</Button>
      </div>

      {error && <p className="mb-4 rounded bg-warn-light px-4 py-3 text-sm text-warn">{error}</p>}

      {/* Temporary password modal */}
      {tempPwd && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="card w-full max-w-sm p-6 text-center">
            <h2 className="mb-2 text-base font-semibold">Temporary Password for {tempPwd.name}</h2>
            <p className="mb-4 rounded bg-yard-50 p-3 font-mono text-xl font-bold text-yard-900">{tempPwd.pwd}</p>
            <p className="mb-5 text-sm text-yard-500">Share this securely. The user should change it on first login.</p>
            <div className="flex gap-2">
              <Button size="sm" variant="secondary" className="flex-1" onClick={() => navigator.clipboard.writeText(tempPwd.pwd)}>
                <Copy size={14} /> Copy
              </Button>
              <Button size="sm" className="flex-1" onClick={() => setTempPwd(null)}>Done</Button>
            </div>
          </div>
        </div>
      )}

      {/* Create user form */}
      {showForm && (
        <div className="card mb-6 p-5">
          <h2 className="mb-4 text-base font-semibold">New User</h2>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Name" required><Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="Full name" /></Field>
            <Field label="Mobile" required><Input value={form.mobile} onChange={(e) => set("mobile", e.target.value)} type="tel" inputMode="numeric" placeholder="10-digit" /></Field>
            <Field label="Email"><Input value={form.email} onChange={(e) => set("email", e.target.value)} type="email" placeholder="Optional" /></Field>
            <Field label="Role" required>
              <select value={form.role} onChange={(e) => set("role", e.target.value as any)} className="input">
                <option value="gatekeeper">Gatekeeper</option>
                <option value="admin">Admin</option>
              </select>
            </Field>
            <Field label="Password" required>
              <Input value={form.password} onChange={(e) => set("password", e.target.value)} type="password" placeholder="Min 6 characters" />
            </Field>
          </div>
          <div className="mt-4 flex gap-2">
            <Button size="sm" onClick={handleCreate} loading={saving}>Create User</Button>
            <Button size="sm" variant="secondary" onClick={() => setShowForm(false)}>Cancel</Button>
          </div>
        </div>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-yard-100 text-xs font-semibold uppercase tracking-wide text-yard-500">
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Mobile</th>
              <th className="px-4 py-3 text-left">Role</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Created</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 4 }).map((_, i) => (
                <tr key={i} className="border-b border-yard-50">
                  {Array.from({ length: 6 }).map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 w-20 animate-pulse rounded bg-yard-100" /></td>
                  ))}
                </tr>
              ))
            ) : users.length === 0 ? (
              <tr><td colSpan={6} className="py-10 text-center text-yard-500">No users yet.</td></tr>
            ) : (
              users.map((u) => (
                <tr key={u.id} className="border-b border-yard-50 hover:bg-yard-50">
                  <td className="px-4 py-3 font-medium text-yard-900">
                    {u.name} {u.is_root && <span className="ml-1 text-xs text-signal">(Root)</span>}
                  </td>
                  <td className="px-4 py-3 text-yard-700">{u.mobile}</td>
                  <td className="px-4 py-3 capitalize text-yard-700">{u.role}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${u.is_active ? "bg-ok-light text-ok" : "bg-yard-100 text-yard-500"}`}>
                      {u.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-yard-500">{formatDateTime(u.created_at)}</td>
                  <td className="px-4 py-3">
                    {!u.is_root && u.id !== currentUser?.id && (
                      <div className="flex gap-2">
                        <button onClick={() => toggleStatus(u)} title={u.is_active ? "Disable" : "Enable"} className="rounded p-1.5 text-yard-500 hover:bg-yard-100">
                          {u.is_active ? <ToggleRight size={16} className="text-ok" /> : <ToggleLeft size={16} />}
                        </button>
                        <button onClick={() => handleResetPwd(u)} title="Reset password" className="rounded p-1.5 text-yard-500 hover:bg-yard-100">
                          <KeyRound size={15} />
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
