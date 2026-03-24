"""
Claude-powered company analysis.
Takes raw website text and returns structured lead intelligence.
"""
import json
import re

import anthropic

from .config import CLAUDE_MODEL, GEO_COMPLIANCE

SYSTEM_PROMPT = """You are a senior sales analyst for db9.ai — a serverless PostgreSQL platform built specifically for AI agents.

The primary users of databases are becoming AI agents. db9.ai is Postgres-native infrastructure
for the agent era: zero-config serverless deployment, built-in pgvector, database branching,
HTTP calls from SQL, and native integrations with Claude, OpenAI Codex, Cursor, and agent frameworks.
Not a database with AI features bolted on — the foundational data substrate for agentic applications.

db9 core capabilities:
- Zero-config serverless Postgres (one CLI command to deploy; scale to zero automatically)
- Built-in pgvector for semantic/vector search without external dependencies or ETL
- Unified SQL + cloud file storage (structured + unstructured data in one place)
- Database branching (copy-on-write snapshots — Git for databases; safe prod-like test environments)
- HTTP calls directly from SQL (agents can trigger webhooks, call APIs from within a query)
- pg_cron for scheduled agent tasks
- Full-text search with international language support
- Native integrations with Claude, OpenAI, LangChain, Cursor, and MCP-compatible agent frameworks
- ACID-compliant with full transaction audit log — provable lineage for every agent decision
- Multi-region deployment: eu-central-1, us-east-1, ap-southeast-1, ap-northeast-1, ap-south-1

db9's ICP has THREE distinct buying profiles. Score against all three:

━━ PROFILE 1 — POSTGRES DISPLACEMENT ━━
Companies currently on MySQL/Aurora/RDS, or self-hosting Postgres with pgvector complexity,
or on Supabase/Neon/PlanetScale who are hitting limits:
- Teams managing Postgres + separate vector DB (Pinecone, Weaviate, Qdrant) — the two-database problem
- Self-hosted pgvector shops drowning in ops overhead who want serverless zero-management Postgres
- MySQL/Aurora shops that want Postgres-native vector search without migrating application logic
- Any team stitching SQL + vector + file storage across 2+ systems — the "Memory Wall" for agents
- Supabase/Neon users who need more power: branching, HTTP-from-SQL, agent-first design

━━ PROFILE 2 — AI COMPLIANCE ━━
Companies operating in REGULATED SECTORS where AI decisions must be auditable.
Detect by sector and product type, not by the presence of compliance keywords.
The applicable framework depends on geography — see the geo context in this prompt.
High-risk sectors across all geos: Healthcare AI (clinical decision support, diagnostics,
patient data, medical imaging), Financial AI (credit scoring, fraud detection, trading, lending),
HR/Recruitment AI (CV screening, hiring decisions), Legal AI (contract analysis, court-facing tools),
Government/Public Services AI, Critical Infrastructure.
EMEA-specific signals: GDPR data residency, EU AI Act high-risk sectors.
NAMERICA-specific signals: healthcare AI handling PHI = HIPAA; US fintech = SOC2 + CCPA.
APAC-specific signals: Singapore/India/Australia data = PDPA/DPDP/APPs.
db9's compliance value: ACID transaction log = provable audit trail for every agent decision;
serverless branching = human-in-the-loop approval gate before AI changes reach production;
regional deployment satisfies data residency requirements out of the box.

━━ PROFILE 3 — AGENTIC WORKFLOW BUILDERS ━━
Companies building actual agent pipelines — not just AI products, but systems where:
- Agents take multi-step autonomous actions and need persistent memory across sessions
- Multi-agent platforms coordinate specialised sub-agents with shared structured + vector state
- Copilots write/read/update structured data as part of their active reasoning loop
- Agent orchestration platforms (workflow automation, research agents, coding agents, customer agents)
- AI-native SaaS where the database IS the agent's cognitive architecture
- EPISODIC MEMORY BUILDERS: agents that write their experiences (decisions + outcomes) back as vector
  embeddings so the system learns over time — the Decide-Validate-Remember loop
- MCP-NATIVE COMPANIES: teams building with Claude, LangChain, or similar frameworks using MCP
  tool-use patterns — db9's HTTP-from-SQL and pgvector let agents query data in natural language
These are the most urgent db9 leads — they will hit the Memory Wall within 6-12 months of scaling,
facing fragmented Postgres + vector DB + S3 stacks paying the "Agentic Tax" in engineering overhead.

Your job: analyse a company, identify which ICP profile(s) apply, and score fit precisely."""

