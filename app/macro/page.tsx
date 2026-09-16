import PageHeader from "@/components/PageHeader";
import CoverageDashboard from "@/components/CoverageDashboard";
import GlobalMacroCalendar from "@/components/GlobalMacroCalendar";
import MacroGlobe from "@/components/MacroGlobe";
import GlobalRiskTape from "@/components/GlobalRiskTape";
import NewsCoverageMatrix from "@/components/NewsCoverageMatrix";

export const metadata = { title: "Macro" };

export default function MacroPage() {
  return <section className="page-shell">
    <PageHeader
      number="04"
      eyebrow="MACRO COUNTRY REGISTRY"
      title="Macro"
      description="The initial coverage universe is a deliberately small set of economies that matter to the active macro framework."
    />
    <MacroGlobe />
    <GlobalRiskTape />
    <GlobalMacroCalendar />
    <NewsCoverageMatrix />
    <CoverageDashboard />
  </section>;
}
