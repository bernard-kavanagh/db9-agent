"""
Company discovery: finds AI/tech companies in each country.

Strategy:
1. Scrape curated startup/tech directories per country (eu-startups.com, f6s.com, etc.)
2. Ask Claude to augment with known AI companies per country (always supplement for better ICP targeting)
"""
import json
from urllib.parse import quote_plus

import anthropic

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_COMPANIES_PER_COUNTRY, COUNTRY_MAX_OVERRIDE, GEO_COMPLIANCE
from .scraper import extract_company_cards, scrape_text

# ---------------------------------------------------------------------------
# Directory sources per country
# ---------------------------------------------------------------------------
DIRECTORY_SOURCES: dict[str, list[str]] = {
    # ── EMEA — British Isles ─────────────────────────────────────────────
    "United Kingdom": [
        "https://www.f6s.com/companies/artificial-intelligence/gb/co",
        "https://eu-startups.com/directory/?country=United+Kingdom&category=Artificial+Intelligence",
    ],
    "Ireland": [
        "https://www.f6s.com/companies/artificial-intelligence/ie/co",
        "https://eu-startups.com/directory/?country=Ireland&category=Artificial+Intelligence",
    ],
    # ── DACH ─────────────────────────────────────────────────────────────
    "Germany": [
        "https://www.f6s.com/companies/artificial-intelligence/de/co",
        "https://eu-startups.com/directory/?country=Germany&category=Artificial+Intelligence",
    ],
    "Austria": [
        "https://www.f6s.com/companies/artificial-intelligence/at/co",
    ],
    "Switzerland": [
        "https://www.f6s.com/companies/artificial-intelligence/ch/co",
    ],
    # ── Nordics ──────────────────────────────────────────────────────────
    "Sweden": [
        "https://www.f6s.com/companies/artificial-intelligence/se/co",
        "https://eu-startups.com/directory/?country=Sweden&category=Artificial+Intelligence",
    ],
    "Norway": [
        "https://www.f6s.com/companies/artificial-intelligence/no/co",
    ],
    "Denmark": [
        "https://www.f6s.com/companies/artificial-intelligence/dk/co",
    ],
    "Finland": [
        "https://www.f6s.com/companies/artificial-intelligence/fi/co",
    ],
    "Iceland": [
        "https://www.f6s.com/companies/artificial-intelligence/is/co",
    ],
    # ── Benelux ──────────────────────────────────────────────────────────
    "Netherlands": [
        "https://www.f6s.com/companies/artificial-intelligence/nl/co",
        "https://eu-startups.com/directory/?country=Netherlands&category=Artificial+Intelligence",
    ],
    "Belgium": [
        "https://www.f6s.com/companies/artificial-intelligence/be/co",
    ],
    "Luxembourg": [
        "https://www.f6s.com/companies/artificial-intelligence/lu/co",
    ],
    # ── Baltics ──────────────────────────────────────────────────────────
    "Estonia": [
        "https://www.f6s.com/companies/artificial-intelligence/ee/co",
    ],
    "Latvia": [
        "https://www.f6s.com/companies/artificial-intelligence/lv/co",
    ],
    "Lithuania": [
        "https://www.f6s.com/companies/artificial-intelligence/lt/co",
    ],
    # ── Southern Europe ───────────────────────────────────────────────────
    "France": [
        "https://www.f6s.com/companies/artificial-intelligence/fr/co",
        "https://eu-startups.com/directory/?country=France&category=Artificial+Intelligence",
    ],
    "Spain": [
        "https://www.f6s.com/companies/artificial-intelligence/es/co",
        "https://eu-startups.com/directory/?country=Spain&category=Artificial+Intelligence",
    ],
    "Portugal": [
        "https://www.f6s.com/companies/artificial-intelligence/pt/co",
    ],
    "Italy": [
        "https://www.f6s.com/companies/artificial-intelligence/it/co",
        "https://eu-startups.com/directory/?country=Italy&category=Artificial+Intelligence",
    ],
    "Greece": [
        "https://www.f6s.com/companies/artificial-intelligence/gr/co",
    ],
    "Malta": [],
    "Cyprus": [],
    # ── Eastern Europe ────────────────────────────────────────────────────
    "Poland": [
        "https://www.f6s.com/companies/artificial-intelligence/pl/co",
        "https://eu-startups.com/directory/?country=Poland&category=Artificial+Intelligence",
    ],
    "Czech Republic": [
        "https://www.f6s.com/companies/artificial-intelligence/cz/co",
    ],
    "Hungary": [
        "https://www.f6s.com/companies/artificial-intelligence/hu/co",
    ],
    "Romania": [
        "https://www.f6s.com/companies/artificial-intelligence/ro/co",
    ],
    "Slovakia": [],
    "Bulgaria": [],
    "Croatia": [],
    "Slovenia": [],
    # ── Middle East ───────────────────────────────────────────────────────
    "Israel": [
        "https://www.f6s.com/companies/artificial-intelligence/il/co",
        "https://www.start-up.co.il/en",
    ],
    "United Arab Emirates": [
        "https://www.f6s.com/companies/artificial-intelligence/ae/co",
        "https://www.magnitt.com/startups/artificial-intelligence",
    ],
    "Saudi Arabia": [
        "https://www.f6s.com/companies/artificial-intelligence/sa/co",
    ],
    "Qatar": [],
    "Bahrain": [],
    "Kuwait": [],
    "Jordan": [],
    "Lebanon": [],
    # ── Africa ────────────────────────────────────────────────────────────
    "South Africa": [
        "https://www.f6s.com/companies/artificial-intelligence/za/co",
    ],
    "Nigeria": [
        "https://www.f6s.com/companies/artificial-intelligence/ng/co",
    ],
    "Kenya": [
        "https://www.f6s.com/companies/artificial-intelligence/ke/co",
    ],
    "Ghana": [],
    "Egypt": [
        "https://www.f6s.com/companies/artificial-intelligence/eg/co",
    ],
    "Morocco": [],
    "Tunisia": [],
    # ── NAMERICA ─────────────────────────────────────────────────────────
    "United States": [
        "https://www.f6s.com/companies/artificial-intelligence/us/co",
        "https://builtin.com/companies/type/artificial-intelligence-companies",
    ],
    "Canada": [
        "https://www.f6s.com/companies/artificial-intelligence/ca/co",
    ],
    "Mexico": [
        "https://www.f6s.com/companies/artificial-intelligence/mx/co",
    ],
    "Brazil": [
        "https://www.f6s.com/companies/artificial-intelligence/br/co",
    ],
    "Colombia": [
        "https://www.f6s.com/companies/artificial-intelligence/co/co",
    ],
    "Argentina": [
        "https://www.f6s.com/companies/artificial-intelligence/ar/co",
    ],
    "Chile": [
        "https://www.f6s.com/companies/artificial-intelligence/cl/co",
    ],
    # ── APAC ─────────────────────────────────────────────────────────────
    "Japan": [
        "https://www.f6s.com/companies/artificial-intelligence/jp/co",
    ],
    "South Korea": [
        "https://www.f6s.com/companies/artificial-intelligence/kr/co",
    ],
    "Taiwan": [
        "https://www.f6s.com/companies/artificial-intelligence/tw/co",
    ],
    "Hong Kong": [
        "https://www.f6s.com/companies/artificial-intelligence/hk/co",
    ],
    "Singapore": [
        "https://www.f6s.com/companies/artificial-intelligence/sg/co",
    ],
    "Vietnam": [
        "https://www.f6s.com/companies/artificial-intelligence/vn/co",
    ],
    "Thailand": [
        "https://www.f6s.com/companies/artificial-intelligence/th/co",
    ],
    "Indonesia": [
        "https://www.f6s.com/companies/artificial-intelligence/id/co",
    ],
    "Malaysia": [
        "https://www.f6s.com/companies/artificial-intelligence/my/co",
    ],
    "Philippines": [
        "https://www.f6s.com/companies/artificial-intelligence/ph/co",
    ],
    "India": [
        "https://www.f6s.com/companies/artificial-intelligence/in/co",
    ],
    "Sri Lanka": [],
    "Australia": [
        "https://www.f6s.com/companies/artificial-intelligence/au/co",
    ],
    "New Zealand": [
        "https://www.f6s.com/companies/artificial-intelligence/nz/co",
    ],
}


