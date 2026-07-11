import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatInTimeZone } from "date-fns-tz";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const DISPLAY_TZ = "Asia/Kolkata";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return formatInTimeZone(new Date(iso), DISPLAY_TZ, "dd MMM yyyy, hh:mm a");
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return formatInTimeZone(new Date(iso), DISPLAY_TZ, "hh:mm a");
}

export function formatDuration(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return "—";
  const totalMinutes = Math.round(hours * 60);
  const days = Math.floor(totalMinutes / (60 * 24));
  const h = Math.floor((totalMinutes % (60 * 24)) / 60);
  const m = totalMinutes % 60;
  const parts: string[] = [];
  if (days) parts.push(`${days}d`);
  if (h || days) parts.push(`${h}h`);
  parts.push(`${m}m`);
  return parts.join(" ");
}

export function formatCurrency(amount: number | string | null | undefined): string {
  if (amount === null || amount === undefined) return "₹0";
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
}

export function statusBadgeClasses(status: string): string {
  switch (status) {
    case "inside":
      return "bg-signal/15 text-signal-dark";
    case "exited":
      return "bg-ok-light text-ok";
    case "paid":
      return "bg-ok-light text-ok";
    case "pending":
      return "bg-warn-light text-warn";
    case "credit":
      return "bg-yard-100 text-yard-700";
    default:
      return "bg-yard-100 text-yard-700";
  }
}
