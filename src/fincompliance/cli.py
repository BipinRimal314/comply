#!/usr/bin/env python3
"""
Comply — Financial Compliance Documentation Linter

Wraps Vale for line-level linting and adds document-level analysis
for required sections, cross-references, and structural completeness.

Usage:
    python comply.py path/to/document.md
    python comply.py path/to/document.md --regulation bsa-aml
    python comply.py path/to/document.md --format json
"""

import argparse
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml


def convert_to_markdown(file_path: str) -> tuple[str, Path]:
    """Convert PDF/Word/HTML to Markdown using MarkItDown. Returns (content, temp_md_path)."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".md", ".txt"):
        return path.read_text(), path

    try:
        from markitdown import MarkItDown
    except ImportError:
        print(
            "Error: markitdown is required for PDF/Word conversion.\n"
            "Install it: pip install markitdown",
            file=sys.stderr,
        )
        sys.exit(1)

    md = MarkItDown()
    result = md.convert(str(path))
    content = result.text_content

    # Write to temp file for Vale to process
    temp_dir = Path(tempfile.mkdtemp())
    temp_path = temp_dir / f"{path.stem}.md"
    temp_path.write_text(content)

    return content, temp_path


@dataclass(frozen=True)
class Finding:
    rule: str
    level: str  # error, warning, suggestion
    message: str
    regulation: str
    citation: str = ""


def load_requirements(regulation: str) -> dict:
    """Load regulatory requirements from YAML."""
    req_dir = Path(__file__).parent / "regulatory-requirements"
    req_file = req_dir / f"{regulation}.yaml"
    if not req_file.exists():
        return {}
    with open(req_file) as f:
        return yaml.safe_load(f)


def check_required_metadata(content: str) -> list[Finding]:
    """Check that compliance document has required metadata fields."""
    findings = []
    required_fields = {
        "Effective Date": "All compliance documents must include an effective date",
        "Last Reviewed": "Examiners check that policies are reviewed regularly",
        "Next Review Date": "Demonstrates commitment to ongoing review",
        "Approved By": "Documents must show who authorized the policy",
        "Version": "Version control is required for audit trail",
    }
    content_lower = content.lower()
    for field, reason in required_fields.items():
        if field.lower() not in content_lower:
            findings.append(Finding(
                rule="DocumentMetadata",
                level="error",
                message=f"Missing required metadata: '{field}'. {reason}.",
                regulation="common",
            ))
    return findings


def check_bsa_pillars(content: str) -> list[Finding]:
    """Check that BSA/AML policy addresses all five required pillars."""
    findings = []
    content_lower = content.lower()

    pillars = {
        "Internal Controls": [
            "internal controls", "internal control", "system of controls",
        ],
        "Independent Testing": [
            "independent testing", "independent audit", "independent review",
            "external audit",
        ],
        "Designated BSA Compliance Officer": [
            "bsa compliance officer", "bsa officer", "designated compliance officer",
            "designated bsa",
        ],
        "Training": [
            "training program", "employee training", "staff training",
            "annual training", "bsa/aml training", "bsa training",
        ],
        "Customer Due Diligence": [
            "customer due diligence", "cdd", "due diligence program",
            "know your customer", "kyc",
        ],
    }

    for pillar_name, search_terms in pillars.items():
        found = any(term in content_lower for term in search_terms)
        if not found:
            findings.append(Finding(
                rule="BSA_FivePillars",
                level="error",
                message=(
                    f"BSA/AML policy is missing required pillar: '{pillar_name}'. "
                    f"FFIEC BSA/AML Examination Manual requires all five pillars."
                ),
                regulation="bsa-aml",
                citation="FFIEC BSA/AML Manual, Core Overview",
            ))
    return findings


def check_bsa_sar(content: str) -> list[Finding]:
    """Check SAR-related requirements."""
    findings = []
    content_lower = content.lower()

    sar_elements = {
        "SAR filing threshold": [
            "$5,000", "5,000", "five thousand", "filing threshold",
        ],
        "SAR filing deadline": [
            "30 calendar days", "30 days", "filing deadline", "thirty days",
        ],
        "SAR confidentiality": [
            "confidentiality", "confidential", "no disclosure",
            "shall not disclose",
        ],
        "SAR retention": [
            "five-year", "five year", "5-year", "5 year",
            "retention",
        ],
        "FinCEN filing": [
            "fincen", "financial crimes enforcement",
        ],
    }

    if "suspicious activity" in content_lower or "sar" in content_lower:
        for element_name, search_terms in sar_elements.items():
            found = any(term in content_lower for term in search_terms)
            if not found:
                findings.append(Finding(
                    rule="BSA_SARRequirements",
                    level="warning",
                    message=(
                        f"SAR section may be missing: '{element_name}'. "
                        f"Per 31 CFR 1020.320."
                    ),
                    regulation="bsa-aml",
                    citation="31 CFR 1020.320",
                ))
    return findings


def check_bsa_ctr(content: str) -> list[Finding]:
    """Check CTR-related requirements."""
    findings = []
    content_lower = content.lower()

    if "currency transaction" in content_lower or "ctr" in content_lower:
        ctr_elements = {
            "$10,000 threshold": [
                "$10,000", "10,000", "ten thousand",
            ],
            "Aggregation rules": [
                "aggregat", "multiple transactions", "combined",
            ],
            "Structuring monitoring": [
                "structur", "smurfing", "evade", "evasion",
            ],
        }
        for element_name, search_terms in ctr_elements.items():
            found = any(term in content_lower for term in search_terms)
            if not found:
                findings.append(Finding(
                    rule="BSA_CTRRequirements",
                    level="warning",
                    message=(
                        f"CTR section may be missing: '{element_name}'. "
                        f"Per 31 CFR 1010.310."
                    ),
                    regulation="bsa-aml",
                    citation="31 CFR 1010.310",
                ))
    return findings


def check_bsa_cip(content: str) -> list[Finding]:
    """Check CIP-related requirements."""
    findings = []
    content_lower = content.lower()

    if "customer identification" in content_lower or "cip" in content_lower:
        cip_elements = {
            "Identity verification methods": [
                "verification", "documentary", "non-documentary",
            ],
            "Required customer information": [
                "date of birth", "address", "identification number",
            ],
            "Government list screening": [
                "government list", "ofac", "sdn", "314(a)",
            ],
            "Customer notice": [
                "customer notice", "notify", "notification",
            ],
        }
        for element_name, search_terms in cip_elements.items():
            found = any(term in content_lower for term in search_terms)
            if not found:
                findings.append(Finding(
                    rule="BSA_CIPRequirements",
                    level="warning",
                    message=(
                        f"CIP section may be missing: '{element_name}'. "
                        f"Per 31 CFR 1020.220."
                    ),
                    regulation="bsa-aml",
                    citation="31 CFR 1020.220",
                ))
    return findings


def check_section_structure(content: str) -> list[Finding]:
    """Check that document has proper heading structure."""
    findings = []
    lines = content.split("\n")
    has_h1 = any(line.startswith("# ") for line in lines)
    has_h2 = any(line.startswith("## ") for line in lines)

    if not has_h1:
        findings.append(Finding(
            rule="DocumentStructure",
            level="error",
            message="Document missing top-level heading (# Title).",
            regulation="common",
        ))
    if not has_h2:
        findings.append(Finding(
            rule="DocumentStructure",
            level="warning",
            message="Document has no section headings (## Section). Compliance documents need clear section organization.",
            regulation="common",
        ))
    return findings


def _get_vale_config() -> Path:
    """Find the Vale config, checking package directory then project root."""
    # Check if running from installed package
    pkg_config = Path(__file__).parent / ".vale.ini"
    if pkg_config.exists():
        return pkg_config
    # Check project root (development mode)
    project_config = Path(__file__).parent.parent.parent / ".vale.ini"
    if project_config.exists():
        return project_config
    # Fallback: current directory
    cwd_config = Path.cwd() / ".vale.ini"
    if cwd_config.exists():
        return cwd_config
    return project_config  # Will fail gracefully if Vale can't find it


def run_vale(file_path: str) -> dict:
    """Run Vale and return JSON results."""
    config = _get_vale_config()
    result = subprocess.run(
        ["vale", f"--config={config}", "--output=JSON", file_path],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        return {}


def format_finding(finding: Finding) -> str:
    """Format a single finding for terminal output."""
    icons = {"error": "E", "warning": "W", "suggestion": "S"}
    colors = {"error": "\033[31m", "warning": "\033[33m", "suggestion": "\033[34m"}
    reset = "\033[0m"
    icon = icons.get(finding.level, "?")
    color = colors.get(finding.level, "")
    citation = f" [{finding.citation}]" if finding.citation else ""
    return f"  {color}{icon}{reset}  [{finding.rule}] {finding.message}{citation}"


def analyze_document(
    file_path: str,
    regulation: str = "bsa-aml",
) -> tuple[list[Finding], dict]:
    """Run full analysis: Vale linting + document-level checks."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    # Convert non-Markdown formats
    if suffix in (".pdf", ".docx", ".doc", ".html", ".htm", ".rtf"):
        print(f"  Converting {suffix} to Markdown...", file=sys.stderr)
        content, md_path = convert_to_markdown(file_path)
        vale_target = str(md_path)
    else:
        content = path.read_text()
        vale_target = file_path

    doc_findings: list[Finding] = []

    # Document-level checks
    doc_findings.extend(check_required_metadata(content))
    doc_findings.extend(check_section_structure(content))

    # Regulation-specific checks
    if regulation == "bsa-aml":
        doc_findings.extend(check_bsa_pillars(content))
        doc_findings.extend(check_bsa_sar(content))
        doc_findings.extend(check_bsa_ctr(content))
        doc_findings.extend(check_bsa_cip(content))

    # Vale linting
    vale_results = run_vale(vale_target)

    return doc_findings, vale_results


