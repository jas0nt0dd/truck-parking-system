"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Truck, History as HistoryIcon, ArrowRightLeft } from "lucide-react";
import { useAuth } from "@/lib/AuthContext";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/entry", label: "Entry", icon: Truck },
  { href: "/exit", label: "Exit", icon: ArrowRightLeft },
  { href: "/history", label: "History", icon: HistoryIcon },
];

export function GatekeeperShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="flex min-h-screen flex-col bg-yard-50">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-yard-100 bg-yard-900 px-4 py-3 text-white">
        <div>
          <p className="text-sm font-semibold tracking-wide">TruckPark</p>
          <p className="text-xs text-yard-100/70">{user?.name} · Gatekeeper</p>
        </div>
        <button onClick={logout} aria-label="Log out" className="rounded-full p-2 hover:bg-yard-800">
          <LogOut size={20} />
        </button>
      </header>

      <main className="flex-1 px-4 py-5 pb-24">{children}</main>

      <nav className="fixed bottom-0 left-0 right-0 z-10 flex border-t border-yard-100 bg-white">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex flex-1 flex-col items-center gap-1 py-3 text-xs font-medium",
                active ? "text-signal-dark" : "text-yard-500"
              )}
            >
              <Icon size={22} strokeWidth={active ? 2.5 : 2} />
              {label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
