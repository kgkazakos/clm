"""
Cognitive Load Monitor — FastAPI backend
Exposes two endpoints:
  POST /api/analyse  — run full analysis, return AnalysisResult
  GET  /api/report/{session_id} — download JSON or Markdown report
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from agent import interpret
from adapters import canonical, maze, usertesting
from composite import calculate as calculate_composite
from config import LLM_PROVIDER
from models import (
    AnalysisRequest,
    AnalysisResult,
    InputFormat,
    InteractionEvent,
)
from report import write_json, write_markdown

app = FastAPI(title="Cognitive Load Monitor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def _adapt(request: AnalysisRequest) -> list[InteractionEvent]:
    """Route raw data through the correct adapter."""
    raw = [e.model_dump() for e in request.events]

    if request.format == InputFormat.CANONICAL:
        return canonical.parse(raw)
    elif request.format == InputFormat.MAZE:
        return maze.parse({"recordings": raw})
    elif request.format == InputFormat.USERTESTING:
        return usertesting.parse({"clips": raw})
    else:
        raise ValueError(f"Unknown format: {request.format}")


@app.post("/api/analyse", response_model=AnalysisResult)
async def analyse(request: AnalysisRequest) -> AnalysisResult:
    """
    Run the full two-layer cognitive load analysis.
    Layer 1: telemetry signal calculators + composite index (pure Python)
    Layer 2: LLM agent CLT classification + hypothesis generation
    """
    if not request.events:
        raise HTTPException(status_code=400, detail="No events provided")

    session_id = str(uuid.uuid4())[:8]
    events = _adapt(request)

    # Layer 1 — deterministic measurement
    composite_index, breakdown = calculate_composite(events)

    duration_ms = (
        max(e.timestamp_ms for e in events) - min(e.timestamp_ms for e in events)
        if len(events) > 1 else 0
    )

    # Layer 2 — AI interpretation (provider set via LLM_PROVIDER in .env)
    agent_output = interpret(composite_index, breakdown, request.context)

    result = AnalysisResult(
        session_id=session_id,
        composite_index=composite_index,
        signal_breakdown=breakdown,
        agent_output=agent_output,
        event_count=len(events),
        duration_ms=duration_ms,
        format_used=request.format,
        context=request.context,
    )

    write_json(result, OUTPUT_DIR)
    write_markdown(result, OUTPUT_DIR)

    return result


@app.get("/api/report/{session_id}")
async def get_report(session_id: str, format: str = "json") -> FileResponse:
    """Download the report for a completed session."""
    ext = "json" if format == "json" else "md"
    path = OUTPUT_DIR / f"clm_report_{session_id}.{ext}"

    if not path.exists():
        raise HTTPException(status_code=404, detail="Report not found")

    media_type = "application/json" if ext == "json" else "text/markdown"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0", "provider": LLM_PROVIDER}