import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import { coreStack, experiences, languages } from "@/data/profile";

export const metadata = { title: "About" };

export default function AboutPage() {
  return <section className="page-shell">
    <PageHeader
      number="05"
      eyebrow="CV · DATA · MARKETS"
      title="Uladzislau Muklanovich"
      description="Data Quality Manager developing a research practice in macroeconomics, market structure and financial data."
      showDivider={false}
    />

    <section className="cv-profile">
      <p className="article-label">PROFILE</p>
      <p>I am a data professional with 4+ years of experience working with large, complex datasets in international environments. My work combines data quality, data management, analytical problem-solving and process automation with a focus on making data commercially usable and decision-ready.</p>
      <p>I am intentionally developing toward macro research, financial-data analysis and systematic market research. This site is the working record of that direction: <Link href="/macro">live macro coverage</Link>, <Link href="/research">research</Link> and a transparent evidence process rather than unsupported market opinions.</p>
    </section>

    <div className="cv-layout">
      <div className="cv-main">
        <section className="cv-section">
          <p className="article-label">MARKET RESEARCH & TRADING APPROACH</p>
          <p className="cv-copy">I apply a swing-trading approach grounded in macroeconomic analysis. I form directional views by studying how capital moves across economies, the policy stance of major central banks - particularly the Federal Reserve - and changes in global liquidity, growth and risk appetite.</p>
          <p className="cv-copy">Risk management is central to the process. Technical analysis is used for trade execution, position management and exit discipline, while macro reasoning defines the scenario, catalysts and invalidation. I have more than two years of hands-on market experience and remain focused on increasing the depth, discipline and professional quality of this practice.</p>
        </section>

        <section className="cv-section">
          <p className="article-label">EXPERIENCE</p>
          {experiences.map((experience) => <article className="cv-experience" key={experience.role}>
            <div className="cv-experience-heading"><div><h2>{experience.role}</h2><p>{experience.company}</p></div><span>{experience.period}</span></div>
            <p className="cv-summary">{experience.summary}</p>
            <ul>{experience.highlights.map((highlight) => <li key={highlight}>{highlight}</li>)}</ul>
          </article>)}
        </section>

        <section className="cv-section">
          <p className="article-label">COLLABORATION</p>
          <p className="cv-copy">Open to collaboration, research opportunities and roles at the intersection of data, financial markets, macroeconomics and risk. My long-term objective is continuous professional growth and deeper expertise in these fields.</p>
        </section>
      </div>

      <aside className="cv-sidebar">
        <section className="cv-section">
          <p className="article-label">CORE STACK</p>
          <ul className="cv-tag-list">{coreStack.map((skill) => <li key={skill}>{skill}</li>)}</ul>
        </section>
        <section className="cv-section">
          <p className="article-label">EDUCATION</p>
          <h2>AGH University of Science and Technology</h2>
          <p className="cv-meta">KRAKÓW · 2018 — 2023</p>
          <p className="cv-copy">Computer Science and Econometrics.</p>
          <p className="cv-diploma">Diploma: <em>Visual Data Analysis using Qlik</em>.</p>
        </section>
        <section className="cv-section">
          <p className="article-label">LANGUAGES</p>
          <ul className="cv-plain-list">{languages.map((language) => <li key={language}>{language}</li>)}</ul>
        </section>
      </aside>
    </div>
  </section>;
}