ANALYSIS_PROMPT = """Analyse this company as a potential db9.ai customer across three ICP lenses.

Company: {company_name}
Website: {website}
Geography: {geo}
Applicable compliance framework: {compliance_context}

Website content:
---
{content}
---

Return ONLY valid JSON (no markdown, no explanation):
{{
  "description": "2-3 sentence description of what the company does and their main product",
  "icp_profile": "Which profile(s) apply — one or more of: 'Postgres Displacement', 'AI Compliance', 'Agentic Workflow Builder', 'Episodic Memory Builder', 'MCP-Native'. Comma-separate if multiple apply.",
  "db_stack": "Inferred or detected current database technology (e.g. 'Postgres + Pinecone', 'MySQL + pgvector', 'Supabase', 'Neon', 'Aurora', 'DynamoDB', 'self-hosted Postgres', 'Unknown'). Look for clues in job postings, tech stack mentions, integrations.",
  "db9_pain": "Specific pain point this company has that db9 solves — be concrete and reference the correct ICP profile. Examples: Displacement: 'Self-hosting Postgres + Pinecone for their AI agents — managing two systems with ETL overhead; db9 replaces both with serverless pgvector'; Compliance: 'Builds healthcare AI under HIPAA — needs ACID audit trail for every agent decision and regional deployment for PHI data residency'; Agentic: 'Building a multi-agent research platform where each agent needs persistent memory; current Postgres + Pinecone split means stale context and hallucinations at scale'; Episodic: 'Agents need to write decisions and outcomes back as vector embeddings — requires unified store for structured state and vector memory in one Postgres-compatible engine'",
  "db9_use_case": "One concrete use case: how would they specifically use db9? Reference their actual product. E.g. 'Replace their self-hosted Postgres + Pinecone stack with db9 serverless — unified pgvector cluster stores agent session memory, product embeddings, and relational data in one engine; database branching gives their DBA agent a safe sandbox for schema changes before prod merge; HTTP-from-SQL lets agents trigger external webhooks directly from query results'",
  "fit_score": <integer 1-10, where 10 = perfect ICP match>,
  "industry": "Industry category (e.g. 'AI Infrastructure', 'Healthcare AI', 'Legal AI', 'HR Tech', 'Fintech', 'Enterprise SaaS', 'Developer Tools', 'Agent Orchestration', etc.)",
  "company_size": "Estimated headcount band: '1-10', '11-50', '51-200', '201-500', '501-1000', or '1000+'. Use 'Unknown' if unclear.",
  "icp_contacts": ["Pick 3-5 from these GTM-aligned titles based on company profile — CTO, VP Engineering, Head of Data & AI, AI/ML Platform Lead, Chief Compliance Officer, Head of Backend Engineering, VP Product, Principal Engineer, Head of AI Infrastructure, Data Engineer Lead, DPO"],
  "outreach_recommendation": "1-2 sentence actionable outreach angle. Lead with the specific db9 value prop — name the database they should migrate from, the compliance framework they're targeting, or the agent architecture pattern where serverless Postgres fits. Be concrete."
}}

Scoring guide — award the highest applicable score:

9-10 PERFECT FIT (any one of):
  • Episodic Memory Builder: agents write decisions + outcomes back as vector embeddings in Postgres
  • Agentic Workflow Builder actively hitting the Memory Wall (Postgres + separate vector DB, multi-agent platform, autonomous agent with persistent memory)
  • AI Compliance HIGH-RISK sector (healthcare/finance/HR/legal AI) with agentic or autonomous decision-making AND scale
  • Postgres Displacement: self-hosting Postgres + Pinecone/Weaviate or on Aurora/RDS AND already managing a second vector system — immediate serverless migration candidate
  • MCP-Native: building with Claude/LangChain tool-use and needs Postgres as the unified data substrate

7-8 STRONG FIT (any one of):
  • Building AI agents or copilots but not yet at Memory Wall scale — will hit it within 12 months
  • AI compliance exposure in a regulated sector (healthcare, finance, legal) even without explicit agent architecture
  • Postgres/MySQL shop with clear AI roadmap and growing data complexity
  • Multi-tenant SaaS platform needing per-tenant database isolation at scale (branching story)
  • AI-native product where the database functions as the system of thought

5-6 MODERATE FIT:
  • Data-heavy tech company with AI on the roadmap but not yet building agents
  • Using a modern database but with signals suggesting future fragmentation
  • Compliance-aware company in a regulated sector not yet building AI agents

3-4 WEAK FIT:
  • Traditional tech company, limited data complexity, no AI signals
  • Non-technical B2C product with no visible data infrastructure needs

1-2 POOR FIT:
  • Non-technical company, pure services business, or no data infrastructure whatsoever

ICP contacts: 3-5 titles from this GTM-aligned list based on the company's profile:
  Technical leads: CTO, VP Engineering, Head of Data & AI, AI/ML Platform Lead, Principal Engineer, Head of AI Infrastructure, Data Engineer Lead
  Compliance leads: Chief Compliance Officer, Head of Legal & Compliance, Chief Risk Officer, DPO
  Product leads: VP Product, Head of AI Products
  Always include Head of Data & AI or AI/ML Platform Lead for any Agentic or Episodic Memory profile."""


def analyse_company(
    client: anthropic.Anthropic,
    company_name: str,
    website: str,
    content: str | None,
    geo: str = "EMEA",
) -> dict | None:
    """
    Returns structured analysis dict or None on failure.
    """
    if not content:
        content = "(No website content available — use company name and domain to infer)"

    compliance_context = GEO_COMPLIANCE.get(geo.upper(), GEO_COMPLIANCE["EMEA"])
    prompt = ANALYSIS_PROMPT.format(
        company_name=company_name,
        website=website,
        geo=geo.upper(),
        compliance_context=compliance_context,
        content=content[:5000],
    )

    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1536,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()

        # Strip markdown code fences if Claude wraps in them
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)

        result = json.loads(raw)

        # Validate required fields
        required = {"description", "db9_pain", "db9_use_case", "fit_score", "industry", "company_size", "icp_contacts", "outreach_recommendation"}
        if not required.issubset(result.keys()):
            return None

        # Normalise optional new fields — store as prefix in db9_pain
        icp_profile = result.pop("icp_profile", "")
        db_stack    = result.pop("db_stack", "")
        if icp_profile or db_stack:
            prefix = []
            if icp_profile: prefix.append(f"[{icp_profile}]")
            if db_stack and db_stack.lower() not in ("unknown", ""):
                prefix.append(f"[Stack: {db_stack}]")
            if prefix:
                result["db9_pain"] = " ".join(prefix) + " " + result["db9_pain"]

        result["fit_score"] = max(1, min(10, int(result["fit_score"])))
        return result

    except Exception:
        return None
