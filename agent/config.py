import os
from dotenv import load_dotenv

# Always resolve .env relative to this file so it loads regardless of CWD
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'), override=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
TIDB_CONNECTION_STRING = os.getenv("TIDB_CONNECTION_STRING", "")

SCRAPER_DELAY = float(os.getenv("SCRAPER_DELAY", "1.5"))
MAX_COMPANIES_PER_COUNTRY = int(os.getenv("MAX_COMPANIES_PER_COUNTRY", "0"))  # 0 = unlimited
MIN_FIT_SCORE = int(os.getenv("MIN_FIT_SCORE", "5"))

# No per-country caps — discover and analyse everything we find
COUNTRY_MAX_OVERRIDE: dict[str, int] = {}

CLAUDE_MODEL        = "claude-haiku-4-5-20251001"
CLAUDE_MODEL_STRONG = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Full geo → sub-region → country hierarchy
# Keeps db9's EMEA sub-region names (British Isles, DACH, Nordics, etc.)
# ---------------------------------------------------------------------------
GEO_REGIONS: dict[str, dict[str, list[str]]] = {
    "EMEA": {
        "British Isles":   ["United Kingdom", "Ireland"],
        "DACH":            ["Germany", "Austria", "Switzerland"],
        "Nordics":         ["Sweden", "Norway", "Denmark", "Finland", "Iceland"],
        "Benelux":         ["Netherlands", "Belgium", "Luxembourg"],
        "Baltics":         ["Estonia", "Latvia", "Lithuania"],
        "Southern Europe": ["France", "Spain", "Portugal", "Italy", "Greece", "Malta", "Cyprus"],
        "Eastern Europe":  ["Poland", "Czech Republic", "Hungary", "Romania", "Slovakia",
                            "Bulgaria", "Croatia", "Slovenia"],
        "Middle East":     ["Israel", "United Arab Emirates", "Saudi Arabia", "Qatar",
                            "Bahrain", "Kuwait", "Jordan", "Lebanon"],
        "Africa":          ["South Africa", "Nigeria", "Kenya", "Ghana", "Egypt",
                            "Morocco", "Tunisia"],
    },
    "NAMERICA": {
        "North America": ["United States", "Canada"],
        "Latin America": ["Mexico", "Brazil", "Colombia", "Argentina", "Chile"],
    },
    "APAC": {
        "East Asia":      ["Japan", "South Korea", "Taiwan", "Hong Kong"],
        "Southeast Asia": ["Singapore", "Vietnam", "Thailand", "Indonesia", "Malaysia", "Philippines"],
        "South Asia":     ["India", "Sri Lanka"],
        "Oceania":        ["Australia", "New Zealand"],
    },
}

# Compliance context injected into the Claude analyser prompt — geo-specific
GEO_COMPLIANCE: dict[str, str] = {
    "EMEA": (
        "EU GDPR: AI agents handling personal data must store it in GDPR-compliant databases; "
        "non-compliance fines reach 4% of global annual turnover. "
        "UK GDPR (post-Brexit): mirrors EU GDPR — UK companies face the same data-residency pressure. "
        "Israel Privacy Protection Law (IPPL Amendment 13): strengthened 2023; aligns closely with GDPR. "
        "UAE PDPL & DIFC/ADGM regulations: data localisation requirements for UAE-based AI products. "
        "Saudi Arabia PDPL (2022): strict data localisation; financial penalties for breaches. "
        "db9 pitch: EU-region deployment (AWS eu-central-1 / eu-west-1) satisfies data-residency "
        "requirements out of the box — no complex cross-border transfer arrangements needed."
    ),
    "NAMERICA": (
        "CCPA/CPRA (California): de-facto US privacy standard — AI products handling California "
        "residents' data must demonstrate compliant storage practices. "
        "HIPAA: healthcare AI companies face strict requirements on where PHI is stored and processed. "
        "PIPEDA / Bill C-27 (Canada): organisations must document data flows and storage locations. "
        "SOC 2 Type II: baseline expectation for any B2B SaaS storage vendor in the US market. "
        "FedRAMP: relevant for AI companies selling into US federal government. "
        "db9 pitch: zero-config serverless Postgres eliminates the need to self-manage compliant "
        "infrastructure; SOC 2-ready, scales with AI workloads, no vendor lock-in."
    ),
    "APAC": (
        "Singapore PDPA: strict requirements on personal data used in AI systems; data processors "
        "must implement technical safeguards. "
        "Thailand PDPA (2022): modelled on GDPR; applies to any processor handling Thai residents' data. "
        "Japan APPI (2022 update): extraterritorial reach; cross-border data transfers require safeguards. "
        "India DPDP Act 2023: significant penalties; AI companies must document storage of personal data. "
        "Australia Privacy Act: under review for GDPR-style overhaul; organisations should prepare now. "
        "China PIPL: very strict data localisation; position db9 for non-China APAC use cases. "
        "db9 pitch: regional data residency (deploy in ap-southeast-1, ap-northeast-1, ap-south-1) "
        "addresses data sovereignty concerns that are the #1 blocker for APAC enterprise AI deals."
    ),
}

# ---------------------------------------------------------------------------
# Flat lookups derived from GEO_REGIONS
# ---------------------------------------------------------------------------

# country -> sub-region (e.g. "Sweden" -> "Nordics")
COUNTRY_REGION: dict[str, str] = {
    country: sub_region
    for geo, sub_regions in GEO_REGIONS.items()
    for sub_region, countries in sub_regions.items()
    for country in countries
}

# country -> geo (e.g. "Sweden" -> "EMEA")
COUNTRY_GEO: dict[str, str] = {
    country: geo
    for geo, sub_regions in GEO_REGIONS.items()
    for sub_region, countries in sub_regions.items()
    for country in countries
}

# Backward-compat aliases
EMEA_REGIONS: dict[str, list[str]] = GEO_REGIONS["EMEA"]
ALL_REGIONS = GEO_REGIONS  # legacy name used by dashboard


def all_countries(geo: str | None = None) -> list[str]:
    """Return all countries for a given geo, or all geos if geo is None."""
    if geo:
        return [
            country
            for sub_regions in GEO_REGIONS.get(geo.upper(), {}).values()
            for country in sub_regions
        ]
    return [
        country
        for sub_regions_map in GEO_REGIONS.values()
        for sub_regions in sub_regions_map.values()
        for country in sub_regions
    ]
