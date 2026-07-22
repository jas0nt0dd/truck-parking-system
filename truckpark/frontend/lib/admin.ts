import { api } from "./api";

// --- Dashboard ---
export interface DashboardSummary {
  trucks_inside: number;
  entries_today: number;
  exits_today: number;
  revenue_today: string;
  pending_payments: number;
}

export interface LiveSessionItem {
  session_id: string;
  truck_number: string;
  driver_mobile: string;
  entry_time: string;
  duration_hours: number;
  payment_status?: string | null;
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const { data } = await api.get("/dashboard/summary");
  return data;
}

export async function fetchLiveSessions(): Promise<LiveSessionItem[]> {
  const { data } = await api.get("/dashboard/live");
  return data;
}

// --- Billing rules ---
export interface BillingRule {
  id: string;
  rule_name: string;
  from_hours: string;
  to_hours?: string | null;
  charge: string;
  priority: number;
  is_active: boolean;
}

export type BillingRuleInput = Omit<BillingRule, "id">;

export async function fetchBillingRules(): Promise<BillingRule[]> {
  const { data } = await api.get("/billing/rules");
  return data;
}

export async function createBillingRule(payload: BillingRuleInput): Promise<BillingRule> {
  const { data } = await api.post("/billing/rules", payload);
  return data;
}

export async function updateBillingRule(id: string, payload: Partial<BillingRuleInput>): Promise<BillingRule> {
  const { data } = await api.put(`/billing/rules/${id}`, payload);
  return data;
}

export async function deleteBillingRule(id: string): Promise<void> {
  await api.delete(`/billing/rules/${id}`);
}

// --- Users ---
export interface ManagedUser {
  id: string;
  tenant_id?: string | null;
  name: string;
  mobile: string;
  email?: string | null;
  role: "admin" | "gatekeeper";
  is_active: boolean;
  is_root: boolean;
  created_at: string;
}

export interface UserCreateInput {
  name: string;
  mobile: string;
  email?: string;
  role: "admin" | "gatekeeper";
  password: string;
}

export async function fetchUsers(): Promise<ManagedUser[]> {
  const { data } = await api.get("/users");
  return data;
}

export async function createUser(payload: UserCreateInput): Promise<ManagedUser> {
  const cleaned = {
    ...payload,
    name: payload.name.trim(),
    mobile: payload.mobile.trim(),
    password: payload.password.trim(),
    email: payload.email?.trim() || undefined,
  };
  const { data } = await api.post("/users", cleaned);
  return data;
}

export async function setUserStatus(id: string, isActive: boolean): Promise<ManagedUser> {
  const { data } = await api.patch(`/users/${id}/status`, { is_active: isActive });
  return data;
}

export async function resetUserPassword(id: string, newPassword: string): Promise<{ message: string }> {
  const { data } = await api.post(`/users/${id}/reset-password`, { new_password: newPassword });
  return data;
}

// --- Platform subscriptions ---
export interface SubscriptionRequest {
  id: string;
  parking_name: string;
  owner_name: string;
  owner_mobile: string;
  owner_email?: string | null;
  parking_location?: string | null;
  expected_trucks_per_day?: number | null;
  message?: string | null;
  status: "pending" | "approved" | "rejected";
  admin_notes?: string | null;
  requested_at: string;
  reviewed_at?: string | null;
  tenant_id?: string | null;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  owner_name: string;
  owner_mobile: string;
  owner_email?: string | null;
  parking_location?: string | null;
  status: "pending" | "active" | "suspended" | "cancelled";
  subscription_status: "trial" | "active" | "past_due" | "cancelled";
  plan_name: string;
  database_name?: string | null;
  subscription_started_at?: string | null;
  subscription_expires_at?: string | null;
  created_at: string;
}

export async function fetchSubscriptionRequests(status?: string): Promise<SubscriptionRequest[]> {
  const { data } = await api.get("/platform/subscription-requests", { params: { status } });
  return data;
}

export async function fetchTenants(): Promise<Tenant[]> {
  const { data } = await api.get("/platform/tenants");
  return data;
}

export async function approveSubscriptionRequest(
  id: string,
  payload: { admin_notes?: string; plan_name?: string; subscription_expires_at?: string }
): Promise<{ request: SubscriptionRequest; tenant: Tenant; owner_mobile: string; temporary_password: string }> {
  const { data } = await api.post(`/platform/subscription-requests/${id}/approve`, payload);
  return data;
}

export async function rejectSubscriptionRequest(
  id: string,
  payload: { admin_notes?: string }
): Promise<SubscriptionRequest> {
  const { data } = await api.post(`/platform/subscription-requests/${id}/reject`, payload);
  return data;
}

export async function deleteUser(id: string): Promise<void> {
  await api.delete(`/users/${id}`);
}

// --- Reports ---
export async function downloadReport(params: {
  from_date: string;
  to_date: string;
  truck_number?: string;
  driver_mobile?: string;
  format: "excel" | "pdf";
}) {
  const response = await api.get("/reports/export", { params, responseType: "blob" });
  const blob = new Blob([response.data]);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  const ext = params.format === "excel" ? "xlsx" : "pdf";
  a.href = url;
  a.download = `truckpark_report_${params.from_date}_${params.to_date}.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