def print_results(
    file_path: str,
    doc_findings: list[Finding],
    vale_results: dict,
) -> int:
    """Print formatted results. Returns exit code (0=clean, 1=issues found)."""
    print(f"\n\033[4m{file_path}\033[0m\n")

    # Document-level findings
    if doc_findings:
        print("  Document-Level Analysis:")
        for finding in doc_findings:
            print(format_finding(finding))
        print()

    # Vale findings
    vale_count = {"error": 0, "warning": 0, "suggestion": 0}
    for filepath, alerts in vale_results.items():
        if alerts:
            print(f"  Line-Level Analysis (Vale):")
            for alert in alerts:
                level = alert.get("Severity", "warning").lower()
                vale_count[level] = vale_count.get(level, 0) + 1
                line = alert.get("Line", 0)
                msg = alert.get("Message", "")
                check = alert.get("Check", "")
                colors = {
                    "error": "\033[31m",
                    "warning": "\033[33m",
                    "suggestion": "\033[34m",
                }
                reset = "\033[0m"
                icon = {"error": "E", "warning": "W", "suggestion": "S"}.get(
                    level, "?"
                )
                print(f"  {colors.get(level, '')}{icon}{reset}  L{line}: [{check}] {msg}")
            print()

    # Summary
    doc_errors = sum(1 for f in doc_findings if f.level == "error")
    doc_warnings = sum(1 for f in doc_findings if f.level == "warning")
    doc_suggestions = sum(1 for f in doc_findings if f.level == "suggestion")

    total_errors = doc_errors + vale_count.get("error", 0)
    total_warnings = doc_warnings + vale_count.get("warning", 0)
    total_suggestions = doc_suggestions + vale_count.get("suggestion", 0)

    print(
        f"  \033[31m{total_errors} errors\033[0m, "
        f"\033[33m{total_warnings} warnings\033[0m, "
        f"\033[34m{total_suggestions} suggestions\033[0m"
    )

    if total_errors == 0 and total_warnings == 0:
        print("  \033[32m✓ Document passes compliance checks\033[0m")

    return 1 if total_errors > 0 else 0


