import { api } from "./api";

export interface Truck {
  id: string;
  truck_number: string;
  driver_name?: string | null;
  driver_mobile: string;
  transport_company?: string | null;
  vehicle_type?: string | null;
}

export interface Payment {
  id: string;
  amount: string;
  payment_mode?: "cash" | "upi" | "credit" | null;
  payment_status: "paid" | "pending" | "credit";
  paid_at?: string | null;
  billing_breakdown?: { rule_name: string; amount: string; days?: number }[] | null;
}

export interface ParkingSession {
  id: string;
  truck: Truck;
  entry_time: string;
  exit_time?: string | null;
  entry_photo_url?: string | null;
  exit_photo_url?: string | null;
  status: "inside" | "exited";
  remarks?: string | null;
  payment?: Payment | null;
}

export interface EntryPayload {
  truck_number: string;
  driver_mobile: string;
  driver_name?: string;
  transport_company?: string;
  vehicle_type?: string;
  remarks?: string;
  entry_photo_url?: string;
  send_notification?: boolean;
}

export interface SessionSearchItem {
  id: string;
  truck_number: string;
  driver_mobile: string;
  entry_time: string;
  exit_time?: string | null;
  status: "inside" | "exited";
  payment_status?: "paid" | "pending" | "credit" | null;
  duration_hours?: number | null;
}

export interface ExitResponse {
  session: ParkingSession;
  amount_due: string;
  duration_hours: number;
  billing_breakdown: { rule_name: string; amount: string; days?: number }[];
}

export async function createEntry(payload: EntryPayload): Promise<ParkingSession> {
  const { data } = await api.post("/sessions/entry", payload);
  return data;
}

export async function searchSessions(q: string, statusFilter?: string): Promise<SessionSearchItem[]> {
  const { data } = await api.get("/sessions/search", { params: { q, status: statusFilter } });
  return data;
}

export async function fetchHistory(params: {
  truck_number?: string;
  driver_mobile?: string;
  from_date?: string;
  to_date?: string;
  page?: number;
  page_size?: number;
}) {
  const { data } = await api.get("/sessions/history", { params });
  return data as { items: SessionSearchItem[]; total: number; page: number; page_size: number };
}

export async function exitSession(sessionId: string, exitPhotoUrl?: string): Promise<ExitResponse> {
  const { data } = await api.post(`/sessions/${sessionId}/exit`, { exit_photo_url: exitPhotoUrl });
  return data;
}

export async function markPaid(
  sessionId: string,
  paymentMode: "cash" | "upi" | "credit",
  amount?: string,
  sendNotification = true
): Promise<ParkingSession> {
  const { data } = await api.post(`/payments/${sessionId}/mark-paid`, {
    payment_mode: paymentMode,
    amount,
    send_notification: sendNotification,
  });
  return data;
}

export async function uploadPhoto(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/uploads/photo", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data.url as string;
}
