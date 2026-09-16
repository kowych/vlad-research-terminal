import Link from "next/link";
import { notFound } from "next/navigation";
import CountryMacroDesk from "@/components/CountryMacroDesk";
import PageHeader from "@/components/PageHeader";
import EmptyArchive from "@/components/EmptyArchive";
import { countries, getCountryDeskStatus } from "@/data/countries";

function statusLabel(status: ReturnType<typeof getCountryDeskStatus>) {
  if (status === "live") return "LIVE DATA";
  if (status === "partial") return "PARTIAL DATA";
  return "INTEGRATION QUEUE";
}

function deskDescription(status: ReturnType<typeof getCountryDeskStatus>) {
  if (status === "live") return undefined;
  if (status === "partial") {
    return "Available observations are shown with their original period and vintage. This desk is not yet a complete current macro assessment.";
  }
  return "A country profile exists, but it will not be published as live until every displayed series passes source and freshness validation.";
}

function partialCoverageNote(iso2: string) {
  if (iso2 === "JP") {
    return "Current Bank of Japan call-rate data is available. Other displayed Japan series remain archival until their official-source replacements pass freshness checks.";
  }
  if (iso2 === "GB") {
    return "Current Bank Rate data is available from the Bank of England. Other displayed UK series remain annual World Bank baseline data until their official-source connectors pass freshness checks.";
  }
  if (iso2 === "FR" || iso2 === "DE") {
    return "Current ECB main refinancing operations data is available. Other displayed national series remain annual World Bank baseline data until their official-source connectors pass freshness checks.";
  }
  return "Comparable annual World Bank baseline data is available. High-frequency central-bank, inflation and labour connectors will be added before this desk is labelled live.";
}

export function generateStaticParams() {
  return countries.map((country) => ({ country: country.iso2.toLowerCase() }));
}

export default async function CountryMacroPage({ params }: { params: Promise<{ country: string }> }) {
  const { country: slug } = await params;
  const country = countries.find((item) => item.iso2.toLowerCase() === slug.toLowerCase());

  if (!country) notFound();

  const status = getCountryDeskStatus(country.iso2);

  return (
    <section className="page-shell">
      <Link href="/macro" className="back-link">← MACRO COUNTRY REGISTRY</Link>
      <PageHeader
        number={country.iso2}
        eyebrow={`${country.name.toUpperCase()} · ${statusLabel(status)}`}
        title={country.name}
        description={deskDescription(status)}
      />
      <section className="country-facts">
        <div className="country-fact-compact"><p>CAPITAL</p><strong>{country.capital}</strong></div>
        <div className="country-fact-compact"><p>CURRENCY</p><strong>{country.currency}</strong></div>
        <div><p>CENTRAL BANK</p><a href={country.centralBankUrl} target="_blank" rel="noreferrer">{country.centralBank} ↗</a></div>
        <div><p>ECONOMIC DRIVERS</p><strong>{country.economicDrivers.join(" · ")}</strong></div>
      </section>
      <div className="mt-10">
        {status === "planned" ? (
          <EmptyArchive
            label="LIVE DATA NOT PUBLISHED"
            detail="The UI and data model are ready. The next step is an official-source connector and a freshness check for every series."
          />
        ) : (
          <>
            {status === "partial" && <section className="data-notice"><p>PARTIAL COVERAGE</p><span>{partialCoverageNote(country.iso2)}</span></section>}
            <CountryMacroDesk key={country.iso2} country={country.iso2} />
          </>
        )}
      </div>
    </section>
  );
}
