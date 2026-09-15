import { ExtractionConsole } from "@/components/extraction-console";
import { SectionShell } from "@/components/section-shell";
import { WebExtractConsole } from "@/components/web-extract-console";

export default function HomePage() {
  return (
    <section className="flex w-full flex-col gap-8">
      <section className="rounded-[28px] border border-[var(--line)] bg-[var(--surface)] p-6 sm:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-accent/75">
          Operator console
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-foreground sm:text-4xl">
          Extract structured data from one public page.
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-muted sm:text-base">
          Submit a public https URL and a short prompt. The workspace downloads the HTML,
          plans extract commands, and returns JSON without sending the live page through
          an LLM scraper.
        </p>
      </section>

      <SectionShell
        description="One URL, one prompt, typed JSON back. Access walls and empty matches fail clearly instead of inventing values."
        eyebrow="Page Extract"
        title="Local HTML fetch with command-based extraction."
      >
        <WebExtractConsole />
      </SectionShell>

      <SectionShell
        description="Keep the document extraction path available for ID parsing on a public image URL."
        eyebrow="Document Extract"
        title="Typed ID extraction remains on this workspace."
      >
        <ExtractionConsole />
      </SectionShell>
    </section>
  );
}
