export type NewsCoverageState = "LIVE" | "PARTIAL" | "GAP";
export type NewsSourceRole = "PRIMARY" | "DISCOVERY";
export type NewsSourceHealthState = "CURRENT" | "DELAYED" | "ATTENTION" | "PENDING";

export type NewsCoverageSource = {
  slug: string;
  label: string;
  role: NewsSourceRole;
};

export type NewsCoverageDomainDefinition = {
  slug: string;
  label: string;
  description: string;
  sources: NewsCoverageSource[];
  minimumCurrentPrimary: number;
  minimumCurrentDiscovery?: number;
  missingLayer: string;
};

// The matrix is intentionally a code-owned research contract. A domain becomes
// LIVE only when its configured evidence layers were actually checked recently;
// a source's presence in the registry alone never qualifies it as coverage.
export const newsCoverageDomains: NewsCoverageDomainDefinition[] = [
  {
    slug: "macro-policy",
    label: "MACRO & MONETARY POLICY",
    description: "Central-bank communication and macro-release context across the active developed-market desks.",
    sources: [
      { slug: "federal-reserve-board", label: "Federal Reserve Board", role: "PRIMARY" },
      { slug: "ecb-communications", label: "European Central Bank", role: "PRIMARY" },
      { slug: "bank-of-canada-communications", label: "Bank of Canada", role: "PRIMARY" },
      { slug: "reserve-bank-australia-communications", label: "Reserve Bank of Australia", role: "PRIMARY" },
    ],
    minimumCurrentPrimary: 3,
    missingLayer: "One or more official central-bank feeds need a successful refresh.",
  },
  {
    slug: "us-policy-trade",
    label: "U.S. POLICY, TARIFFS & EXPORT CONTROLS",
    description: "Executive Orders and Bureau of Industry and Security actions that can change trade, technology or supply-chain assumptions.",
    sources: [{ slug: "federal-register-risk", label: "Federal Register", role: "PRIMARY" }],
    minimumCurrentPrimary: 1,
    missingLayer: "The official Federal Register monitor has not completed successfully.",
  },
  {
    slug: "russia-ukraine",
    label: "RUSSIA–UKRAINE & EUROPEAN SANCTIONS",
    description: "Official European policy and nuclear-safety evidence, paired with a discovery layer for early incident signals.",
    sources: [
      { slug: "eu-council-communications", label: "Council of the EU", role: "PRIMARY" },
      { slug: "iaea-news", label: "International Atomic Energy Agency", role: "PRIMARY" },
      { slug: "gdelt-discovery", label: "GDELT discovery", role: "DISCOVERY" },
    ],
    minimumCurrentPrimary: 1,
    minimumCurrentDiscovery: 1,
    missingLayer: "An independent incident-discovery run is needed alongside the official policy layer.",
  },
  {
    slug: "iran-nuclear",
    label: "IRAN, NUCLEAR & MIDDLE-EAST RISK",
    description: "Official nuclear-safety context and open-web discovery for conflict, sanctions and Strait of Hormuz transmission.",
    sources: [
      { slug: "iaea-news", label: "International Atomic Energy Agency", role: "PRIMARY" },
      { slug: "gdelt-discovery", label: "GDELT discovery", role: "DISCOVERY" },
    ],
    minimumCurrentPrimary: 1,
    minimumCurrentDiscovery: 1,
    missingLayer: "The official nuclear layer needs a recent independent incident-discovery run.",
  },
  {
    slug: "energy-maritime",
    label: "ENERGY & MARITIME TRANSMISSION",
    description: "Official U.S. energy evidence and incident discovery for oil, gas, supply-chain and shipping-risk hypotheses.",
    sources: [
      { slug: "us-eia-energy", label: "U.S. Energy Information Administration", role: "PRIMARY" },
      { slug: "gdelt-discovery", label: "GDELT discovery", role: "DISCOVERY" },
    ],
    minimumCurrentPrimary: 1,
    minimumCurrentDiscovery: 1,
    missingLayer: "A current incident-discovery run is required; a dedicated authorised maritime feed remains a later addition.",
  },
  {
    slug: "china-tech",
    label: "CHINA TECHNOLOGY & TRADE",
    description: "U.S. export-control actions plus discovery coverage of Chinese technology, semiconductors and supply-chain transmission.",
    sources: [
      { slug: "federal-register-risk", label: "Federal Register", role: "PRIMARY" },
      { slug: "gdelt-discovery", label: "GDELT discovery", role: "DISCOVERY" },
    ],
    minimumCurrentPrimary: 1,
    minimumCurrentDiscovery: 1,
    missingLayer: "A current discovery run is required; a verified Chinese-side primary feed is not connected yet.",
  },
  {
    slug: "fast-social-signals",
    label: "FAST SOCIAL SIGNALS",
    description: "Watchlisted public statements from officials and market-relevant institutions, always labelled as unverified until corroborated.",
    sources: [],
    minimumCurrentPrimary: 1,
    missingLayer: "No public-account watchlist is configured. Add only named official accounts with a permitted public API or feed.",
  },
];

export type NewsCoverageSourceStatus = NewsCoverageSource & {
  status: NewsSourceHealthState;
  checkedAt?: string;
  recordsWritten?: number;
};

export type NewsCoverageDomain = Omit<NewsCoverageDomainDefinition, "minimumCurrentPrimary" | "minimumCurrentDiscovery" | "sources"> & {
  status: NewsCoverageState;
  reason: string;
  sources: NewsCoverageSourceStatus[];
};

export type NewsCoverageResponse = {
  generatedAt: string;
  domains: NewsCoverageDomain[];
};
