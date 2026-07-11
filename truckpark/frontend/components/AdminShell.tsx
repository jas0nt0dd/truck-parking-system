"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  History,
  Receipt,
  Users,
  FileBarChart,
  LogOut,
  Menu,
} from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/lib/AuthContext";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/sessions", label: "Sessions & History", icon: History },
  { href: "/billing", label: "Billing Rules", icon: Receipt },
  { href: "/reports", label: "Reports", icon: FileBarChart },
  { href: "/users", label: "Users", icon: Users },
];

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-yard-50">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-20 w-64 transform bg-yard-900 text-white transition-transform md:static md:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="px-5 py-5">
          <p className="text-lg font-bold tracking-tight">TruckPark</p>
          <p className="text-xs text-yard-100/60">Admin Panel</p>
        </div>
        <nav className="mt-2 flex flex-col gap-0.5 px-3">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname?.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "flex items-center gap-3 rounded px-3 py-2.5 text-sm font-medium transition",
                  active ? "bg-signal text-yard-950" : "text-yard-100/80 hover:bg-yard-800"
                )}
              >
                <Icon size={18} />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 border-t border-yard-800 px-5 py-4">
          <p className="text-sm font-medium">{user?.name}</p>
          <p className="text-xs text-yard-100/60">{user?.is_root ? "Root Admin" : "Admin"}</p>
          <button
            onClick={logout}
            className="mt-3 flex items-center gap-2 text-sm text-yard-100/70 hover:text-white"
          >
            <LogOut size={16} /> Log out
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <div
          className="fixed inset-0 z-10 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <div className="flex-1">
        <header className="flex items-center justify-between border-b border-yard-100 bg-white px-4 py-3 md:hidden">
          <button onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu size={22} />
          </button>
          <p className="text-sm font-semibold">TruckPark Admin</p>
          <div className="w-6" />
        </header>
        <main className="p-4 md:p-8">{children}</main>
      </div>
    </div>
  );
}
