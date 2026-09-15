"use client";

import { useEffect, useState } from "react";

import { WebExtractRequestError, runWebExtract } from "@/lib/api/web-extract";
import type { WebExtractInput, WebExtractResponse } from "@/types/web-extract";

const DRAFT_STORAGE_KEY = "interfaze_project.extract_page.draft";
const RUNS_STORAGE_KEY = "interfaze_project.extract_page.runs";
const MAX_RECENT_RUNS = 5;

const defaultDraft: WebExtractInput = {
  prompt: "Extract the page title and primary heading",
  url: "https://example.com",
};

function readStoredValue<T>(storageKey: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }

  const raw = window.localStorage.getItem(storageKey);
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function formatResultValue(value: unknown) {
  if (typeof value === "string") {
    return value;
  }

  return JSON.stringify(value);
}

export function WebExtractConsole() {
  const [draft, setDraft] = useState<WebExtractInput>(defaultDraft);
  const [recentRuns, setRecentRuns] = useState<WebExtractResponse[]>([]);
  const [activeRun, setActiveRun] = useState<WebExtractResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setDraft(readStoredValue(DRAFT_STORAGE_KEY, defaultDraft));
    const storedRuns = readStoredValue<WebExtractResponse[]>(RUNS_STORAGE_KEY, []);
    setRecentRuns(storedRuns);
    setActiveRun(storedRuns[0] ?? null);
    setIsHydrated(true);
  }, []);
  /* eslint-enable react-hooks/set-state-in-effect */

  useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  }, [draft, isHydrated]);

  useEffect(() => {
    if (!isHydrated || typeof window === "undefined") {
      return;
    }

    window.localStorage.setItem(RUNS_STORAGE_KEY, JSON.stringify(recentRuns));
  }, [recentRuns, isHydrated]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const response = await runWebExtract(draft);
      setActiveRun(response);
      setRecentRuns((current) => [response, ...current].slice(0, MAX_RECENT_RUNS));
    } catch (error) {
      if (error instanceof WebExtractRequestError && error.response) {
        const failedResponse = error.response;
        setActiveRun(failedResponse);
        setRecentRuns((current) => [failedResponse, ...current].slice(0, MAX_RECENT_RUNS));
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("The page extraction task failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateDraft<K extends keyof WebExtractInput>(key: K, value: WebExtractInput[K]) {
    setDraft((current) => ({
      ...current,
      [key]: value,
    }));
  }

  const resultEntries = activeRun?.result
    ? Object.entries(activeRun.result.data)
    : [];

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent/80">
              Page extract
            </p>
            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-foreground sm:text-3xl">
              Pull structured JSON from one public page.
            </h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              Paste a public https URL and say what to extract. A parent planner writes a
              child prompt, deterministic tools fill JSON, and a checker scores the answer.
              Scores below 90% rerun the extract cycle up to three times.
            </p>
          </div>
        </div>

        <form className="mt-6 grid gap-5" onSubmit={handleSubmit}>
          <label className="grid gap-2">
            <span className="text-sm font-semibold text-foreground">Public page URL</span>
            <input
              className="min-h-11 rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-accent"
              onChange={(event) => updateDraft("url", event.target.value)}
              placeholder="https://example.com"
              type="url"
              value={draft.url}
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-semibold text-foreground">Extraction prompt</span>
            <textarea
              className="min-h-28 rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3 text-sm leading-6 text-foreground outline-none transition-colors focus:border-accent"
              onChange={(event) => updateDraft("prompt", event.target.value)}
              value={draft.prompt}
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-semibold text-foreground">Idempotency key</span>
            <input
              className="min-h-11 rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-accent"
              onChange={(event) => updateDraft("idempotencyKey", event.target.value)}
              placeholder="optional-stable-run-key"
              type="text"
              value={draft.idempotencyKey ?? ""}
            />
          </label>

          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <button
              className="min-h-11 rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Extracting page..." : "Extract page JSON"}
            </button>
            <p className="text-sm text-muted">
              Single public https page. Access walls can use Playwright; CAPTCHAs are not solved.
            </p>
          </div>
        </form>
      </section>

      <section className="grid gap-6">
        <div className="rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent/80">
                Latest result
              </p>
              <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                Extracted JSON and commands
              </h3>
            </div>
            {activeRun ? (
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${
                  activeRun.status
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-rose-50 text-rose-700"
                }`}
              >
                {activeRun.status ? "Succeeded" : "Failed"}
              </span>
            ) : (
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                No runs yet
              </span>
            )}
          </div>

          {activeRun ? (
            <div className="mt-5 grid gap-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Provider
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {activeRun.meta.siteType || activeRun.meta.provider}
                  </p>
                </article>
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Cache
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {activeRun.meta.cached ? "Returned from cache" : "Fresh extract"}
                  </p>
                </article>
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Page sample
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {activeRun.meta.truncated
                      ? `Clipped, ${activeRun.meta.regionPasses || 1} region pass`
                      : "Full download"}
                  </p>
                </article>
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Confidence
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {Math.round((activeRun.meta.confidence || 0) * 100)}% ·{" "}
                    {activeRun.meta.checkAttempts || 1} check
                    {(activeRun.meta.checkAttempts || 1) === 1 ? "" : "s"}
                  </p>
                </article>
              </div>

              {resultEntries.length > 0 ? (
                <div className="grid gap-3">
                  {resultEntries.map(([key, value]) => (
                    <article
                      className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4"
                      key={key}
                    >
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                        {key}
                      </p>
                      <p className="mt-2 break-words text-base font-semibold text-foreground">
                        {formatResultValue(value)}
                      </p>
                    </article>
                  ))}
                </div>
              ) : null}

              {activeRun.result?.commands.length ? (
                <pre className="overflow-x-auto rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4 text-xs leading-6 text-muted">
                  {JSON.stringify(activeRun.result.commands, null, 2)}
                </pre>
              ) : null}

              {!activeRun.status && activeRun.errors.length > 0 ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4">
                  <p className="text-sm font-semibold text-rose-700">Extract error</p>
                  <p className="mt-2 text-sm leading-6 text-rose-700">
                    {activeRun.errors[0]?.message}
                  </p>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface-strong)] px-4 py-8 text-sm leading-7 text-muted">
              Submit example.com or another public https page to generate the first JSON result.
            </div>
          )}
        </div>

        <div className="rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent/80">
                Recent runs
              </p>
              <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                Local extract history
              </h3>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              Last {MAX_RECENT_RUNS}
            </span>
          </div>

          {recentRuns.length > 0 ? (
            <div className="mt-5 overflow-x-auto rounded-2xl border border-[var(--line)]">
              <table className="min-w-full divide-y divide-[var(--line)] text-left text-sm">
                <thead className="bg-[var(--surface-strong)]">
                  <tr>
                    <th className="px-4 py-3 font-semibold text-foreground">Status</th>
                    <th className="px-4 py-3 font-semibold text-foreground">URL</th>
                    <th className="px-4 py-3 font-semibold text-foreground">Cache</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--line)] bg-[var(--surface)]">
                  {recentRuns.map((run) => (
                    <tr
                      className="cursor-pointer transition-colors hover:bg-[var(--surface-strong)]"
                      key={run.meta.requestId}
                      onClick={() => setActiveRun(run)}
                    >
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2 py-1 text-xs font-semibold uppercase tracking-[0.16em] ${
                            run.status
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-rose-50 text-rose-700"
                          }`}
                        >
                          {run.status ? "Success" : "Failed"}
                        </span>
                      </td>
                      <td className="max-w-[14rem] truncate px-4 py-3 text-foreground">
                        {run.result?.url || "Unavailable"}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {run.meta.cached ? "Cached" : "Fresh"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface-strong)] px-4 py-8 text-sm leading-7 text-muted">
              Recent extracts stay in this browser only.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
