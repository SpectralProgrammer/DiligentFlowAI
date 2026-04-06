import { auth0 } from "@/lib/auth0";
import { ThemeToggle } from "@/components/theme-toggle";
import SmartDashboard, { type AuthenticatedUser } from "./command-center-dashboard";

function mapAuthenticatedUser(sessionUser: Record<string, unknown>): AuthenticatedUser {
  const name =
    (typeof sessionUser.name === "string" && sessionUser.name) ||
    (typeof sessionUser.nickname === "string" && sessionUser.nickname) ||
    (typeof sessionUser.email === "string" && sessionUser.email) ||
    "Authorized Operator";

  return {
    sub: typeof sessionUser.sub === "string" ? sessionUser.sub : "unknown-user",
    name,
    email: typeof sessionUser.email === "string" ? sessionUser.email : null,
    picture: typeof sessionUser.picture === "string" ? sessionUser.picture : null,
  };
}

export default async function Home() {
  const session = await auth0.getSession();

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f6f4ef] px-6 py-12 text-slate-900 dark:bg-[#111111] dark:text-slate-100">
        <section className="w-full max-w-2xl rounded-[32px] border border-slate-300/80 bg-white/95 p-8 shadow-[0_24px_60px_rgba(15,23,42,0.08)] dark:border-white/10 dark:bg-[#171717] sm:p-10">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-sky-700 dark:text-slate-400">
                Authorized to Act
              </p>
              <h1 className="mt-4 text-4xl font-semibold tracking-tight text-slate-950 dark:text-slate-50 sm:text-5xl">
                Sign in to use the assistant.
              </h1>
            </div>
            <ThemeToggle />
          </div>

          <p className="mt-6 text-base leading-8 text-slate-700 dark:text-slate-300">
            This frontend keeps the experience simple: one conversation surface for questions and
            protected AI actions, backed by Auth0 and the FastAPI broker.
          </p>

          <div className="mt-8 flex flex-wrap gap-3">
            <a
              href="/auth/login"
              className="inline-flex min-w-[11.5rem] items-center justify-center rounded-full bg-slate-900 px-6 py-3 text-sm font-semibold text-white shadow-[0_12px_24px_rgba(15,23,42,0.18)] transition hover:bg-slate-800 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
            >
              Sign in with Auth0
            </a>
            <a
              href="/auth/login?screen_hint=signup"
              className="rounded-full border border-slate-300 bg-slate-50 px-6 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-100 dark:hover:bg-white/[0.08]"
            >
              Create account
            </a>
          </div>

          <div className="mt-8 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/[0.03]">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700 dark:text-slate-400">
                Auth0
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                Secures the operator session.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/[0.03]">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700 dark:text-slate-400">
                FastAPI
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                Verifies tokens and routes actions.
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/[0.03]">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-700 dark:text-slate-400">
                Assistant
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-700 dark:text-slate-300">
                Chat and protected execution in one place.
              </p>
            </div>
          </div>
        </section>
      </main>
    );
  }

  return <SmartDashboard user={mapAuthenticatedUser(session.user as Record<string, unknown>)} />;
}
