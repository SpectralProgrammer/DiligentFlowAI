"use client";

import { type FormEvent, type KeyboardEvent, type ReactNode, useEffect, useRef, useState, useTransition } from "react";
import {
  Bot,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Link2,
  Link2Off,
  LogOut,
  Plus,
  ShieldCheck,
  Sparkles,
  SquarePen,
} from "lucide-react";
import type {
  Agent,
  AuthenticatedUser,
  ChatCompletionRequest,
  ChatCompletionResponse,
  ChatMessage,
  DashboardBootstrapResponse,
  GoogleConnectResponse,
  GoogleStatus,
  GoogleSummaryResponse,
  PermissionMap,
  TaskHistoryItem,
  TaskResponse,
  TokenInfo,
} from "@/components/dashboard/types";

export type { AuthenticatedUser } from "@/components/dashboard/types";

const apiBaseUrl = "/api/backend";

const actionStarters = [
  "Flag my urgent emails and draft a reply to my boss about tomorrow's review.",
  "Plan my calendar around two deep work blocks tomorrow afternoon.",
  "Analyze Nvidia and summarize the biggest market signals before lunch.",
];

const suggestionCards = [
  {
    id: "status",
    label: "Ask",
    mode: "assistant" as const,
    prompt: "Explain how this project uses Auth0, permissions, and short-lived tokens.",
  },
  {
    id: "email",
    label: "Action",
    mode: "action" as const,
    prompt: actionStarters[0],
  },
  {
    id: "schedule",
    label: "Action",
    mode: "action" as const,
    prompt: actionStarters[1],
  },
  {
    id: "market",
    label: "Action",
    mode: "action" as const,
    prompt: actionStarters[2],
  },
  {
    id: "google-summary",
    label: "Ask",
    mode: "assistant" as const,
    prompt: "Summarize my unread emails and today's calendar.",
  },
];

const welcomeMessage = {
  id: "welcome",
  role: "assistant" as const,
  kind: "status" as const,
  content:
    "I can answer questions through the backend chat route or run protected actions through the task broker. Connect Google when you want Gmail and Calendar summaries here too.",
};

type ComposerMode = "assistant" | "action";

