"use client";

import { FormEvent, useEffect, useState, useTransition } from "react";

type Agent = {
  id: string;
  name: string;
  summary: string;
  provider_status: string;
  capabilities: { action: string; resource: string; description: string }[];
};

type ParsedTask = {
  agent_id: string;
  action: string;
  resource: string;
  confidence: "high" | "medium" | "low";
  reasoning: string;
};

type TaskResponse = {
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

type TaskHistoryItem = {
  id: string;
  created_at: string;
  input_text: string;
  status: "completed" | "denied";
  permission_granted: boolean;
  parsed_task: { agent_id: string };
};

type PermissionMap = Record<string, string[]>;
type TokenInfo = { kind: string; ttl_minutes: number; issuer: string; note: string };

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

const starterPrompts = [
  "Send an email to the design team with tomorrow's review agenda",
  "Schedule a meeting with Maya next Tuesday afternoon",
  "Analyze Nvidia and summarize the biggest market signals",
];

export default function SmartDashboard() {
  const [prompt, setPrompt] = useState(starterPrompts[0]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [history, setHistory] = useState<TaskHistoryItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionMap>({});
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [result, setResult] = useState<TaskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const preview = result?.parsed_task ?? inferRoute(prompt);
  const focusedAgent = agents.find((agent) => agent.id === preview.agent_id) ?? null;
  const approvalRate =
    history.length === 0
      ? 100
      : Math.round(
          (history.filter((item) => item.permission_granted).length / history.length) *
            100
        );

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const [agentsResponse, historyResponse, permissionsResponse, tokenResponse] =
          await Promise.all([
            fetch(`${apiBaseUrl}/agents`),
            fetch(`${apiBaseUrl}/history`),
            fetch(`${apiBaseUrl}/permissions`),
            fetch(`${apiBaseUrl}/tokens/about`),
          ]);

        if (
          !agentsResponse.ok ||
          !historyResponse.ok ||
          !permissionsResponse.ok ||
          !tokenResponse.ok
        ) {
          throw new Error("Unable to load backend data.");
        }

        const [agentsData, historyData, permissionsData, tokenData] = await Promise.all([
          agentsResponse.json() as Promise<Agent[]>,
          historyResponse.json() as Promise<TaskHistoryItem[]>,
          permissionsResponse.json() as Promise<PermissionMap>,
          tokenResponse.json() as Promise<TokenInfo>,
        ]);

        if (!cancelled) {
          setAgents(agentsData);
          setHistory(historyData);
          setPermissions(permissionsData);
          setTokenInfo(tokenData);
        }
      } catch {
        if (!cancelled) {
          setError(
            "The frontend could not reach the backend. Start FastAPI on port 8000 or set NEXT_PUBLIC_API_BASE_URL."
          );
        }
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    startTransition(async () => {
      try {
        const response = await fetch(`${apiBaseUrl}/tasks`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input_text: prompt }),
        });

        if (!response.ok) {
          throw new Error("Task execution failed.");
        }

        const data = (await response.json()) as TaskResponse;
        const historyResponse = await fetch(`${apiBaseUrl}/history`);
        const updatedHistory = (await historyResponse.json()) as TaskHistoryItem[];

        setResult(data);
        setHistory(updatedHistory);
      } catch {
        setError(
          "Task submission failed. If you want real providers next, I can wire them once you share the credentials."
        );
      }
    });
  }

  return (
    <main className="relative min-h-screen overflow-hidden bg-[linear-gradient(180deg,_#07131a_0%,_#0b2029_45%,_#102c37_100%)] text-slate-100">
      <div className="drift absolute left-[-8%] top-0 h-72 w-72 rounded-full bg-[radial-gradient(circle,_rgba(122,255,226,0.22),_transparent_68%)] blur-3xl" />
      <div className="drift absolute right-[-8%] top-20 h-96 w-96 rounded-full bg-[radial-gradient(circle,_rgba(84,168,255,0.20),_transparent_68%)] blur-3xl [animation-delay:-4s]" />
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,_transparent_1px),linear-gradient(90deg,_rgba(255,255,255,0.04)_1px,_transparent_1px)] bg-[size:88px_88px] opacity-[0.08]" />

      <div className="relative mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-6 sm:px-8 lg:py-8">
        <section className="reveal-up rounded-[32px] border border-white/10 bg-white/5 p-6 backdrop-blur-xl sm:p-8">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-3xl">
              <p className="text-[11px] uppercase tracking-[0.3em] text-emerald-200/80">
                Authorized To Act
              </p>
              <h1 className="mt-3 font-serif text-5xl leading-[1.02] text-white sm:text-6xl">
                Modern AI actions with visible trust boundaries.
              </h1>
              <p className="mt-5 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                Preview the route, inspect the policy gate, mint a short-lived token,
                then execute with least privilege.
              </p>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <GlassStat label="Approval rate" value={`${approvalRate}%`} />
              <GlassStat label="Token window" value={`${tokenInfo?.ttl_minutes ?? 30}m`} />
              <GlassStat label="Policy scopes" value={String(Object.values(permissions).flat().length)} />
            </div>
          </div>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <section className="reveal-up rounded-[32px] border border-white/10 bg-[#0d1b24]/88 p-6 shadow-[0_26px_90px_rgba(0,0,0,0.28)] backdrop-blur-xl [animation-delay:120ms]">
              <div className="grid gap-5 xl:grid-cols-[1fr_280px]">
                <form className="space-y-5" onSubmit={handleSubmit}>
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                      Command Console
                    </p>
                    <h2 className="mt-2 text-3xl font-semibold text-white">
                      Describe the work and inspect the route before execution.
                    </h2>
                  </div>

                  <textarea
                    value={prompt}
                    onChange={(event) => setPrompt(event.target.value)}
                    rows={7}
                    className="w-full rounded-[28px] border border-white/10 bg-[#071118] px-5 py-5 text-base leading-7 text-slate-100 outline-none transition focus:border-emerald-300/40 focus:shadow-[0_0_0_4px_rgba(110,231,183,0.08)]"
                    placeholder="Describe the task in plain language..."
                  />

                  <div className="flex flex-wrap gap-3">
                    {starterPrompts.map((starterPrompt) => (
                      <button
                        key={starterPrompt}
                        type="button"
                        onClick={() => setPrompt(starterPrompt)}
                        className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-emerald-300/30 hover:bg-emerald-300/8"
                      >
                        {starterPrompt}
                      </button>
                    ))}
                  </div>

                  <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <p className="text-sm leading-6 text-slate-400">
                      The console shows routing, policy, token scope, and the final normalized result.
                    </p>
                    <button
                      type="submit"
                      disabled={isPending}
                      className="rounded-full bg-[linear-gradient(135deg,_#82ffd7,_#6dd6ff)] px-6 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:brightness-75"
                    >
                      {isPending ? "Evaluating route..." : "Authorize + Execute"}
                    </button>
                  </div>
                </form>

                <div className="rounded-[28px] border border-white/10 bg-white/[0.04] p-5">
                  <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">
                    Likely route
                  </p>
                  <h3 className="mt-3 text-2xl font-semibold text-white">
                    {focusedAgent?.name ?? preview.agent_id}
                  </h3>
                  <p className="mt-2 text-sm leading-6 text-slate-300">
                    {focusedAgent?.summary ?? preview.reasoning}
                  </p>
                  <div className="mt-5 space-y-3 text-sm text-slate-200">
                    <InlineRow label="Action" value={preview.action} />
                    <InlineRow label="Resource" value={preview.resource} />
                    <InlineRow label="Confidence" value={preview.confidence} />
                    <InlineRow label="Broker" value={tokenInfo?.issuer ?? "Demo vault"} />
                  </div>
                </div>
              </div>

              {error ? (
                <div className="mt-5 rounded-[24px] border border-rose-300/20 bg-rose-300/8 p-4 text-sm leading-6 text-rose-100">
                  {error}
                </div>
              ) : null}
            </section>

            <section className="reveal-up rounded-[32px] border border-white/10 bg-[#eef4f2] p-6 text-slate-950 shadow-[0_26px_90px_rgba(0,0,0,0.24)] [animation-delay:200ms]">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.28em] text-slate-500">
                    Decision Sheet
                  </p>
                  <h2 className="mt-2 font-serif text-4xl text-slate-950">
                    {result?.result?.summary ?? "Run a task to generate a visible execution trace."}
                  </h2>
                </div>
                <Badge tone={result?.permission_granted ? "success" : "neutral"}>
                  {result ? (result.permission_granted ? "Permission granted" : "Denied") : "Idle"}
                </Badge>
              </div>

              {result ? (
                <div className="mt-6 space-y-5">
                  <div className="grid gap-4 md:grid-cols-3">
                    <PlainStat label="Agent" value={result.parsed_task.agent_id} />
                    <PlainStat label="Action" value={result.parsed_task.action} />
                    <PlainStat label="Resource" value={result.parsed_task.resource} />
                  </div>

                  <div className="grid gap-4 lg:grid-cols-2">
                    <Card title="Execution trace">
                      {result.audit_trail.map((entry, index) => (
                        <div key={entry} className="flex gap-3">
                          <div className="mt-1 flex h-6 w-6 items-center justify-center rounded-full bg-slate-950 text-xs text-white">
                            {index + 1}
                          </div>
                          <p className="text-sm leading-7 text-slate-700">{entry}</p>
                        </div>
                      ))}
                    </Card>

                    <Card title="Result payload">
                      {Object.entries(result.result?.details ?? {}).map(([key, value]) => (
                        <div
                          key={key}
                          className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3"
                        >
                          <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
                            {key}
                          </p>
                          <p className="mt-2 text-sm leading-6 text-slate-800">
                            {formatDetail(value)}
                          </p>
                        </div>
                      ))}
                    </Card>
                  </div>

                  {result.token ? (
                    <div className="rounded-[24px] border border-slate-200 bg-white p-5">
                      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">
                        Scoped token
                      </p>
                      <p className="mt-2 text-sm leading-7 text-slate-700">
                        Issued for {result.token.agent_id} and expires at{" "}
                        {new Date(result.token.expires_at).toLocaleString()}.
                      </p>
                      <div className="mt-4 flex flex-wrap gap-2">
                        {result.token.scopes.map((scope) => (
                          <span
                            key={scope}
                            className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-900"
                          >
                            {scope}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="mt-6 grid gap-4 md:grid-cols-3">
                  <PlainStat label="Preview routing" value="See the likely agent before the task runs." />
                  <PlainStat label="Inspect policy" value="Make access scopes visible to the operator." />
                  <PlainStat label="Time-box access" value="Keep execution auditable with short-lived tokens." />
                </div>
              )}
            </section>
          </div>

          <div className="space-y-6">
            <section className="reveal-up rounded-[32px] border border-white/10 bg-white/5 p-6 backdrop-blur-xl [animation-delay:160ms]">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">Policy map</p>
              <div className="mt-4 space-y-3">
                {Object.entries(permissions).map(([agentId, scopes]) => (
                  <div
                    key={agentId}
                    className={`rounded-[24px] border px-4 py-4 ${
                      agentId === preview.agent_id
                        ? "border-emerald-300/30 bg-emerald-300/10"
                        : "border-white/10 bg-white/[0.03]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-white">{agentId}</p>
                      <Badge tone="dark">{scopes.length} scopes</Badge>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {scopes.map((scope) => (
                        <span
                          key={scope}
                          className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-slate-200"
                        >
                          {scope}
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-4 text-sm leading-7 text-slate-400">
                {tokenInfo?.note ?? "Token metadata will appear here once the backend is connected."}
              </p>
            </section>

            <section className="reveal-up rounded-[32px] border border-white/10 bg-[#0f1f2a]/90 p-6 [animation-delay:240ms]">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">Agents</p>
              <div className="mt-4 space-y-3">
                {agents.map((agent) => (
                  <div
                    key={agent.id}
                    className={`rounded-[24px] border p-4 ${
                      agent.id === preview.agent_id
                        ? "border-cyan-300/30 bg-cyan-300/10"
                        : "border-white/10 bg-white/[0.03]"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                        <p className="mt-2 text-sm leading-6 text-slate-300">{agent.summary}</p>
                      </div>
                      <Badge tone="outline">{agent.provider_status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="reveal-up rounded-[32px] border border-white/10 bg-white/5 p-6 backdrop-blur-xl [animation-delay:320ms]">
              <p className="text-[11px] uppercase tracking-[0.28em] text-slate-400">Recent decisions</p>
              <div className="mt-4 space-y-3">
                {history.length === 0 ? (
                  <p className="rounded-[24px] border border-white/10 bg-white/[0.03] p-5 text-sm leading-7 text-slate-300">
                    No task history yet. Run a prompt and the timeline will appear here.
                  </p>
                ) : (
                  history.map((item) => (
                    <div key={item.id} className="rounded-[24px] border border-white/10 bg-white/[0.03] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-semibold text-white">{item.parsed_task.agent_id}</p>
                        <Badge tone={item.permission_granted ? "success" : "danger"}>
                          {item.status}
                        </Badge>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-slate-300">{item.input_text}</p>
                      <p className="mt-3 text-xs uppercase tracking-[0.18em] text-slate-500">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

function inferRoute(inputText: string): ParsedTask {
  const normalized = inputText.toLowerCase();
  if (["email", "mail", "send", "draft", "reply"].some((term) => normalized.includes(term))) {
    return {
      agent_id: "email-agent",
      action: normalized.includes("draft") ? "draft" : "send",
      resource: "gmail-api",
      confidence: "high",
      reasoning: "The prompt contains email language, so the email agent is the most likely route.",
    };
  }
  if (["calendar", "meeting", "schedule", "invite"].some((term) => normalized.includes(term))) {
    return {
      agent_id: "calendar-agent",
      action: ["show", "check", "read"].some((term) => normalized.includes(term)) ? "read" : "schedule",
      resource: "google-calendar",
      confidence: "high",
      reasoning: "The prompt reads like a scheduling request, so the calendar agent is the best match.",
    };
  }
  return {
    agent_id: "finance-agent",
    action: "analyze",
    resource: "market-data",
    confidence: "medium",
    reasoning: "The prompt does not match communication or scheduling keywords, so finance analysis is the fallback route.",
  };
}

function formatDetail(value: unknown): string {
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value);
}

function GlassStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[24px] border border-white/10 bg-white/[0.04] p-4">
      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-white">{value}</p>
    </div>
  );
}

function PlainStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-4">
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className="mt-2 text-base leading-6 text-slate-900">{value}</p>
    </div>
  );
}

function InlineRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-white/8 pb-3 last:border-b-0 last:pb-0">
      <span className="text-xs uppercase tracking-[0.2em] text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-100">{value}</span>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-[24px] border border-slate-200 bg-white p-5">
      <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">{title}</p>
      <div className="mt-4 space-y-3">{children}</div>
    </div>
  );
}

function Badge({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone: "success" | "danger" | "outline" | "dark" | "neutral";
}) {
  const styles = {
    success: "border border-emerald-300/30 bg-emerald-100 text-emerald-900",
    danger: "border border-rose-300/30 bg-rose-100 text-rose-900",
    outline: "border border-white/12 bg-white/5 text-slate-100",
    dark: "border border-slate-800 bg-slate-950 text-white",
    neutral: "border border-slate-300 bg-slate-200 text-slate-800",
  };
  return (
    <span className={`rounded-full px-3 py-1 text-xs uppercase tracking-[0.16em] ${styles[tone]}`}>
      {children}
    </span>
  );
}
