import { AuthGuard } from "@/components/AuthGuard";
import { GatekeeperShell } from "@/components/GatekeeperShell";

export default function GatekeeperLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard allow={["gatekeeper", "admin"]}>
      <GatekeeperShell>{children}</GatekeeperShell>
    </AuthGuard>
  );
}
