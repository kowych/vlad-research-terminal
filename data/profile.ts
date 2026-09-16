export type Experience = {
  role: string;
  company: string;
  period: string;
  summary: string;
  highlights: string[];
};

export const experiences: Experience[] = [
  {
    role: "Data Quality Manager / Data Analyst",
    company: "Rubix sp. z o.o. · Remote",
    period: "JAN 2023 — PRESENT",
    summary: "Data professional in an international product-information environment, improving the completeness, reliability and commercial usability of a large e-commerce catalogue.",
    highlights: [
      "Collaborate with data engineers, data scientists and cross-functional stakeholders to improve the quality and availability of product data.",
      "Design data-quality improvements that increase catalogue coverage, product visibility and the commercial readiness of listings, supporting wider commercial reach and sales.",
      "Use SQL, Databricks, Excel, Power Query, VBA and SAP PIM to investigate data issues, standardise records and automate recurring controls.",
      "Translate stakeholder queries into traceable fixes, following issues through from diagnosis to verified catalogue updates.",
    ],
  },
  {
    role: "Global Benefits Junior Analyst",
    company: "Aon · Kraków, Poland",
    period: "AUG 2021 — DEC 2022",
    summary: "Analysed multi-market employee-benefits data to support client reporting, operational decisions and recurring data processes.",
    highlights: [
      "Cleaned and analysed benefits data across multiple markets for client reporting and decision support.",
      "Built recurring Excel and Microsoft Office reports and dashboards; automated repetitive reporting tasks with VBA.",
      "Acted as a day-to-day client contact for data and reporting queries.",
    ],
  },
];

export const coreStack = [
  "SQL", "Databricks", "Python", "Excel", "Power Query", "VBA", "SAP PIM", "Data Quality & Governance", "Data Management", "Process Automation",
];

export const languages = ["English · C1", "Polish · C2", "Russian · Native", "Belarusian · Native"];
