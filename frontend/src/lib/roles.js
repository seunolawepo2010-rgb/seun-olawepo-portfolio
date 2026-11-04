const G = (roles, labs, cats, exp) => roles.map((r) => ({ role: r, labs, cats, exp }));

export const CAREER_PATHS = [
  ...G(["Senior GRC Analyst", "Cybersecurity GRC Analyst", "IT Risk & Controls Analyst", "Technology Risk Analyst", "Security Compliance Analyst"], ["irm", "cyber", "audit", "vendor"], ["Cybersecurity GRC", "ServiceNow", "Security Operations"], ["loandepot", "tspi-usda", "fidelity"]),
  ...G(["IT Audit Analyst"], ["audit", "irm"], ["Cybersecurity GRC", "Enterprise Tools"], ["fidelity", "tspi-usda"]),
  ...G(["Third-Party Risk Analyst", "Vendor Risk Analyst"], ["vendor", "irm"], ["Cybersecurity GRC"], ["loandepot", "fidelity"]),
  ...G(["AI Governance Analyst", "AI Risk Analyst", "AI Security Governance Analyst"], ["aigov", "agents"], ["AI Governance", "AI Agent Management", "Cybersecurity GRC"], ["loandepot", "tspi-usda"]),
  ...G(["AI Agent Manager", "AI Operations Manager", "AI Automation Manager", "AI Program Manager"], ["agents", "aigov", "pm"], ["AI Agent Management", "AI Governance", "Project & Agile Delivery"], ["loandepot", "unitedhealth"]),
  ...G(["ServiceNow IRM/GRC Specialist", "ServiceNow Administrator", "ServiceNow Developer"], ["irm", "servicenow"], ["ServiceNow", "Cybersecurity GRC"], ["loandepot", "tspi-usda", "fidelity"]),
  ...G(["IT Project Manager", "Program Manager", "Scrum Master", "Release Train Engineer", "Product Owner", "Product Manager", "Business Analyst"], ["pm", "safe"], ["Project & Agile Delivery", "Enterprise Tools"], ["unitedhealth", "mastercard", "att"]),
  ...G(["Incident Response Analyst", "BCDR Specialist"], ["ir", "cyber"], ["Security Operations", "Cybersecurity GRC"], ["loandepot", "tspi-usda"]),
];
