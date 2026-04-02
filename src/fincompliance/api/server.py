"""
FinCompliance REST API

Enterprise-grade API for compliance documentation linting.
Accepts PDF, Word, Markdown. Returns structured JSON gap reports.

Usage:
    uvicorn fincompliance.api.server:app --host 0.0.0.0 --port 8000
    # Or via Docker:
    docker run -p 8000:8000 fincompliance/api
"""

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from fincompliance import __version__
from fincompliance.analysis.engine import AnalysisEngine
from fincompliance.report import generate_html_report

app = FastAPI(
    title="FinCompliance API",
    description=(
        "Financial compliance documentation linter. "
        "49 deterministic rules across 9 US financial regulations."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = AnalysisEngine()


@app.get("/")
async def root():
    return {
        "name": "FinCompliance API",
        "version": __version__,
        "rules": engine.rule_count,
        "regulations": engine.regulations,
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/rules")
async def list_rules():
    """List all available linting rules with metadata."""
    return {"rules": engine.list_rules(), "total": engine.rule_count}


@app.post("/analyze")
async def analyze_document(
    file: UploadFile = File(...),
    regulation: str = Query(
        "bsa-aml",
        description="Primary regulation to check against",
        enum=["bsa-aml", "sox", "pci-dss", "glba", "ncua", "udaap", "reg-e", "reg-cc", "reg-dd", "all"],
    ),
    institution_name: str = Query(
        "Institution",
        description="Institution name for the report",
    ),
):
    """
    Analyze a compliance document.

    Upload a PDF, Word, or Markdown file. Returns a structured JSON gap report
    with findings categorized by severity, regulation, and remediation priority.
    """
    allowed_types = {
        ".pdf", ".docx", ".doc", ".md", ".txt", ".html", ".htm", ".rtf",
    }
    suffix = Path(file.filename or "document.md").suffix.lower()
    if suffix not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(allowed_types))}",
        )

    # Save uploaded file to temp location
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / f"upload_{uuid.uuid4().hex[:8]}{suffix}"
    content = await file.read()
    temp_path.write_bytes(content)

    try:
        result = engine.analyze(str(temp_path), regulation=regulation)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e!s}") from e
    finally:
        temp_path.unlink(missing_ok=True)
        temp_dir.rmdir()

    # Build response
    analysis_id = uuid.uuid4().hex[:12]
    return {
        "analysis_id": analysis_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "file": file.filename,
        "regulation": regulation,
        "institution": institution_name,
        "version": __version__,
        "summary": {
            "score": result["score"],
            "total_findings": result["total_findings"],
            "errors": result["error_count"],
            "warnings": result["warning_count"],
            "suggestions": result["suggestion_count"],
        },
        "findings": result["findings"],
        "metadata_check": result["metadata_check"],
        "regulation_coverage": result["regulation_coverage"],
    }


@app.post("/analyze/report")
async def analyze_and_report(
    file: UploadFile = File(...),
    regulation: str = Query("bsa-aml"),
    institution_name: str = Query("Institution"),
):
    """
    Analyze a document and return an HTML gap report.
    Suitable for emailing to compliance officers.
    """
    # Run analysis
    json_result = await analyze_document(file, regulation, institution_name)

    # Convert to format expected by report generator
    report_data = {
        "document_findings": [
            {
                "rule": f["rule"],
                "level": f["level"],
                "message": f["message"],
                "regulation": f.get("regulation", ""),
                "citation": f.get("citation", ""),
            }
            for f in json_result["findings"]
        ],
        "vale_findings": {},
    }
    html = generate_html_report(report_data, institution_name)
    return HTMLResponse(content=html)


@app.post("/batch")
async def batch_analyze(
    files: list[UploadFile] = File(...),
    regulation: str = Query("all"),
    institution_name: str = Query("Institution"),
):
    """
    Analyze multiple compliance documents in a single request.
    Returns aggregated findings and cross-document analysis.
    """
    results = []
    all_findings = []
    total_errors = 0
    total_warnings = 0

    for file in files:
        suffix = Path(file.filename or "document.md").suffix.lower()
        temp_dir = Path(tempfile.mkdtemp())
        temp_path = temp_dir / f"upload_{uuid.uuid4().hex[:8]}{suffix}"
        content = await file.read()
        temp_path.write_bytes(content)

        try:
            result = engine.analyze(str(temp_path), regulation=regulation)
            results.append({
                "file": file.filename,
                "score": result["score"],
                "errors": result["error_count"],
                "warnings": result["warning_count"],
                "findings_count": result["total_findings"],
            })
            for f in result["findings"]:
                f["source_file"] = file.filename
                all_findings.append(f)
            total_errors += result["error_count"]
            total_warnings += result["warning_count"]
        finally:
            temp_path.unlink(missing_ok=True)
            temp_dir.rmdir()

    # Cross-document analysis
    cross_doc = engine.cross_document_analysis(all_findings)

    avg_score = (
        sum(r["score"] for r in results) / len(results) if results else 0
    )

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "institution": institution_name,
        "documents_analyzed": len(results),
        "summary": {
            "average_score": round(avg_score, 1),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_findings": len(all_findings),
        },
        "per_document": results,
        "cross_document_analysis": cross_doc,
        "findings": all_findings,
    }
