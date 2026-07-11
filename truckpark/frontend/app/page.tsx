"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { homeRouteForRole } from "@/lib/auth";

export default function RootPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? homeRouteForRole(user.role) : "/login");
  }, [loading, user, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-yard-50">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-yard-300 border-t-signal" />
    </div>
  );
}
