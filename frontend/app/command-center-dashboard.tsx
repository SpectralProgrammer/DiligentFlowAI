"use client";

import SimpleAssistant, { type AuthenticatedUser } from "@/components/simple-assistant";

export type { AuthenticatedUser } from "@/components/simple-assistant";

export default function CommandCenterDashboard({ user }: { user: AuthenticatedUser }) {
  return <SimpleAssistant user={user} />;
}
