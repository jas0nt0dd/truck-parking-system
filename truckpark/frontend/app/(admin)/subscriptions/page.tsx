"use client";

import { useEffect, useState } from "react";
import { Check, X, RefreshCw } from "lucide-react";
import {
  approveSubscriptionRequest,
  fetchSubscriptionRequests,
  fetchTenants,
  rejectSubscriptionRequest,
  SubscriptionRequest,
  Tenant,
} from "@/lib/admin";
import { apiErrorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Textarea } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";

type ApprovalResult = {
  parking: string;
  mobile: string;
  password: string;
} | null;

export default function SubscriptionsPage() {
  const [requests, setRequests] = useState<SubscriptionRequest[]>([]);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [approval, setApproval] = useState<ApprovalResult>(null);

  async function loadAll() {
    setLoading(true);
    setError(null);
    try {
      const [requestData, tenantData] = await Promise.all([
        fetchSubscriptionRequests(),
        fetchTenants(),
      ]);
      setRequests(requestData);
      setTenants(tenantData);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load subscription data"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, []);

  async function approve(request: SubscriptionRequest) {
    setActionId(request.id);
    setError(null);
    setApproval(null);
    try {
      const result = await approveSubscriptionRequest(request.id, {
        admin_notes: notes[request.id],
        plan_name: "manual",
      });
      setApproval({
        parking: result.tenant.name,
        mobile: result.owner_mobile,
        password: result.temporary_password,
      });
      await loadAll();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not approve subscription request"));
    } finally {
      setActionId(null);
    }
  }

  async function reject(request: SubscriptionRequest) {
    setActionId(request.id);
    setError(null);
    setApproval(null);
    try {
      await rejectSubscriptionRequest(request.id, { admin_notes: notes[request.id] });
      await loadAll();
    } catch (err) {
      setError(apiErrorMessage(err, "Could not reject subscription request"));
    } finally {
      setActionId(null);
    }
  }

  const pending = requests.filter((request) => request.status === "pending");

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-yard-900">Subscriptions</h1>
          <p className="text-sm text-yard-500">Manual approval for new parking-owner accounts.</p>
        </div>
        <Button variant="secondary" size="sm" onClick={loadAll} loading={loading}>
          <RefreshCw size={15} />
          Refresh
        </Button>
      </div>

      {error && <p className="mb-4 rounded bg-warn-light px-4 py-3 text-sm text-warn">{error}</p>}

      {approval && (
        <div className="mb-4 rounded border border-ok/30 bg-ok/10 px-4 py-3 text-sm text-yard-800">
          <p className="font-semibold">Approved {approval.parking}</p>
          <p className="mt-1">
            Owner login: <span className="font-mono">{approval.mobile}</span> /{" "}
            <span className="font-mono">{approval.password}</span>
          </p>
        </div>
      )}

      <div className="mb-8 grid gap-3 md:grid-cols-3">
        <div className="card p-4">
          <p className="text-2xl font-bold text-yard-900">{pending.length}</p>
          <p className="text-xs text-yard-500">Pending Requests</p>
        </div>
        <div className="card p-4">
          <p className="text-2xl font-bold text-yard-900">{tenants.length}</p>
          <p className="text-xs text-yard-500">Tenants Created</p>
        </div>
        <div className="card p-4">
          <p className="text-2xl font-bold text-yard-900">
            {tenants.filter((tenant) => tenant.subscription_status === "active").length}
          </p>
          <p className="text-xs text-yard-500">Active Subscriptions</p>
        </div>
      </div>

      <div className="grid gap-4">
        {loading ? (
          <div className="card p-6 text-sm text-yard-500">Loading subscription requests...</div>
        ) : requests.length === 0 ? (
          <div className="card p-6 text-sm text-yard-500">No subscription requests yet.</div>
        ) : (
          requests.map((request) => (
            <div key={request.id} className="card p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="mb-2 flex items-center gap-2">
                    <h2 className="text-base font-semibold text-yard-900">{request.parking_name}</h2>
                    <Badge status={request.status as any}>{request.status}</Badge>
                  </div>
                  <p className="text-sm text-yard-700">
                    {request.owner_name} / {request.owner_mobile}
                    {request.owner_email ? ` / ${request.owner_email}` : ""}
                  </p>
                  <p className="mt-1 text-sm text-yard-500">
                    {request.parking_location || "No location provided"} /{" "}
                    {request.expected_trucks_per_day ?? "-"} trucks/day
                  </p>
                  <p className="mt-1 text-xs text-yard-400">Requested {formatDateTime(request.requested_at)}</p>
                  {request.message && <p className="mt-3 text-sm text-yard-700">{request.message}</p>}
                  {request.admin_notes && (
                    <p className="mt-3 rounded bg-yard-50 px-3 py-2 text-sm text-yard-600">{request.admin_notes}</p>
                  )}
                </div>

                {request.status === "pending" && (
                  <div className="w-full space-y-2 md:w-80">
                    <Textarea
                      placeholder="Admin notes"
                      value={notes[request.id] || ""}
                      onChange={(event) =>
                        setNotes((current) => ({ ...current, [request.id]: event.target.value }))
                      }
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => approve(request)}
                        loading={actionId === request.id}
                      >
                        <Check size={15} />
                        Approve
                      </Button>
                      <Button
                        type="button"
                        variant="danger"
                        size="sm"
                        onClick={() => reject(request)}
                        loading={actionId === request.id}
                      >
                        <X size={15} />
                        Reject
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
