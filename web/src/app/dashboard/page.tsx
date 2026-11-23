import type { Metadata } from "next";

import { Dashboard } from "@/components/dashboard";
import { PageHeader } from "@/components/page-header";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  return (
    <>
      <PageHeader
        title="Audit dashboard"
        description="What the gateway decided, and what kinds of data people tried to send. Raw secrets and prompt text are never stored."
      />
      <Dashboard />
    </>
  );
}