def _dedupe(companies: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for c in companies:
        key = c.get("website", "").lower().rstrip("/")
        if key and key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _claude_seed(client: anthropic.Anthropic, country: str, n: int = 15, geo: str = "EMEA") -> list[dict]:
    """
    Ask Claude to generate a seed list of AI/tech companies in a country
    that are likely to benefit from serverless Postgres for AI agents.
    """
    compliance_context = GEO_COMPLIANCE.get(geo.upper(), GEO_COMPLIANCE["EMEA"])

    namerica_extra = """
━━ NAMERICA-SPECIFIC TARGETING ━━
For North America, prioritise these additional high-value profiles:
- AWS-HEAVY companies currently on Amazon RDS Postgres, Aurora Postgres, or Supabase who are adding AI
  features and want a serverless, zero-config alternative with built-in pgvector
- Y COMBINATOR / VC-BACKED AI startups scaling fast — serverless branching is the "git for
  prod databases" story that resonates with rapid-iteration engineering culture
- HEALTHCARE AI companies (clinical decision support, medical imaging, patient data platforms)
  — HIPAA audit trail requirements make db9's ACID log compelling
- FINTECH AI (credit scoring, fraud detection, algorithmic trading) — SOC2 + real-time analytics
  on the same Postgres-compatible dataset
- ENTERPRISE SAAS companies scaling to thousands of tenants who need per-tenant isolation
  (db9 branching = instant per-customer database clone)
Do NOT limit to pure AI companies — include any tech company with a clear AI infrastructure need.
""" if geo.upper() == "NAMERICA" else ""

    prompt = f"""List {n} real AI or tech companies and startups based in {country} that are strong candidates for db9.ai — a serverless PostgreSQL platform built specifically for AI agents.

Applicable compliance framework for this region ({geo}): {compliance_context}
{namerica_extra}

db9's core value: zero-config serverless Postgres with built-in pgvector, database branching,
HTTP calls from SQL, and native integrations with Claude, OpenAI, and agent frameworks.
The pitch: AI agents need a database that's as easy to spin up as the agent itself — db9 is that database.

Target companies across FIVE distinct profiles. Aim for a balanced mix:

━━ PROFILE 1 — POSTGRES DISPLACEMENT CANDIDATES ━━
Companies currently on MySQL/Aurora/RDS who want Postgres-native vector search,
or on Supabase/Neon/PlanetScale who need more power, or self-hosting Postgres
with pgvector who would benefit from serverless zero-ops management.

━━ PROFILE 2 — AI COMPLIANCE TARGETS ━━
Companies building AI systems in regulated sectors (healthcare, finance, HR/recruitment, legal,
government) who need GDPR/HIPAA-compliant data storage with full audit trails.
db9 pitch: serverless Postgres with ACID guarantees, region-specific deployment, SOC2-ready.

━━ PROFILE 3 — AGENTIC WORKFLOW BUILDERS ━━
Companies building AI agents, copilots, or autonomous workflows that need:
- Persistent memory across sessions
- Multi-agent shared state
- Vector search for semantic recall
- Database branching for safe agent experimentation

━━ PROFILE 4 — EPISODIC MEMORY BUILDERS ━━
Companies whose AI agents need to LEARN over time — writing decisions and outcomes back
as vector embeddings. The Decide-Validate-Remember loop. Needs unified SQL + vector storage.

━━ PROFILE 5 — MCP-NATIVE COMPANIES ━━
Companies building with Claude, LangChain, or similar frameworks using MCP tool-use patterns.
db9's native Postgres HTTP endpoint means agents can query the database directly in natural language.

Include well-known companies AND lesser-known startups.
For each, provide their real website URL.

Return ONLY a JSON array, no other text:
[
  {{"name": "Company Name", "website": "https://example.com"}},
  ...
]"""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return []


def discover_companies(
    country: str,
    client: anthropic.Anthropic,
    min_results: int = 10,
    geo: str = "EMEA",
) -> list[dict]:
    """
    Discover AI companies in a given country.
    Returns list of {"name": str, "website": str}.
    """
    country_max = COUNTRY_MAX_OVERRIDE.get(country, MAX_COMPANIES_PER_COUNTRY)
    companies: list[dict] = []

    # Phase 1: scrape directories
    sources = DIRECTORY_SOURCES.get(country, [])
    for url in sources:
        cards = extract_company_cards(url)
        companies.extend(cards)

    companies = _dedupe(companies)

    # Phase 2: always supplement with Claude seed list for better ICP targeting
    seed_n = max(min_results, 30)
    if len(companies) < max(min_results, 20):
        seed = _claude_seed(client, country, n=seed_n, geo=geo)
        companies.extend(seed)
        companies = _dedupe(companies)

    # Apply cap only if set (0 = unlimited)
    if country_max > 0:
        return companies[:country_max]
    return companies
