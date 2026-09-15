"use client";

import { useEffect, useState } from "react";

import { TaskRequestError, runExtractIdTask } from "@/lib/api/tasks";
import type { ExtractIdTaskInput, TaskRunResponse } from "@/types/task";

const DRAFT_STORAGE_KEY = "interfaze_project.extract_id.draft";
const RUNS_STORAGE_KEY = "interfaze_project.extract_id.runs";
const MAX_RECENT_RUNS = 5;

const defaultDraft: ExtractIdTaskInput = {
  imageUrl: "https://r2public.jigsawstack.com/interfaze/examples/id.jpg",
  instruction: "Extract the details from this ID",
};

type StoredRun = TaskRunResponse;

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

export function ExtractionConsole() {
  const [draft, setDraft] = useState<ExtractIdTaskInput>(defaultDraft);
  const [recentRuns, setRecentRuns] = useState<StoredRun[]>([]);
  const [activeRun, setActiveRun] = useState<StoredRun | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);

  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    setDraft(readStoredValue(DRAFT_STORAGE_KEY, defaultDraft));
    const storedRuns = readStoredValue<StoredRun[]>(RUNS_STORAGE_KEY, []);
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
      const response = await runExtractIdTask(draft);
      setActiveRun(response);
      setRecentRuns((current) => [response, ...current].slice(0, MAX_RECENT_RUNS));
    } catch (error) {
      if (error instanceof TaskRequestError && error.response) {
        const failedResponse = error.response;
        setActiveRun(failedResponse);
        setRecentRuns((current) => [failedResponse, ...current].slice(0, MAX_RECENT_RUNS));
        setErrorMessage(error.message);
      } else if (error instanceof Error) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("The extraction task failed.");
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateDraft<K extends keyof ExtractIdTaskInput>(
    key: K,
    value: ExtractIdTaskInput[K],
  ) {
    setDraft((current) => ({
      ...current,
      [key]: value,
    }));
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent/80">
              Extraction task
            </p>
            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.04em] text-foreground sm:text-3xl">
              Run one deterministic document workflow from the main product surface.
            </h2>
            <p className="mt-3 text-sm leading-7 text-muted">
              This console mirrors the interview shape more closely: provide a public
              document URL, submit one typed task, and inspect a structured result with
              cache and retry context.
            </p>
          </div>

          <div className="min-w-[15rem] rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted">
              Browser-sticky draft
            </p>
            <p className="mt-2 text-sm leading-6 text-muted">
              Input values and recent runs stay local in the browser so the operator can
              resume without re-entering non-secret task state.
            </p>
          </div>
        </div>

        <form className="mt-6 grid gap-5" onSubmit={handleSubmit}>
          <label className="grid gap-2">
            <span className="text-sm font-semibold text-foreground">Public image URL</span>
            <input
              className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-accent"
              onChange={(event) => updateDraft("imageUrl", event.target.value)}
              placeholder="https://example.com/id.jpg"
              type="url"
              value={draft.imageUrl}
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-semibold text-foreground">Instruction</span>
            <textarea
              className="min-h-28 rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3 text-sm leading-6 text-foreground outline-none transition-colors focus:border-accent"
              onChange={(event) => updateDraft("instruction", event.target.value)}
              value={draft.instruction}
            />
          </label>

          <label className="grid gap-2">
            <span className="text-sm font-semibold text-foreground">
              Idempotency key
            </span>
            <input
              className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-3 text-sm text-foreground outline-none transition-colors focus:border-accent"
              onChange={(event) => updateDraft("idempotencyKey", event.target.value)}
              placeholder="optional-stable-run-key"
              type="text"
              value={draft.idempotencyKey ?? ""}
            />
            <p className="text-xs leading-5 text-muted">
              Use the same key to safely retry the same request and receive a cached result
              when available.
            </p>
          </label>

          {errorMessage ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {errorMessage}
            </div>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <button
              className="rounded-2xl bg-accent px-5 py-3 text-sm font-semibold text-white transition-opacity disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              type="submit"
            >
              {isSubmitting ? "Running extraction..." : "Run extraction task"}
            </button>
            <p className="text-sm text-muted">
              Requires an authenticated session and a public `https` image URL.
            </p>
          </div>
        </form>
      </section>

      <section className="grid gap-6">
        <div className="rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-accent/80">
                Latest run
              </p>
              <h3 className="mt-2 text-xl font-semibold tracking-[-0.03em] text-foreground">
                Structured output and task metadata
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
              <div className="grid gap-3 sm:grid-cols-2">
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Provider
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {activeRun.meta.provider}
                  </p>
                </article>
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Duration
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {activeRun.meta.durationMs} ms
                  </p>
                </article>
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Cache
                  </p>
                  <p className="mt-2 text-sm font-semibold text-foreground">
                    {activeRun.meta.cached ? "Returned from cache" : "Fresh provider response"}
                  </p>
                </article>
                <article className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                    Idempotency
                  </p>
                  <p className="mt-2 break-all text-sm font-semibold text-foreground">
                    {activeRun.meta.idempotencyKey}
                  </p>
                </article>
              </div>

              {activeRun.result ? (
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    { label: "First name", value: activeRun.result.firstName },
                    { label: "Last name", value: activeRun.result.lastName },
                    { label: "Date of birth", value: activeRun.result.dob },
                    {
                      label: "Driver licence number",
                      value: activeRun.result.driverLicenceNumber,
                    },
                  ].map((field) => (
                    <article
                      className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-4"
                      key={field.label}
                    >
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted">
                        {field.label}
                      </p>
                      <p className="mt-2 text-base font-semibold text-foreground">
                        {field.value}
                      </p>
                    </article>
                  ))}
                </div>
              ) : null}

              {!activeRun.status && activeRun.errors.length > 0 ? (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-4">
                  <p className="text-sm font-semibold text-rose-700">Task error</p>
                  <p className="mt-2 text-sm leading-6 text-rose-700">
                    {activeRun.errors[0]?.message}
                  </p>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface-strong)] px-4 py-8 text-sm leading-7 text-muted">
              Submit the sample ID or your own public document URL to generate the first
              structured run.
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
                Local operator history
              </h3>
            </div>
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-muted">
              Last {MAX_RECENT_RUNS}
            </span>
          </div>

          {recentRuns.length > 0 ? (
            <div className="mt-5 overflow-hidden rounded-2xl border border-[var(--line)]">
              <table className="min-w-full divide-y divide-[var(--line)] text-left text-sm">
                <thead className="bg-[var(--surface-strong)]">
                  <tr>
                    <th className="px-4 py-3 font-semibold text-foreground">Status</th>
                    <th className="px-4 py-3 font-semibold text-foreground">Name</th>
                    <th className="px-4 py-3 font-semibold text-foreground">Cache</th>
                    <th className="px-4 py-3 font-semibold text-foreground">Time</th>
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
                      <td className="px-4 py-3 text-foreground">
                        {run.result
                          ? `${run.result.firstName} ${run.result.lastName}`
                          : "Unavailable"}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {run.meta.cached ? "Cached" : "Fresh"}
                      </td>
                      <td className="px-4 py-3 text-muted">
                        {new Date(run.meta.createdAt).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="mt-5 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface-strong)] px-4 py-8 text-sm leading-7 text-muted">
              Recent runs will appear here after the first submission. This history is kept
              in browser storage only.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
