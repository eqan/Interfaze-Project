import NextLink from "next/link";

import { ExtractionConsole } from "@/components/extraction-console";
import { SectionShell } from "@/components/section-shell";
import { siteConfig } from "@/config/site";

export default function HomePage() {
  return (
    <section className="flex w-full flex-col gap-8">
      <section className="rounded-[28px] border border-[var(--line)] bg-[var(--surface)] p-6 sm:p-8">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-accent/75">
              Operator console
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-foreground sm:text-4xl">
              Run the workflow you would actually demo in a build round.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-6 text-muted sm:text-base">
              The main route now behaves like a simple internal tool: submit one typed
              extraction task, review the result, and inspect cache and retry context without
              leaving the protected workspace.
            </p>
          </div>

            <div className="grid gap-3 sm:grid-cols-2 xl:w-[360px]">
            {siteConfig.quickLinks.slice(0, 2).map((link) => (
              <NextLink
                key={link.href}
                className="rounded-xl border border-[var(--line)] bg-[var(--surface-strong)] px-4 py-4 transition-colors hover:bg-slate-50"
                href={link.href}
              >
                <p className="text-sm font-semibold text-foreground">{link.label}</p>
                <p className="mt-2 text-sm leading-6 text-muted">{link.description}</p>
              </NextLink>
            ))}
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {siteConfig.proofMetrics.map((metric) => (
            <article
              key={metric.label}
              className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] p-5"
            >
              <p className="text-2xl font-semibold tracking-[-0.03em] text-foreground">
                {metric.value}
              </p>
              <p className="mt-2 text-xs font-semibold uppercase tracking-[0.22em] text-accent/75">
                {metric.label}
              </p>
              <p className="mt-3 text-sm leading-6 text-muted">{metric.note}</p>
            </article>
          ))}
        </div>
      </section>

      <SectionShell
        description="The most important route should now do real work instead of only describing what the app could become."
        eyebrow="Task Surface"
        title="A practical extraction workflow with typed output."
      >
        <ExtractionConsole />
      </SectionShell>

      <SectionShell
        description="These notes keep the product surface grounded in the specific delivery patterns you want to explain during the interview."
        eyebrow="Build Notes"
        title="Execution priorities and browser-state decisions."
      >
        <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-accent/75">
                Execution posture
              </p>
              <span className="rounded-full border border-[var(--line)] bg-[var(--surface-strong)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                Interview-ready
              </span>
            </div>
            <div className="mt-5 grid gap-3">
              {[
                {
                  title: "Typed task contract",
                  status: "Now",
                  description:
                    "The app should accept one clear task shape, validate it once, and return a structured result or a structured failure.",
                },
                {
                  title: "Safe retries",
                  status: "Live",
                  description:
                    "The same idempotency key should make repeated submissions predictable instead of spawning ambiguous duplicate work.",
                },
                {
                  title: "Visible operator states",
                  status: "Required",
                  description:
                    "Loading, success, cached responses, and failures should be obvious from the page without opening logs first.",
                },
              ].map((track) => (
                <div
                  key={track.title}
                  className="rounded-xl border border-[var(--line)] bg-[var(--surface-strong)] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-base font-semibold text-foreground">{track.title}</h3>
                    <span className="rounded-full border border-[var(--line)] bg-[var(--surface)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                      {track.status}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted">{track.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-6">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-accent/75">
                Cache posture
              </p>
              <span className="rounded-full border border-[var(--line)] bg-[var(--surface-strong)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                Browser-aware
              </span>
            </div>
            <div className="mt-5 grid gap-3">
              {siteConfig.cacheScenarios.map((scenario) => (
                <article
                  key={scenario.title}
                  className="rounded-xl border border-[var(--line)] bg-[var(--surface-strong)] p-4"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <h3 className="text-base font-semibold text-foreground">{scenario.title}</h3>
                    <span className="rounded-full border border-[var(--line)] bg-[var(--surface)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-muted">
                      {scenario.recommendation}
                    </span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted">{scenario.description}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </SectionShell>
    </section>
  );
}
