import type { LucideIcon } from "lucide-react";

export type AuthenticatedUser = {
  sub: string;
  name: string;
  email: string | null;
  picture: string | null;
};

export type Agent = {
  id: string;
  name: string;
  summary: string;
  provider_status: string;
  capabilities: { action: string; resource: string; description: string }[];
};

export type ParsedTask = {
  agent_id: string;
  action: string;
  resource: string;
  confidence: "high" | "medium" | "low";
  reasoning: string;
};

export type TaskResponse = {
  status: "completed" | "denied";
  permission_granted: boolean;
  parsed_task: ParsedTask;
  token: {
    agent_id: string;
    scopes: string[];
    expires_at: string;
  } | null;
  result: {
    summary: string;
    details: Record<string, unknown>;
  } | null;
  audit_trail: string[];
};

export type TaskHistoryItem = {
  id: string;
  created_at: string;
  input_text: string;
  status: "completed" | "denied";
  permission_granted: boolean;
  parsed_task: { agent_id: string };
};

export type PermissionMap = Record<string, string[]>;

export type TokenInfo = {
  kind: string;
  ttl_minutes: number | null;
  issuer: string;
  note: string;
};

export type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
  kind: "conversation" | "status";
};

export type ChatRequestMessage = Pick<ChatMessage, "role" | "content">;

export type ChatCompletionRequest = {
  prompt?: string;
  messages?: ChatRequestMessage[];
};

export type ChatCompletionResponse = { response: string };

export type GoogleConnectResponse = {
  auth_url: string;
};

export type GoogleStatus = {
  connected: boolean;
  email: string | null;
  scopes: string[];
  updated_at: string | null;
};

export type GoogleSummaryResponse = {
  response: string;
  email_count: number;
  event_count: number;
  connected_email: string | null;
};

export type DashboardBootstrapResponse = {
  agents: Agent[];
  history: TaskHistoryItem[];
  permissions: PermissionMap;
  token_info: TokenInfo;
};

export type ActivityItem = {
  id: string;
  title: string;
  detail: string;
  status: "live" | "complete" | "warning" | "idle";
  icon: LucideIcon;
  timestamp: string;
};

export type EmailSummary = {
  id: string;
  sender: string;
  subject: string;
  preview: string;
  priority: "High" | "Rule" | "FYI";
};

export type ScheduleItem = {
  id: string;
  title: string;
  time: string;
  detail: string;
};

export type DeepWorkGap = {
  id: string;
  window: string;
  suggestion: string;
};

export type StudyFile = {
  id: string;
  name: string;
  sizeLabel: string;
  addedAt: string;
};
