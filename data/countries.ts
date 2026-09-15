export type Country = {
  iso2: string;
  name: string;
  capital: string;
  currency: string;
  centralBank: string;
  economicDrivers: string[];
  wikidataId: string;
  officialStatisticsUrl: string;
  centralBankUrl: string;
  initialCoverage: "CORE";
};

// Structural facts are seeded from Wikidata and must be attributed in the UI.
// Macroeconomic observations are deliberately not stored here: they are sourced
// and versioned in PostgreSQL through the data-platform schema.
export const countries: Country[] = [
  { iso2: "US", name: "United States", capital: "Washington, D.C.", currency: "USD", centralBank: "Federal Reserve", economicDrivers: ["Consumer", "Technology", "Financial markets", "Energy"], wikidataId: "Q30", officialStatisticsUrl: "https://www.bls.gov/", centralBankUrl: "https://www.federalreserve.gov/", initialCoverage: "CORE" },
  { iso2: "IR", name: "Iran", capital: "Tehran", currency: "IRR", centralBank: "Central Bank of Iran", economicDrivers: ["Hydrocarbons", "Regional trade", "Shipping routes"], wikidataId: "Q794", officialStatisticsUrl: "https://www.amar.org.ir/english", centralBankUrl: "https://www.cbi.ir/", initialCoverage: "CORE" },
  { iso2: "GB", name: "United Kingdom", capital: "London", currency: "GBP", centralBank: "Bank of England", economicDrivers: ["Financial services", "Services", "Energy"], wikidataId: "Q145", officialStatisticsUrl: "https://www.ons.gov.uk/", centralBankUrl: "https://www.bankofengland.co.uk/", initialCoverage: "CORE" },
  { iso2: "FR", name: "France", capital: "Paris", currency: "EUR", centralBank: "European Central Bank", economicDrivers: ["Services", "Aerospace", "Luxury goods", "Agriculture"], wikidataId: "Q142", officialStatisticsUrl: "https://www.insee.fr/en/accueil", centralBankUrl: "https://www.ecb.europa.eu/", initialCoverage: "CORE" },
  { iso2: "DE", name: "Germany", capital: "Berlin", currency: "EUR", centralBank: "European Central Bank", economicDrivers: ["Manufacturing", "Autos", "Chemicals", "Capital goods"], wikidataId: "Q183", officialStatisticsUrl: "https://www.destatis.de/EN/Home/_node.html", centralBankUrl: "https://www.ecb.europa.eu/", initialCoverage: "CORE" },
  { iso2: "UA", name: "Ukraine", capital: "Kyiv", currency: "UAH", centralBank: "National Bank of Ukraine", economicDrivers: ["Agriculture", "Metals", "Defence", "Logistics"], wikidataId: "Q212", officialStatisticsUrl: "https://ukrstat.gov.ua/", centralBankUrl: "https://bank.gov.ua/", initialCoverage: "CORE" },
  { iso2: "RU", name: "Russia", capital: "Moscow", currency: "RUB", centralBank: "Bank of Russia", economicDrivers: ["Hydrocarbons", "Metals", "Defence industry"], wikidataId: "Q159", officialStatisticsUrl: "https://rosstat.gov.ru/", centralBankUrl: "https://www.cbr.ru/eng/", initialCoverage: "CORE" },
  { iso2: "AU", name: "Australia", capital: "Canberra", currency: "AUD", centralBank: "Reserve Bank of Australia", economicDrivers: ["Iron ore", "Coal", "LNG", "Agriculture"], wikidataId: "Q408", officialStatisticsUrl: "https://www.abs.gov.au/", centralBankUrl: "https://www.rba.gov.au/", initialCoverage: "CORE" },
  { iso2: "CA", name: "Canada", capital: "Ottawa", currency: "CAD", centralBank: "Bank of Canada", economicDrivers: ["Energy", "US trade", "Housing", "Metals"], wikidataId: "Q16", officialStatisticsUrl: "https://www.statcan.gc.ca/en/start", centralBankUrl: "https://www.bankofcanada.ca/", initialCoverage: "CORE" },
  { iso2: "NZ", name: "New Zealand", capital: "Wellington", currency: "NZD", centralBank: "Reserve Bank of New Zealand", economicDrivers: ["Dairy", "Agriculture", "Tourism"], wikidataId: "Q664", officialStatisticsUrl: "https://www.stats.govt.nz/", centralBankUrl: "https://www.rbnz.govt.nz/", initialCoverage: "CORE" },
  { iso2: "CN", name: "China", capital: "Beijing", currency: "CNY", centralBank: "People's Bank of China", economicDrivers: ["Manufacturing", "Exports", "Property", "Technology"], wikidataId: "Q148", officialStatisticsUrl: "https://www.stats.gov.cn/english/", centralBankUrl: "http://www.pbc.gov.cn/en/", initialCoverage: "CORE" },
  { iso2: "JP", name: "Japan", capital: "Tokyo", currency: "JPY", centralBank: "Bank of Japan", economicDrivers: ["Autos", "Machinery", "Technology", "Services"], wikidataId: "Q17", officialStatisticsUrl: "https://www.stat.go.jp/english/", centralBankUrl: "https://www.boj.or.jp/en/", initialCoverage: "CORE" },
  { iso2: "IT", name: "Italy", capital: "Rome", currency: "EUR", centralBank: "European Central Bank", economicDrivers: ["Manufacturing", "Tourism", "Machinery", "Food and luxury"], wikidataId: "Q38", officialStatisticsUrl: "https://www.istat.it/en/", centralBankUrl: "https://www.ecb.europa.eu/", initialCoverage: "CORE" },
  { iso2: "ES", name: "Spain", capital: "Madrid", currency: "EUR", centralBank: "European Central Bank", economicDrivers: ["Services", "Tourism", "Autos", "Renewable energy"], wikidataId: "Q29", officialStatisticsUrl: "https://www.ine.es/en/", centralBankUrl: "https://www.ecb.europa.eu/", initialCoverage: "CORE" },
  { iso2: "CH", name: "Switzerland", capital: "Bern", currency: "CHF", centralBank: "Swiss National Bank", economicDrivers: ["Financial services", "Pharmaceuticals", "Precision manufacturing", "Trade"], wikidataId: "Q39", officialStatisticsUrl: "https://www.bfs.admin.ch/bfs/en/home.html", centralBankUrl: "https://www.snb.ch/", initialCoverage: "CORE" },
  { iso2: "NO", name: "Norway", capital: "Oslo", currency: "NOK", centralBank: "Norges Bank", economicDrivers: ["Oil and gas", "Shipping", "Seafood", "Hydropower"], wikidataId: "Q20", officialStatisticsUrl: "https://www.ssb.no/en", centralBankUrl: "https://www.norges-bank.no/en/", initialCoverage: "CORE" },
  { iso2: "SE", name: "Sweden", capital: "Stockholm", currency: "SEK", centralBank: "Sveriges Riksbank", economicDrivers: ["Manufacturing", "Technology", "Exports", "Services"], wikidataId: "Q34", officialStatisticsUrl: "https://www.scb.se/en/", centralBankUrl: "https://www.riksbank.se/en-gb/", initialCoverage: "CORE" },
  { iso2: "TR", name: "Turkey", capital: "Ankara", currency: "TRY", centralBank: "Central Bank of the Republic of Türkiye", economicDrivers: ["Manufacturing", "Tourism", "Construction", "Regional trade"], wikidataId: "Q43", officialStatisticsUrl: "https://data.tuik.gov.tr/", centralBankUrl: "https://www.tcmb.gov.tr/wps/wcm/connect/EN/TCMB+EN/Main+Menu/", initialCoverage: "CORE" },
  { iso2: "IN", name: "India", capital: "New Delhi", currency: "INR", centralBank: "Reserve Bank of India", economicDrivers: ["Services", "Manufacturing", "Digital economy", "Domestic demand"], wikidataId: "Q668", officialStatisticsUrl: "https://www.mospi.gov.in/", centralBankUrl: "https://www.rbi.org.in/", initialCoverage: "CORE" },
  { iso2: "KR", name: "South Korea", capital: "Seoul", currency: "KRW", centralBank: "Bank of Korea", economicDrivers: ["Semiconductors", "Autos", "Shipbuilding", "Exports"], wikidataId: "Q884", officialStatisticsUrl: "https://kostat.go.kr/anse/", centralBankUrl: "https://www.bok.or.kr/eng/main/main.do", initialCoverage: "CORE" },
  { iso2: "PL", name: "Poland", capital: "Warsaw", currency: "PLN", centralBank: "Narodowy Bank Polski", economicDrivers: ["Manufacturing", "EU trade", "Services", "Domestic demand"], wikidataId: "Q36", officialStatisticsUrl: "https://stat.gov.pl/en/", centralBankUrl: "https://nbp.pl/en/", initialCoverage: "CORE" },
];

// A country becomes live only after every displayed series passes a freshness
// check against its intended source of truth. Raw exploratory imports alone do
// not qualify it for publication.
export type CountryDeskStatus = "live" | "partial" | "planned";

export const countryDeskStatus: Record<string, CountryDeskStatus> = {
  US: "live",
  AU: "live",
  FR: "live",
  DE: "live",
  IT: "live",
  ES: "live",
  JP: "partial",
  IR: "partial", GB: "partial", UA: "partial",
  RU: "partial", CA: "partial", NZ: "partial", CN: "partial",
  CH: "partial", NO: "partial", SE: "partial", TR: "partial", IN: "partial", KR: "partial",
  PL: "partial",
};

export function getCountryDeskStatus(iso2: string): CountryDeskStatus {
  return countryDeskStatus[iso2] ?? "planned";
}