def main():
    parser = argparse.ArgumentParser(
        description="FinCompliance — Financial Compliance Documentation Linter",
        epilog="Supports: .md, .txt, .pdf, .docx, .doc, .html, .rtf",
    )
    parser.add_argument(
        "file",
        help="Path to compliance document (Markdown, PDF, Word, HTML)",
    )
    parser.add_argument(
        "--regulation",
        default="bsa-aml",
        choices=["bsa-aml", "common"],
        help="Regulation to check against (default: bsa-aml)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        default="text",
        choices=["text", "json"],
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--report",
        metavar="NAME",
        help="Generate HTML gap report. NAME = institution name for the report header.",
    )
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    doc_findings, vale_results = analyze_document(args.file, args.regulation)

    if args.report:
        from fincompliance.report import generate_html_report

        data = {
            "document_findings": [
                {
                    "rule": f.rule,
                    "level": f.level,
                    "message": f.message,
                    "regulation": f.regulation,
                    "citation": f.citation,
                }
                for f in doc_findings
            ],
            "vale_findings": vale_results,
        }
        html = generate_html_report(data, args.report)
        output_path = Path(args.file).stem + "_gap_report.html"
        with open(output_path, "w") as f:
            f.write(html)
        print(f"Gap report generated: {output_path}")
    elif args.output_format == "json":
        output = {
            "file": args.file,
            "regulation": args.regulation,
            "document_findings": [
                {
                    "rule": f.rule,
                    "level": f.level,
                    "message": f.message,
                    "regulation": f.regulation,
                    "citation": f.citation,
                }
                for f in doc_findings
            ],
            "vale_findings": vale_results,
        }
        print(json.dumps(output, indent=2))
    else:
        exit_code = print_results(args.file, doc_findings, vale_results)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
