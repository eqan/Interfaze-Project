import { BackendDomainTable } from "@/components/backend-domain-table";
import { HeroBanner } from "@/components/hero-banner";
import { InfoCard } from "@/components/info-card";
import { SectionShell } from "@/components/section-shell";
import { siteConfig } from "@/config/site";

export default function BackendApiPage() {
  return (
    <section className="flex w-full flex-col gap-10">
      <HeroBanner
        actions={[
          { href: "/architecture", label: "Review boundaries" },
          { href: "/playbook", label: "Open workflow", variant: "secondary" },
        ]}
        asideDescription="A practical product shell needs concrete UI primitives too: tables, pagination, selects, dialogs, inputs, and predictable state handling around them."
        asideTitle="Practical UI posture"
        description="The frontend now owns the extraction workflow in its server layer while keeping auth requests, cache decisions, and route composition predictable."
        eyebrow="Integration"
        heading="Keep the API edge practical, typed, and hard to misuse."
        metrics={[
          {
            value: "1",
            label: "Request layer",
            note: "Auth and future modules should flow through one shared API boundary.",
          },
          {
            value: "4",
            label: "Cache modes",
            note: "Fresh, short-lived, cacheable, and browser-sticky are enough to classify most product data.",
          },
          {
            value: "0",
            label: "Secret storage copies",
            note: "Sensitive auth state should not spread across multiple browser persistence layers.",
          },
        ]}
      />

      <SectionShell
        description="These integration surfaces give new modules one consistent place to plug into the frontend."
        eyebrow="Foundations"
        title="A few contracts should carry most of the app."
      >
        <div className="grid gap-6 xl:grid-cols-3">
          {siteConfig.integrations.map((item, index) => (
            <InfoCard
              key={item.title}
              description={item.description}
              kicker={`Surface 0${index + 1}`}
              title={item.title}
            />
          ))}
        </div>
      </SectionShell>

      <SectionShell
        description="These backend domains already map cleanly to product modules inside the protected shell."
        eyebrow="Backend modules"
        title="Build on real contracts instead of inventing one-off route logic."
      >
        <BackendDomainTable domains={siteConfig.backendDomains} />
      </SectionShell>

      <SectionShell
        description="Frontend cache rules should be explicit enough that contributors do not have to guess whether data belongs in live fetches, revalidation, or browser storage."
        eyebrow="Caching"
        title="Use a small set of browser-freshness decisions."
      >
        <div className="grid gap-5 xl:grid-cols-2">
          {siteConfig.cacheScenarios.map((scenario) => (
            <article
              key={scenario.title}
              className="rounded-3xl border border-[var(--line)] bg-[var(--surface)] p-6 shadow-[0_14px_40px_rgba(2,6,23,0.12)]"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h3 className="text-lg font-semibold text-foreground">{scenario.title}</h3>
                <span className="rounded-2xl border border-[var(--line)] bg-[var(--surface-strong)] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-accent/75">
                  {scenario.recommendation}
                </span>
              </div>
              <p className="mt-4 text-sm leading-7 text-muted">{scenario.description}</p>
            </article>
          ))}
        </div>
      </SectionShell>
    </section>
  );
}
