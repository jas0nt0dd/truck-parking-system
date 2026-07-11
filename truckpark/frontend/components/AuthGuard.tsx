"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import type { Role } from "@/lib/auth";

export function AuthGuard({
  allow,
  children,
}: {
  allow: Role[];
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!allow.includes(user.role)) {
      router.replace(user.role === "admin" ? "/dashboard" : "/entry");
    }
  }, [loading, user, allow, router]);

  if (loading || !user || !allow.includes(user.role)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-yard-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-yard-300 border-t-signal" />
      </div>
    );
  }

  return <>{children}</>;
}
