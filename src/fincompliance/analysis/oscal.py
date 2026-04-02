"""
OSCAL-Compatible Output Schema

Generates compliance assessment results in a format inspired by NIST OSCAL
(Open Security Controls Assessment Language). This is the first financial
regulation equivalent of OSCAL — enabling interoperability with enterprise
GRC platforms like RegScale, Drata, and Vanta.

OSCAL structure adapted for FinCompliance:
- Catalog: regulatory rules (our Vale rules + Python checks)
- Profile: institution configuration (which regulations apply)
- Assessment Results: findings from a specific analysis run
- Component Definition: the institution's document being assessed

Reference: https://pages.nist.gov/OSCAL/
"""

import uuid
from datetime import datetime, timezone
from typing import Any


def generate_oscal_assessment(
    analysis_result: dict,
    institution_name: str = "Institution",
    document_name: str = "Document",
) -> dict:
    """
    Generate an OSCAL-inspired assessment result from analysis output.

    This format is compatible with enterprise GRC import pipelines and
    enables automated compliance tracking across tools.
    """
    now = datetime.now(timezone.utc).isoformat()
    assessment_id = f"fc-assessment-{uuid.uuid4().hex[:12]}"

    findings = analysis_result.get("findings", [])
    score = analysis_result.get("score", 0)
    citations = analysis_result.get("cfr_citations", [])

    # Build control results from findings
    control_results = []
    for f in findings:
        status = "not-satisfied" if f["level"] == "error" else "other"
        control_results.append({
            "control-id": f["rule"],
            "state": status,
            "title": f["rule"].replace("_", " "),
            "description": f["message"],
            "props": [
                {"name": "severity", "value": f["level"]},
                {"name": "regulation", "value": f.get("regulation", "common")},
                {"name": "citation", "value": f.get("citation", "")},
                {"name": "line", "value": str(f.get("line", 0))},
                {"name": "source", "value": f.get("source", "document")},
            ],
        })

    # Aggregate by regulation
    regulation_summary: dict[str, dict[str, Any]] = {}
    for f in findings:
        reg = f.get("regulation", "common")
        if reg not in regulation_summary:
            regulation_summary[reg] = {
                "errors": 0, "warnings": 0, "suggestions": 0, "total": 0,
            }
        regulation_summary[reg][f["level"] + "s"] = (
            regulation_summary[reg].get(f["level"] + "s", 0) + 1
        )
        regulation_summary[reg]["total"] += 1

    return {
        "$schema": "https://fincompliance.dev/schemas/assessment-result-v1.json",
        "metadata": {
            "title": f"FinCompliance Assessment — {institution_name}",
            "version": "1.0.0",
            "oscal-version": "1.1.2-fc",
            "published": now,
            "last-modified": now,
            "assessment-id": assessment_id,
            "tool": {
                "name": "FinCompliance",
                "version": analysis_result.get("version", "0.5.0"),
                "vendor": "BipinRimal314",
                "url": "https://github.com/BipinRimal314/comply",
            },
        },
        "import-ap": {
            "href": "https://fincompliance.dev/catalogs/us-financial-v1.json",
            "description": "FinCompliance US Financial Regulations Catalog",
        },
        "local-definitions": {
            "institution": {
                "name": institution_name,
                "type": "financial-institution",
            },
            "assessed-document": {
                "name": document_name,
                "type": "compliance-document",
            },
            "regulatory-citations": citations,
        },
        "results": {
            "title": f"Assessment of {document_name}",
            "start": now,
            "end": now,
            "compliance-score": score,
            "summary": {
                "total-findings": len(findings),
                "errors": analysis_result.get("error_count", 0),
                "warnings": analysis_result.get("warning_count", 0),
                "suggestions": analysis_result.get("suggestion_count", 0),
            },
            "regulation-coverage": regulation_summary,
            "metadata-completeness": analysis_result.get("metadata_check", {}),
            "observations": control_results,
        },
        "back-matter": {
            "resources": [
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "FFIEC BSA/AML Examination Manual",
                    "rlinks": [{"href": "https://bsaaml.ffiec.gov/manual"}],
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "PCI-DSS v4.0.1",
                    "rlinks": [{"href": "https://www.pcisecuritystandards.org/"}],
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "title": "CFPB UDAAP Procedures",
                    "rlinks": [{
                        "href": "https://files.consumerfinance.gov/f/documents/cfpb_unfair-deceptive-abusive-acts-practices-udaaps_procedures_2023-09.pdf",
                    }],
                },
            ],
        },
    }


def generate_oscal_catalog() -> dict:
    """
    Generate the FinCompliance rule catalog in OSCAL-inspired format.

    This is the machine-readable representation of all 49 rules,
    organized by regulation. Enterprise GRC platforms import this
    to map FinCompliance rules to their internal control frameworks.
    """
    from fincompliance.analysis.engine import AnalysisEngine

    engine = AnalysisEngine()
    rules = engine.list_rules()

    # Group rules by regulation
    groups: dict[str, list] = {}
    for rule in rules:
        reg = rule["regulation"]
        if reg not in groups:
            groups[reg] = []
        groups[reg].append({
            "id": f"FC-{rule['name']}",
            "title": rule["name"].replace("_", " "),
            "description": rule["description"],
            "props": [
                {"name": "severity", "value": rule["level"]},
                {"name": "type", "value": rule["type"]},
            ],
        })

    regulation_names = {
        "bsa-aml": "Bank Secrecy Act / Anti-Money Laundering",
        "sox": "Sarbanes-Oxley Act",
        "pci-dss": "Payment Card Industry Data Security Standard v4.0.1",
        "glba": "Gramm-Leach-Bliley Act",
        "ncua": "National Credit Union Administration",
        "udaap": "Unfair, Deceptive, or Abusive Acts or Practices",
        "reg-e": "Regulation E (Electronic Fund Transfers)",
        "reg-cc": "Regulation CC (Expedited Funds Availability)",
        "reg-dd": "Regulation DD (Truth in Savings)",
        "common": "Cross-Regulation Common Controls",
    }

    catalog_groups = []
    for reg_id, controls in sorted(groups.items()):
        catalog_groups.append({
            "id": f"FC-{reg_id}",
            "title": regulation_names.get(reg_id, reg_id),
            "controls": controls,
        })

    return {
        "$schema": "https://fincompliance.dev/schemas/catalog-v1.json",
        "metadata": {
            "title": "FinCompliance US Financial Regulations Catalog",
            "version": "0.5.0",
            "oscal-version": "1.1.2-fc",
            "published": datetime.now(timezone.utc).isoformat(),
        },
        "groups": catalog_groups,
        "total-controls": len(rules),
    }
