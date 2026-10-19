from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, HttpUrl

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("LEAD_DB_PATH", ROOT / "data" / "leads.sqlite3"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Market & Lead Intelligence Engine", version="0.1.0")


class ICP(BaseModel):
    industries: list[str] = Field(default_factory=list, max_length=50)
    regions: list[str] = Field(default_factory=list, max_length=50)
    min_employees: int = Field(default=0, ge=0)
    max_employees: int | None = Field(default=None, ge=1)
    required_signals: list[str] = Field(default_factory=list, max_length=50)


class Candidate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    domain: str = Field(min_length=1, max_length=253)
    industry: str = Field(default="", max_length=120)
    region: str = Field(default="", max_length=120)
    employees: int | None = Field(default=None, ge=0)
    signals: list[str] = Field(default_factory=list, max_length=100)
    contact_name: str | None = Field(default=None, max_length=200)
    contact_role: str | None = Field(default=None, max_length=200)
    contact_email: str | None = Field(default=None, max_length=320)
    source: str = Field(min_length=1, max_length=300)


class ResearchRequest(BaseModel):
    icp: ICP
    candidates: list[Candidate] = Field(min_length=1, max_length=1000)


def _connect() -> sqlite3.Connection:
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, created_at TEXT NOT NULL, icp_json TEXT NOT NULL,
        result_json TEXT NOT NULL
    )""")
    return db


def _score(candidate: Candidate, icp: ICP) -> dict[str, Any]:
    reasons: list[str] = []
    dimensions: list[float] = []
    if icp.industries:
        matched = candidate.industry.casefold() in {x.casefold() for x in icp.industries}
        dimensions.append(float(matched))
        if matched:
            reasons.append("industry matches ICP")
    if icp.regions:
        matched = candidate.region.casefold() in {x.casefold() for x in icp.regions}
        dimensions.append(float(matched))
        if matched:
            reasons.append("region matches ICP")
    if icp.min_employees or icp.max_employees is not None:
        matched = candidate.employees is not None and candidate.employees >= icp.min_employees
        if icp.max_employees is not None:
            matched = matched and candidate.employees is not None and candidate.employees <= icp.max_employees
        dimensions.append(float(matched))
        if matched:
            reasons.append("employee range matches ICP")
    signals = {x.casefold() for x in candidate.signals}
    for required in icp.required_signals:
        matched = required.casefold() in signals
        dimensions.append(float(matched))
        if matched:
            reasons.append(f"signal present: {required}")
    score = round(sum(dimensions) / len(dimensions) * 100) if dimensions else 0
    return {"score": score, "reasons": reasons, "score_version": "rule-based-v1"}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """<!doctype html><html><head><meta charset=utf-8><title>Lead Intelligence MVP</title>
    <style>body{font:16px system-ui;max-width:900px;margin:3rem auto;padding:0 1rem}textarea{width:100%;height:16rem}button{padding:.6rem 1rem}pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem}</style></head>
    <body><h1>Market &amp; Lead Intelligence</h1><p>Paste a JSON request. Candidate data must come from sources you are authorized to use.</p>
    <textarea id=x>{"icp":{"industries":["Manufacturing"],"regions":["US"],"min_employees":100,"required_signals":["hiring"]},"candidates":[{"company":"Example Manufacturing","domain":"example.com","industry":"Manufacturing","region":"US","employees":250,"signals":["hiring"],"source":"operator-provided"}]}</textarea><p><button onclick="run()">Score candidates</button></p><pre id=o></pre>
    <script>async function run(){let o=document.querySelector('#o');try{let r=await fetch('/research',{method:'POST',headers:{'content-type':'application/json'},body:document.querySelector('#x').value});o.textContent=JSON.stringify(await r.json(),null,2)}catch(e){o.textContent=String(e)}}</script></body></html>"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/research")
def research(request: ResearchRequest) -> dict[str, Any]:
    if request.icp.max_employees is not None and request.icp.max_employees < request.icp.min_employees:
        raise HTTPException(status_code=422, detail="max_employees must be at least min_employees")
    results = []
    seen: set[str] = set()
    for candidate in request.candidates:
        key = candidate.domain.casefold().removeprefix("www.")
        if key in seen:
            continue
        seen.add(key)
        results.append({**candidate.model_dump(), **_score(candidate, request.icp)})
    results.sort(key=lambda item: item["score"], reverse=True)
    job_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    result = {"job_id": job_id, "created_at": created_at, "results": results,
              "workflow": ["input-validation", "company-signal-analysis", "contact-review", "icp-scoring"]}
    with _connect() as db:
        db.execute("INSERT INTO jobs VALUES (?, ?, ?, ?)",
                   (job_id, created_at, request.icp.model_dump_json(), json.dumps(result)))
    return result


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    with _connect() as db:
        row = db.execute("SELECT result_json FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(row["result_json"])
