"""
db9 Lead Dashboard — FastAPI backend.

Run: uvicorn dashboard.main:app --reload --port 8002
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import csv
import io
import secrets
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from agent.config import TIDB_CONNECTION_STRING, GEO_REGIONS
from agent.storage import get_conn, get_leads, get_countries_summary, update_lead_status
from agent.embeddings import hybrid_search
from agent.case_matcher import match_case_studies

app = FastAPI(title="db9 Global Leads Dashboard")
security = HTTPBasic()

DASHBOARD_USER = os.getenv("DASHBOARD_USER", "db9")
DASHBOARD_PASS = os.getenv("DASHBOARD_PASS", "db92026")


def require_auth(credentials: HTTPBasicCredentials = Depends(security)):
    ok = (
        secrets.compare_digest(credentials.username.encode(), DASHBOARD_USER.encode()) and
        secrets.compare_digest(credentials.password.encode(), DASHBOARD_PASS.encode())
    )
    if not ok:
        raise HTTPException(status_code=401, detail="Unauthorized",
                            headers={"WWW-Authenticate": "Basic"})


# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


def _db():
    if not TIDB_CONNECTION_STRING:
        raise HTTPException(status_code=503, detail="TIDB_CONNECTION_STRING not configured")
    return get_conn()


@app.get("/", response_class=HTMLResponse)
async def index(auth=Depends(require_auth)):
    html = (static_dir / "index.html").read_text()
    return HTMLResponse(content=html)


@app.get("/api/regions")
async def api_regions(auth=Depends(require_auth)):
    """Return full geo → sub-region → country hierarchy."""
    return GEO_REGIONS


@app.get("/api/summary")
async def api_summary(auth=Depends(require_auth)):
    """Per-country lead counts and stats."""
    conn = _db()
    try:
        return get_countries_summary(conn)
    finally:
        conn.close()


@app.get("/api/leads")
async def api_leads(
    auth=Depends(require_auth),
    geo: str | None = Query(None),
    country: str | None = Query(None),
    sub_region: str | None = Query(None),
    global_region: str | None = Query(None),  # legacy param
    min_score: int = Query(1, ge=1, le=10),
    status: str | None = Query(None),
):
    conn = _db()
    try:
        leads = get_leads(
            conn,
            country=country,
            global_region=global_region,
            sub_region=sub_region,
            geo=geo,
            min_score=min_score,
            status=status,
        )
        import json as _json
        for lead in leads:
            if lead.get("created_at"):
                lead["created_at"] = lead["created_at"].isoformat()
            emb = lead.pop("embedding", None)
            try:
                emb_vec = _json.loads(emb) if isinstance(emb, str) else emb
                lead["matched_case_studies"] = match_case_studies(emb_vec) if emb_vec else []
            except Exception:
                lead["matched_case_studies"] = []
        return leads
    finally:
        conn.close()


@app.get("/api/leads/export")
async def api_export(
    auth=Depends(require_auth),
    geo: str | None = Query(None),
    country: str | None = Query(None),
    sub_region: str | None = Query(None),
    global_region: str | None = Query(None),
    min_score: int = Query(1, ge=1, le=10),
    status: str | None = Query(None),
):
    conn = _db()
    try:
        leads = get_leads(
            conn,
            country=country,
            global_region=global_region,
            sub_region=sub_region,
            geo=geo,
            min_score=min_score,
            status=status,
        )
    finally:
        conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Company", "Website", "Country", "Global Region", "Sub-Region", "Geo",
        "Industry", "Company Size", "Description", "db9 Pain", "db9 Use Case",
        "Fit Score", "Status", "ICP Contacts"
    ])
    for lead in leads:
        contacts = "; ".join(
            c.get("role", "") if isinstance(c, dict) else c
            for c in (lead.get("contacts") or [])
        )
        writer.writerow([
            lead.get("company_name", ""),
            lead.get("website", ""),
            lead.get("country", ""),
            lead.get("global_region", ""),
            lead.get("sub_region", ""),
            lead.get("geo", ""),
            lead.get("industry", ""),
            lead.get("company_size", ""),
            lead.get("description", ""),
            lead.get("db9_pain", ""),
            lead.get("db9_use_case", ""),
            lead.get("fit_score", ""),
            lead.get("status", ""),
            contacts,
        ])

    output.seek(0)
    filename = f"db9-leads-score{min_score}+"
    if country:
        filename += f"-{country.lower().replace(' ','-')}"
    elif sub_region:
        filename += f"-{sub_region.lower().replace(' ','-')}"
    elif geo:
        filename += f"-{geo.lower()}"
    filename += ".csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/search")
async def api_search(
    auth=Depends(require_auth),
    q: str = Query(..., min_length=2),
    top_k: int = Query(20, ge=1, le=100),
    min_score: int = Query(1, ge=1, le=10),
    geo: str | None = Query(None),
    country: str | None = Query(None),
    region: str | None = Query(None),
):
    """
    Hybrid semantic search over leads using TiDB Vector Search.
    Combines VEC_COSINE_DISTANCE similarity with keyword matching.
    """
    conn = _db()
    try:
        results = hybrid_search(
            conn, query=q, top_k=top_k, min_score=min_score,
            geo=geo or None, country=country or None, region=region or None,
        )
        import json as _json
        for lead in results:
            if lead.get("created_at"):
                lead["created_at"] = lead["created_at"].isoformat()
            emb = lead.pop("embedding", None)
            try:
                emb_vec = _json.loads(emb) if isinstance(emb, str) else emb
                lead["matched_case_studies"] = match_case_studies(emb_vec) if emb_vec else []
            except Exception:
                lead["matched_case_studies"] = []
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.patch("/api/leads/{lead_id}/status")
async def api_update_status(lead_id: int, body: dict, auth=Depends(require_auth)):
    status = body.get("status")
    if status not in ("new", "contacted", "qualified", "disqualified"):
        raise HTTPException(status_code=400, detail="Invalid status")
    conn = _db()
    try:
        update_lead_status(conn, lead_id, status)
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
