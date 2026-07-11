"use client";

import { useEffect, useState } from "react";
import { Plus, Pencil, Trash2, Check, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Field, Input } from "@/components/ui/Input";
import {
  fetchBillingRules,
  createBillingRule,
  updateBillingRule,
  deleteBillingRule,
  BillingRule,
} from "@/lib/admin";
import { apiErrorMessage } from "@/lib/api";

const EMPTY_FORM = { rule_name: "", from_hours: "", to_hours: "", charge: "", priority: "1", is_active: true };

type FormState = typeof EMPTY_FORM;

export default function BillingPage() {
  const [rules,    setRules]    = useState<BillingRule[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing,  setEditing]  = useState<BillingRule | null>(null);
  const [form,     setForm]     = useState<FormState>(EMPTY_FORM);
  const [saving,   setSaving]   = useState(false);

  async function load() {
    setLoading(true);
    try { setRules(await fetchBillingRules()); }
    catch (err) { setError(apiErrorMessage(err)); }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, []);

  function openCreate() {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowForm(true);
  }

  function openEdit(rule: BillingRule) {
    setEditing(rule);
    setForm({
      rule_name:  rule.rule_name,
      from_hours: rule.from_hours,
      to_hours:   rule.to_hours ?? "",
      charge:     rule.charge,
      priority:   String(rule.priority),
      is_active:  rule.is_active,
    });
    setShowForm(true);
  }

  function set(k: keyof FormState, v: string | boolean) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const payload = {
        rule_name:  form.rule_name,
        from_hours: form.from_hours,
        to_hours:   form.to_hours || null,
        charge:     form.charge,
        priority:   Number(form.priority),
        is_active:  form.is_active,
      } as any;

      if (editing) {
        await updateBillingRule(editing.id, payload);
      } else {
        await createBillingRule(payload);
      }
      setShowForm(false);
      await load();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this rule?")) return;
    try {
      await deleteBillingRule(id);
      setRules((r) => r.filter((x) => x.id !== id));
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-yard-900">Billing Rules</h1>
          <p className="text-sm text-yard-500">Configure parking charge brackets. Changes take effect immediately.</p>
        </div>
        <Button onClick={openCreate} size="sm"><Plus size={16} /> Add Rule</Button>
      </div>

      {error && <p className="mb-4 rounded bg-warn-light px-4 py-3 text-sm text-warn">{error}</p>}

      {/* Rule form */}
      {showForm && (
        <div className="card mb-6 p-5">
          <h2 className="mb-4 text-base font-semibold text-yard-900">
            {editing ? "Edit Rule" : "New Rule"}
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="Rule Name" required>
              <Input value={form.rule_name} onChange={(e) => set("rule_name", e.target.value)} placeholder="e.g. First 12 Hours" />
            </Field>
            <Field label="From Hours" required>
              <Input type="number" min="0" step="0.5" value={form.from_hours} onChange={(e) => set("from_hours", e.target.value)} placeholder="0" />
            </Field>
            <Field label="To Hours (blank = open-ended)">
              <Input type="number" min="0" step="0.5" value={form.to_hours} onChange={(e) => set("to_hours", e.target.value)} placeholder="12" />
            </Field>
            <Field label="Charge (₹)" required>
              <Input type="number" min="0" step="1" value={form.charge} onChange={(e) => set("charge", e.target.value)} placeholder="100" />
            </Field>
            <Field label="Priority">
              <Input type="number" min="1" step="1" value={form.priority} onChange={(e) => set("priority", e.target.value)} />
            </Field>
            <Field label="Active">
              <div className="flex items-center gap-2 pt-2">
                <input type="checkbox" checked={form.is_active} onChange={(e) => set("is_active", e.target.checked)} id="is_active" className="h-4 w-4 accent-signal" />
                <label htmlFor="is_active" className="text-sm text-yard-700">Enabled</label>
              </div>
            </Field>
          </div>
          <div className="mt-4 flex gap-2">
            <Button onClick={handleSave} loading={saving} size="sm"><Check size={15} /> Save</Button>
            <Button variant="secondary" size="sm" onClick={() => setShowForm(false)}><X size={15} /> Cancel</Button>
          </div>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-yard-100 text-xs font-semibold uppercase tracking-wide text-yard-500">
              <th className="px-4 py-3 text-left">Rule Name</th>
              <th className="px-4 py-3 text-left">From (hrs)</th>
              <th className="px-4 py-3 text-left">To (hrs)</th>
              <th className="px-4 py-3 text-left">Charge</th>
              <th className="px-4 py-3 text-left">Priority</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={i} className="border-b border-yard-50">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3"><div className="h-4 w-20 animate-pulse rounded bg-yard-100" /></td>
                  ))}
                </tr>
              ))
            ) : rules.length === 0 ? (
              <tr><td colSpan={7} className="py-10 text-center text-yard-500">No billing rules yet. Add one above.</td></tr>
            ) : (
              rules.map((rule) => (
                <tr key={rule.id} className="border-b border-yard-50 hover:bg-yard-50">
                  <td className="px-4 py-3 font-medium text-yard-900">{rule.rule_name}</td>
                  <td className="px-4 py-3 text-yard-700">{rule.from_hours}</td>
                  <td className="px-4 py-3 text-yard-700">{rule.to_hours ?? "Open-ended"}</td>
                  <td className="px-4 py-3 font-semibold text-yard-900">₹{rule.charge}</td>
                  <td className="px-4 py-3 text-yard-700">{rule.priority}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${rule.is_active ? "bg-ok-light text-ok" : "bg-yard-100 text-yard-500"}`}>
                      {rule.is_active ? "Active" : "Disabled"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => openEdit(rule)} className="rounded p-1.5 text-yard-500 hover:bg-yard-100 hover:text-yard-900">
                        <Pencil size={15} />
                      </button>
                      <button onClick={() => handleDelete(rule.id)} className="rounded p-1.5 text-yard-500 hover:bg-warn-light hover:text-warn">
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 rounded bg-yard-100 px-4 py-3 text-sm text-yard-600">
        <strong>Note:</strong> For open-ended rules (no "To Hours"), the charge applies per additional 24-hour day beyond "From Hours".
      </div>
    </div>
  );
}