export default function SimpleAssistant({ user }: { user: AuthenticatedUser }) {
  const [mode, setMode] = useState<ComposerMode>("assistant");
  const [prompt, setPrompt] = useState(actionStarters[0]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [history, setHistory] = useState<TaskHistoryItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionMap>({});
  const [tokenInfo, setTokenInfo] = useState<TokenInfo | null>(null);
  const [googleStatus, setGoogleStatus] = useState<GoogleStatus | null>(null);
  const [result, setResult] = useState<TaskResponse | null>(null);
  const [chatInput, setChatInput] = useState("What matters most in this project today?");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([welcomeMessage]);
  const [chatError, setChatError] = useState<string | null>(null);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isGoogleBusy, setIsGoogleBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const feedRef = useRef<HTMLDivElement | null>(null);

  const trimmedPrompt = prompt.trim();
  const trimmedChatInput = chatInput.trim();
  const preview = result?.parsed_task ?? inferRoute(trimmedPrompt);
  const scopeCount = Object.values(permissions).flat().length;
  const visibleScopes = result?.token?.scopes ?? permissions[preview.agent_id] ?? [];
  const recentHistory = history.slice(0, 6);
  const showSuggestions = chatMessages.length === 1 && !result;

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      try {
        const [dashboardData, googleConnection] = await Promise.all([
          fetchJson<DashboardBootstrapResponse>(`${apiBaseUrl}/dashboard/bootstrap`),
          fetchJson<GoogleStatus>(`${apiBaseUrl}/google/status`),
        ]);

        if (!cancelled) {
          setAgents(dashboardData.agents);
          setHistory(dashboardData.history);
          setPermissions(dashboardData.permissions);
          setTokenInfo(dashboardData.token_info);
          setGoogleStatus(googleConnection);
        }
      } catch (caughtError: unknown) {
        if (!cancelled) {
          const message =
            caughtError instanceof Error
              ? caughtError.message
              : "Start FastAPI on port 8000 or set API_BASE_URL in the frontend environment.";

          setError(`Dashboard load failed. ${message}`);
        }
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const googleState = params.get("google");
    const googleMessage = params.get("message");
    if (!googleState) {
      return;
    }

    if (googleState === "connected") {
      setChatMessages((currentMessages) => [
        ...currentMessages,
        createChatMessage(
          "assistant",
          googleMessage ?? "Google connected. Ask for Gmail and Calendar summaries anytime.",
          "status"
        ),
      ]);
      void fetchJson<GoogleStatus>(`${apiBaseUrl}/google/status`)
        .then((connection) => setGoogleStatus(connection))
        .catch(() => undefined);
    } else {
      setChatError(googleMessage ?? "Google connection failed.");
    }

    params.delete("google");
    params.delete("message");
    const nextQuery = params.toString();
    const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ""}`;
    window.history.replaceState({}, "", nextUrl);
  }, []);

  useEffect(() => {
    const element = feedRef.current;
    if (!element) {
      return;
    }

    element.scrollTo({
      top: element.scrollHeight,
      behavior: "smooth",
    });
  }, [chatMessages, result, error, chatError, isPending, isChatLoading]);

  function resetWorkspace() {
    setMode("assistant");
    setPrompt(actionStarters[0]);
    setChatInput("What matters most in this project today?");
    setResult(null);
    setError(null);
    setChatError(null);
    setChatMessages([welcomeMessage]);
  }

  function handleSuggestion(modeValue: ComposerMode, value: string) {
    setMode(modeValue);
    if (modeValue === "assistant") {
      setChatInput(value);
      return;
    }
    setPrompt(value);
  }

  function runProtectedActionTask(inputText: string) {
    startTransition(async () => {
      try {
        const data = await fetchJson<TaskResponse>(`${apiBaseUrl}/tasks`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ input_text: inputText }),
        });
        const updatedHistory = await fetchJson<TaskHistoryItem[]>(`${apiBaseUrl}/history`);
        setResult(data);
        setHistory(updatedHistory);
      } catch (caughtError: unknown) {
        const message =
          caughtError instanceof Error ? caughtError.message : "Task submission failed.";

        setError(message);
      }
    });
  }

  function handleTaskSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmedPrompt || isPending) {
      return;
    }

    setMode("action");
    setError(null);
    runProtectedActionTask(trimmedPrompt);
  }

  async function handleConnectGoogle() {
    if (isGoogleBusy) {
      return;
    }

    setIsGoogleBusy(true);
    setChatError(null);
    try {
      const response = await fetchJson<GoogleConnectResponse>(`${apiBaseUrl}/google/connect`, {
        method: "POST",
      });
      window.location.href = response.auth_url;
    } catch (caughtError: unknown) {
      const message =
        caughtError instanceof Error ? caughtError.message : "Could not start the Google connection flow.";
      setChatError(message);
      setIsGoogleBusy(false);
    }
  }

  async function handleDisconnectGoogle() {
    if (isGoogleBusy) {
      return;
    }

    setIsGoogleBusy(true);
    setChatError(null);
    try {
      await fetchJson<{ disconnected: boolean }>(`${apiBaseUrl}/google/connection`, {
        method: "DELETE",
      });
      setGoogleStatus({
        connected: false,
        email: null,
        scopes: [],
        updated_at: null,
      });
      setChatMessages((currentMessages) => [
        ...currentMessages,
        createChatMessage("assistant", "Google was disconnected from this workspace.", "status"),
      ]);
    } catch (caughtError: unknown) {
      const message =
        caughtError instanceof Error ? caughtError.message : "Could not disconnect Google.";
      setChatError(message);
    } finally {
      setIsGoogleBusy(false);
    }
  }

  function handleChatSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!trimmedChatInput || isChatLoading) {
      return;
    }

    setMode("assistant");
    setChatError(null);
    const requestMessages = buildConversationMessages(chatMessages, trimmedChatInput);
    setChatMessages((currentMessages) => [
      ...currentMessages,
      createChatMessage("user", trimmedChatInput),
    ]);
    setChatInput("");
    setIsChatLoading(true);

    const shouldUseGoogleSummary = shouldUseGoogleWorkspacePrompt(trimmedChatInput);
    const endpoint = shouldUseGoogleSummary ? `${apiBaseUrl}/google/summary` : `${apiBaseUrl}/chat`;
    const requestBody: ChatCompletionRequest = shouldUseGoogleSummary
      ? { prompt: trimmedChatInput }
      : { messages: requestMessages };

    void fetchJson<ChatCompletionResponse | GoogleSummaryResponse>(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestBody),
    })
      .then((data) => {
        const sourceSuffix = "email_count" in data && "event_count" in data ? formatGoogleSourceSuffix(data) : "";
        setChatMessages((currentMessages) => [
          ...currentMessages,
          createChatMessage("assistant", `${data.response}${sourceSuffix}`),
        ]);
      })
      .catch((caughtError: unknown) => {
        const message =
          caughtError instanceof Error
            ? caughtError.message
            : "The assistant request failed. Confirm the backend is running and Gemini is configured.";

        setChatError(message);
        setChatMessages((currentMessages) => [
          ...currentMessages,
          createChatMessage(
            "assistant",
            "I couldn't answer just now. Check the backend logs, then try again.",
            "status"
          ),
        ]);
      })
      .finally(() => {
        setIsChatLoading(false);
      });
  }

  return (
    <main className="min-h-screen bg-[#f6f4ef] text-slate-900 dark:bg-[#111111] dark:text-slate-100">
      <div className="mx-auto flex h-[calc(100dvh-2rem)] max-w-[1440px] gap-4 p-4 sm:h-[calc(100dvh-3rem)] sm:p-6">
        <aside className="hidden h-full w-72 shrink-0 rounded-[28px] border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#171717] lg:flex lg:flex-col">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
              Authorized to Act
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight">Authorized Assistant</h1>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              A simpler workspace for asking questions and running protected actions.
            </p>
          </div>

          <button
            type="button"
            onClick={resetWorkspace}
            className="mt-5 inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm font-medium transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/[0.04] dark:hover:bg-white/[0.08]"
          >
            <Plus className="h-4 w-4" />
            New chat
          </button>

          <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/[0.03]">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-200 text-sm font-semibold text-slate-700 dark:bg-white/[0.08] dark:text-slate-100">
                {getInitials(user.name)}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold">{user.name}</p>
                <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                  {user.email ?? user.sub}
                </p>
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-emerald-600 dark:text-emerald-300">
              <ShieldCheck className="h-4 w-4" />
              Auth0 active
            </div>
          </div>

          <div className="mt-4 rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
              Google Workspace
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
              {googleStatus?.connected
                ? `Connected as ${googleStatus.email ?? "your Google account"} for Gmail and Calendar summaries.`
                : "Connect Google to pull unread Gmail and today's calendar into the assistant."}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleConnectGoogle}
                disabled={isGoogleBusy}
                className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
              >
                <Link2 className="h-4 w-4" />
                {googleStatus?.connected ? "Reconnect Google" : "Connect Google"}
              </button>
              {googleStatus?.connected ? (
                <button
                  type="button"
                  onClick={handleDisconnectGoogle}
                  disabled={isGoogleBusy}
                  className="inline-flex items-center gap-2 rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-200 dark:hover:bg-white/[0.08]"
                >
                  <Link2Off className="h-4 w-4" />
                  Disconnect
                </button>
              ) : null}
            </div>
          </div>

          <div className="mt-6">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">
              Recent actions
            </p>
            <div className="mt-3 space-y-2">
              {recentHistory.length > 0 ? (
                recentHistory.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => {
                      setMode("action");
                      setPrompt(item.input_text);
                    }}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-3 py-3 text-left transition hover:bg-slate-50 dark:border-white/10 dark:bg-white/[0.03] dark:hover:bg-white/[0.06]"
                  >
                    <p className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      {labelAgent(item.parsed_task.agent_id)}
                    </p>
                    <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
                      {item.input_text}
                    </p>
                    <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-slate-400 dark:text-slate-500">
                      {formatTimestamp(item.created_at)}
                    </p>
                  </button>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-300 px-3 py-4 text-sm leading-6 text-slate-500 dark:border-white/10 dark:text-slate-400">
                  Protected actions will appear here after the first run.
                </div>
              )}
            </div>
          </div>

          <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/[0.03]">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500 dark:text-slate-400">
              Status
            </p>
            <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              <p>{agents.length} agents ready</p>
              <p>{scopeCount} scopes published</p>
              <p>
                {tokenInfo?.ttl_minutes
                  ? `${tokenInfo.ttl_minutes} minute tokens`
                  : "Auth0 session active"}
              </p>
            </div>
          </div>

          <a
            href="/auth/logout"
            className="mt-auto inline-flex items-center justify-center gap-2 rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm font-medium transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/[0.04] dark:hover:bg-white/[0.08]"
          >
            <LogOut className="h-4 w-4" />
            Sign out
          </a>
        </aside>

        <section className="flex h-full min-w-0 flex-1 flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm dark:border-white/10 dark:bg-[#171717]">
          <header className="flex flex-col gap-4 border-b border-slate-200 px-4 py-4 dark:border-white/10 sm:flex-row sm:items-center sm:justify-between sm:px-6">
            <div>
              <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                ChatGPT-style workspace
              </p>
              <h2 className="mt-1 text-xl font-semibold tracking-tight">Ask or act from one thread</h2>
            </div>
            <div className="flex flex-wrap gap-2">
              <HeaderPill icon={ShieldCheck} label="Auth0 protected" />
              <HeaderPill icon={Bot} label="/chat ready" />
              <HeaderPill icon={Sparkles} label={`${agents.length} agents`} />
            </div>
          </header>

          <div ref={feedRef} className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
            <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
              {showSuggestions ? (
                <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-6 dark:border-white/10 dark:bg-white/[0.03]">
                  <p className="text-sm font-medium text-slate-500 dark:text-slate-400">
                    Start with a prompt
                  </p>
                  <h3 className="mt-2 text-2xl font-semibold tracking-tight">
                    One assistant, two modes.
                  </h3>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {suggestionCards.map((card) => (
                      <button
                        key={card.id}
                        type="button"
                        onClick={() => handleSuggestion(card.mode, card.prompt)}
                        className="rounded-2xl border border-slate-200 bg-white px-4 py-4 text-left transition hover:bg-slate-50 dark:border-white/10 dark:bg-white/[0.04] dark:hover:bg-white/[0.08]"
                      >
                        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
                          {card.label}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">
                          {card.prompt}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}

              {chatMessages.map((message) => (
                <ChatBubble key={message.id} role={message.role} content={message.content} />
              ))}

              {isChatLoading ? (
                <ChatBubble role="assistant" content="Thinking through that request..." />
              ) : null}

              {isPending ? (
                <SystemCard
                  title="Running protected action"
                  description="Routing the request, checking policy, and waiting for the backend result."
                />
              ) : null}

              {result ? (
                <TaskResultCard
                  inputText={trimmedPrompt}
                  result={result}
                  tokenInfo={tokenInfo}
                  visibleScopes={visibleScopes}
                />
              ) : null}

              {error ? <SystemCard title="Action error" description={error} tone="danger" /> : null}
              {chatError ? (
                <SystemCard title="Assistant error" description={chatError} tone="danger" />
              ) : null}
            </div>
          </div>

          <div className="border-t border-slate-200 px-4 py-4 dark:border-white/10 sm:px-6">
            <div className="mx-auto w-full max-w-3xl">
              <div className="mb-3 flex flex-wrap gap-2">
                <ModeButton
                  active={mode === "assistant"}
                  icon={SquarePen}
                  label="Ask assistant"
                  onClick={() => setMode("assistant")}
                />
                <ModeButton
                  active={mode === "action"}
                  icon={Sparkles}
                  label="Run action"
                  onClick={() => setMode("action")}
                />
              </div>

              {mode === "assistant" ? (
                <form onSubmit={handleChatSubmit}>
                  <Composer
                    value={chatInput}
                    onChange={setChatInput}
                    placeholder="Message the assistant..."
                    submitLabel={isChatLoading ? "Thinking..." : "Send"}
                    disabled={!trimmedChatInput || isChatLoading}
                  />
                </form>
              ) : (
                <form onSubmit={handleTaskSubmit}>
                  <div className="mb-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-300">
                    <p className="font-medium text-slate-900 dark:text-slate-100">
                      Next route: {labelAgent(preview.agent_id)}
                    </p>
                    <p className="mt-1 leading-6">
                      {preview.action} on {preview.resource}
                      {tokenInfo?.issuer ? ` via ${tokenInfo.issuer}` : ""}.
                    </p>
                  </div>
                  <Composer
                    value={prompt}
                    onChange={setPrompt}
                    placeholder="Describe the action you want the broker to run..."
                    submitLabel={isPending ? "Running..." : "Run action"}
                    disabled={!trimmedPrompt || isPending}
                  />
                </form>
              )}

              <div className="mt-3 flex flex-wrap gap-2">
                {(mode === "assistant"
                  ? suggestionCards.filter((card) => card.mode === "assistant")
                  : suggestionCards.filter((card) => card.mode === "action")
                ).map((card) => (
                  <button
                    key={card.id}
                    type="button"
                    onClick={() => handleSuggestion(card.mode, card.prompt)}
                    className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 transition hover:bg-slate-50 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300 dark:hover:bg-white/[0.08]"
                  >
                    {card.prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Composer({
  value,
  onChange,
  placeholder,
  submitLabel,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  submitLabel: string;
  disabled: boolean;
}) {
  return (
    <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-3 dark:border-white/10 dark:bg-white/[0.03]">
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => handleComposerKeyDown(event, disabled)}
        rows={4}
        className="max-h-52 min-h-[7.5rem] w-full resize-none overflow-y-auto bg-transparent px-2 py-2 text-sm leading-7 outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
        placeholder={placeholder}
      />
      <div className="mt-2 flex items-center justify-between gap-3">
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Shift workflows between conversation and protected execution without leaving this thread.
        </p>
        <button
          type="submit"
          disabled={disabled}
          className="inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
        >
          {submitLabel}
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function handleComposerKeyDown(
  event: KeyboardEvent<HTMLTextAreaElement>,
  disabled: boolean
) {
  if (disabled || event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) {
    return;
  }

  event.preventDefault();
  event.currentTarget.form?.requestSubmit();
}

function ModeButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: typeof Bot;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${
        active
          ? "border-slate-900 bg-slate-900 text-white dark:border-slate-100 dark:bg-slate-100 dark:text-slate-900"
          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300 dark:hover:bg-white/[0.08]"
      }`}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function HeaderPill({
  icon: Icon,
  label,
}: {
  icon: typeof ShieldCheck;
  label: string;
}) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

type MessageBlock =
  | { type: "heading"; text: string }
  | { type: "paragraph"; lines: string[] }
  | { type: "unordered-list"; items: string[] }
  | { type: "ordered-list"; items: string[] }
  | { type: "code"; lines: string[] };

function ChatBubble({
  role,
  content,
}: {
  role: ChatMessage["role"];
  content: string;
}) {
  return (
    <div
      className={`rounded-[28px] px-5 py-4 ${
        role === "assistant"
          ? "border border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-white/[0.03]"
          : "ml-auto max-w-[90%] bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">
        {role === "assistant" ? "Assistant" : "You"}
      </p>
      <FormattedMessageContent content={content} role={role} />
    </div>
  );
}

function FormattedMessageContent({
  content,
  role,
}: {
  content: string;
  role: ChatMessage["role"];
}) {
  const toneClass =
    role === "assistant"
      ? "text-slate-700 dark:text-slate-200"
      : "text-white dark:text-slate-900";
  const accentClass =
    role === "assistant"
      ? "text-slate-500 dark:text-slate-400"
      : "text-white/70 dark:text-slate-700";
  const blocks = parseMessageBlocks(content);

  return (
    <div className={`mt-3 space-y-3 text-sm leading-7 ${toneClass}`}>
      {blocks.map((block, index) => {
        switch (block.type) {
          case "heading":
            return (
              <h4
                key={`${block.type}-${index}`}
                className={`text-xs font-semibold uppercase tracking-[0.18em] ${accentClass}`}
              >
                {renderInlineContent(block.text)}
              </h4>
            );
          case "unordered-list":
            return (
              <ul key={`${block.type}-${index}`} className="space-y-2 pl-5">
                {block.items.map((item, itemIndex) => (
                  <li key={`${index}-${itemIndex}`} className="list-disc">
                    {renderInlineContent(item)}
                  </li>
                ))}
              </ul>
            );
          case "ordered-list":
            return (
              <ol key={`${block.type}-${index}`} className="space-y-2 pl-5">
                {block.items.map((item, itemIndex) => (
                  <li key={`${index}-${itemIndex}`} className="list-decimal">
                    {renderInlineContent(item)}
                  </li>
                ))}
              </ol>
            );
          case "code":
            return (
              <pre
                key={`${block.type}-${index}`}
                className="overflow-x-auto rounded-2xl bg-slate-900/95 px-4 py-3 text-xs leading-6 text-slate-100 dark:bg-[#050505]"
              >
                <code>{block.lines.join("\n")}</code>
              </pre>
            );
          case "paragraph":
          default:
            return (
              <p key={`${block.type}-${index}`}>
                {block.lines.map((line, lineIndex) => (
                  <span key={`${index}-${lineIndex}`}>
                    {lineIndex > 0 ? <br /> : null}
                    {renderInlineContent(line)}
                  </span>
                ))}
              </p>
            );
        }
      })}
    </div>
  );
}

function SystemCard({
  title,
  description,
  tone = "neutral",
}: {
  title: string;
  description: string;
  tone?: "neutral" | "danger";
}) {
  return (
    <div
      className={`rounded-[28px] border px-5 py-4 ${
        tone === "danger"
          ? "border-rose-200 bg-rose-50 text-rose-900 dark:border-rose-300/20 dark:bg-rose-300/10 dark:text-rose-100"
          : "border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-white/[0.03]"
      }`}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] opacity-70">{title}</p>
      <p className="mt-2 text-sm leading-7">{description}</p>
    </div>
  );
}

function TaskResultCard({
  inputText,
  result,
  tokenInfo,
  visibleScopes,
}: {
  inputText: string;
  result: TaskResponse;
  tokenInfo: TokenInfo | null;
  visibleScopes: string[];
}) {
  const detailEntries = Object.entries(result.result?.details ?? {}).slice(0, 8);

  return (
    <div className="rounded-[28px] border border-slate-200 bg-slate-50 p-5 dark:border-white/10 dark:bg-white/[0.03]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
            Protected action
          </p>
          <h3 className="mt-2 text-lg font-semibold">
            {result.result?.summary ?? "Action completed"}
          </h3>
        </div>
        <span
          className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
            result.permission_granted
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-300/10 dark:text-emerald-200"
              : "bg-amber-100 text-amber-700 dark:bg-amber-300/10 dark:text-amber-200"
          }`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          {result.permission_granted ? "Permission granted" : "Denied"}
        </span>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <MetaItem label="Prompt" value={inputText} />
        <MetaItem label="Agent" value={labelAgent(result.parsed_task.agent_id)} />
        <MetaItem label="Action" value={result.parsed_task.action} />
        <MetaItem label="Resource" value={result.parsed_task.resource} />
      </div>

      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-[#111111]">
        <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          Audit trail
        </p>
        <div className="mt-3 space-y-2">
          {result.audit_trail.map((entry, index) => (
            <div key={`${entry}-${index}`} className="flex gap-3">
              <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-semibold text-white dark:bg-slate-100 dark:text-slate-900">
                {index + 1}
              </span>
              <p className="text-sm leading-6 text-slate-700 dark:text-slate-200">{entry}</p>
            </div>
          ))}
        </div>
      </div>

      {detailEntries.length > 0 ? (
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {detailEntries.map(([label, value]) => (
            <MetaItem key={label} label={label.replace(/_/g, " ")} value={formatDetailValue(value)} />
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap gap-2">
        {visibleScopes.map((scope) => (
          <span
            key={scope}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium uppercase tracking-[0.16em] text-slate-600 dark:border-white/10 dark:bg-[#111111] dark:text-slate-300"
          >
            {scope}
          </span>
        ))}
        {visibleScopes.length === 0 ? (
          <span className="rounded-full border border-dashed border-slate-300 px-3 py-1.5 text-xs uppercase tracking-[0.16em] text-slate-400 dark:border-white/10 dark:text-slate-500">
            No scopes returned
          </span>
        ) : null}
      </div>

      {result.token || tokenInfo?.note ? (
        <div className="mt-4 flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
          <Clock3 className="h-4 w-4" />
          {result.token
            ? `Expires ${new Date(result.token.expires_at).toLocaleString()}`
            : tokenInfo?.note}
        </div>
      ) : null}
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-white/10 dark:bg-[#111111]">
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500 dark:text-slate-400">
        {label}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-200">{value}</p>
    </div>
  );
}

function inferRoute(inputText: string) {
  const normalized = inputText.toLowerCase();
  if (["email", "mail", "send", "draft", "reply"].some((term) => normalized.includes(term))) {
    return {
      agent_id: "email-agent",
      action: normalized.includes("draft") ? "draft" : "send",
      resource: "gmail-api",
      confidence: "high" as const,
      reasoning: "The request looks like email work, so the email agent is the best fit.",
    };
  }
  if (["calendar", "meeting", "schedule", "invite"].some((term) => normalized.includes(term))) {
    return {
      agent_id: "calendar-agent",
      action: ["show", "check", "read"].some((term) => normalized.includes(term)) ? "read" : "schedule",
      resource: "google-calendar",
      confidence: "high" as const,
      reasoning: "The request reads like a scheduling task, so the calendar agent is most likely.",
    };
  }
  return {
    agent_id: "finance-agent",
    action: "analyze",
    resource: "market-data",
    confidence: "medium" as const,
    reasoning:
      "This falls back to the finance agent because it does not match email or calendar language.",
  };
}

function shouldUseGoogleWorkspacePrompt(inputText: string) {
  const normalized = inputText.toLowerCase();
  const mentionsGoogleSource = ["email", "gmail", "inbox", "calendar", "meeting", "schedule", "event"].some(
    (term) => normalized.includes(term)
  );
  const mentionsWorkspaceIntent = [
    "summarize",
    "summary",
    "brief",
    "overview",
    "unread",
    "today",
  ].some((term) => normalized.includes(term));
  return mentionsGoogleSource && mentionsWorkspaceIntent;
}

async function fetchJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  const payload = (await response.json().catch(() => null)) as T | { detail?: unknown } | null;
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload ? payload.detail : null;
    throw new Error(
      typeof detail === "string" ? detail : `Request failed with status ${response.status}`
    );
  }
  return payload as T;
}

function parseMessageBlocks(content: string): MessageBlock[] {
  const lines = content.replace(/\r/g, "").split("\n");
  const blocks: MessageBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const currentLine = lines[index].trim();
    if (!currentLine) {
      index += 1;
      continue;
    }

    if (currentLine.startsWith("```")) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith("```")) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push({ type: "code", lines: codeLines });
      continue;
    }

    const chunk: string[] = [];
    while (index < lines.length && lines[index].trim()) {
      chunk.push(lines[index].trim());
      index += 1;
    }

    if (chunk.every((line) => /^[-*•]\s+/.test(line))) {
      blocks.push({
        type: "unordered-list",
        items: chunk.map((line) => line.replace(/^[-*•]\s+/, "")),
      });
      continue;
    }

    if (chunk.every((line) => /^\d+\.\s+/.test(line))) {
      blocks.push({
        type: "ordered-list",
        items: chunk.map((line) => line.replace(/^\d+\.\s+/, "")),
      });
      continue;
    }

    if (chunk.length === 1) {
      const heading = normalizeHeading(chunk[0]);
      if (heading) {
        blocks.push({ type: "heading", text: heading });
        continue;
      }
    }

    blocks.push({ type: "paragraph", lines: chunk });
  }

  return blocks;
}

function normalizeHeading(line: string) {
  const markdownHeading = line.match(/^#{1,3}\s+(.+)/);
  if (markdownHeading) {
    return markdownHeading[1].trim();
  }

  if (line.endsWith(":") && line.length <= 60 && !line.includes(".")) {
    return line.slice(0, -1).trim();
  }

  return null;
}

function renderInlineContent(text: string) {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const matchedText = match[0];
    const startIndex = match.index ?? 0;
    if (startIndex > lastIndex) {
      nodes.push(text.slice(lastIndex, startIndex));
    }

    if (matchedText.startsWith("**") && matchedText.endsWith("**")) {
      nodes.push(
        <strong key={`${startIndex}-strong`} className="font-semibold text-current">
          {matchedText.slice(2, -2)}
        </strong>
      );
    } else if (matchedText.startsWith("`") && matchedText.endsWith("`")) {
      nodes.push(
        <code
          key={`${startIndex}-code`}
          className="rounded-md bg-slate-900/10 px-1.5 py-0.5 font-mono text-[0.92em] dark:bg-white/10"
        >
          {matchedText.slice(1, -1)}
        </code>
      );
    }

    lastIndex = startIndex + matchedText.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length > 0 ? nodes : text;
}

function formatGoogleSourceSuffix(summary: GoogleSummaryResponse) {
  return `\n\nSource snapshot: ${summary.email_count} unread emails and ${summary.event_count} events.`;
}

function formatDetailValue(value: unknown) {
  if (value == null) {
    return "None";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.length > 0 ? JSON.stringify(value) : "[]";
  }
  return JSON.stringify(value);
}

function createChatMessage(
  role: ChatMessage["role"],
  content: string,
  kind: ChatMessage["kind"] = "conversation"
): ChatMessage {
  return {
    id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    role,
    content,
    kind,
  };
}

function buildConversationMessages(
  currentMessages: ChatMessage[],
  latestUserInput: string
): ChatCompletionRequest["messages"] {
  const history = [
    ...currentMessages.filter((message) => message.kind === "conversation"),
    {
      id: "pending-user-turn",
      role: "user" as const,
      content: latestUserInput,
      kind: "conversation" as const,
    },
  ];

  return history.slice(-12).map(({ role, content }) => ({
    role,
    content,
  }));
}

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((segment) => segment[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

function labelAgent(agentId: string) {
  return agentId
    .split("-")
    .map((segment) => `${segment[0]?.toUpperCase() ?? ""}${segment.slice(1)}`)
    .join(" ");
}

function formatTimestamp(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Recent";
  }
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
