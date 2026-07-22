import { api } from "./api";

export interface SubscriptionRequestInput {
  parking_name: string;
  owner_name: string;
  owner_mobile: string;
  owner_email?: string;
  parking_location?: string;
  expected_trucks_per_day?: number;
  message?: string;
}

export async function createSubscriptionRequest(payload: SubscriptionRequestInput) {
  const { data } = await api.post("/subscription-requests", payload);
  return data;
}
