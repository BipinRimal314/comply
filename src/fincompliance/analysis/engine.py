"""
FinCompliance Analysis Engine

The core analysis logic. Combines:
1. Vale deterministic linting (line-level)
2. Document-level structural analysis (Python)
3. Cross-document reference tracking
4. Regulatory coverage scoring

This is the defensible layer — regulatory knowledge encoded as structured logic.
"""

import json
import re
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Finding:
    rule: str
    level: str
    message: str
    regulation: str
    citation: str = ""
    line: int = 0
    source: str = "document"  # "document" or "vale"


class AnalysisEngine:
    """Core analysis engine combining Vale + Python checks."""

    # Map of regulation IDs to display names
    REGULATIONS = {
        "bsa-aml": "BSA/AML (Bank Secrecy Act)",
        "sox": "SOX (Sarbanes-Oxley)",
        "pci-dss": "PCI-DSS v4.0.1",
        "glba": "GLBA (Gramm-Leach-Bliley)",
        "ncua": "NCUA",
        "udaap": "UDAAP",
        "reg-e": "Regulation E",
        "reg-cc": "Regulation CC",
        "reg-dd": "Regulation DD",
    }

    # Regulatory requirement matrix — what each regulation requires in documentation
    REQUIREMENT_MATRIX = {
        "bsa-aml": {
            "pillars": [
                "internal controls", "independent testing",
                "bsa compliance officer", "training", "customer due diligence",
            ],
            "sar_elements": [
                "filing threshold", "filing deadline", "confidentiality",
                "retention", "fincen",
            ],
            "ctr_elements": ["$10,000", "aggregation", "structuring"],
            "cip_elements": [
                "verification", "date of birth", "address",
                "identification number", "government list",
            ],
        },
        "pci-dss": {
            "core_sections": [
                "network security", "secure configuration", "stored account data",
                "cryptography", "malware", "secure systems", "access control",
                "authentication", "physical access", "logging and monitoring",
                "vulnerability testing", "organizational policies",
            ],
        },
        "glba": {
            "privacy_notice": [
                "categories of information collected",
                "categories of information disclosed",
                "affiliates", "third parties", "protection practices",
            ],
        },
    }

    def __init__(self):
        self._vale_config = self._find_vale_config()
        self._requirements = self._load_requirements()

    @property
    def rule_count(self) -> int:
        styles_dir = self._vale_config.parent / ".vale" / "styles" / "FinCompliance"
        if not styles_dir.exists():
            # Try package location
            styles_dir = Path(__file__).parent.parent / "vale_styles" / "FinCompliance"
        return len(list(styles_dir.glob("*.yml"))) if styles_dir.exists() else 0

    @property
    def regulations(self) -> list[str]:
        return list(self.REGULATIONS.keys())

    def _find_vale_config(self) -> Path:
        """Find the Vale config file."""
        locations = [
            Path(__file__).parent.parent / ".vale.ini",
            Path(__file__).parent.parent.parent.parent / ".vale.ini",
            Path.cwd() / ".vale.ini",
        ]
        for loc in locations:
            if loc.exists():
                return loc
        return locations[0]

    def _load_requirements(self) -> dict:
        """Load regulatory requirements YAML."""
        req_dir = Path(__file__).parent.parent / "regulatory-requirements"
        reqs = {}
        if req_dir.exists():
            for f in req_dir.glob("*.yaml"):
                with open(f) as fh:
                    reqs[f.stem] = yaml.safe_load(fh)
        return reqs

    def list_rules(self) -> list[dict]:
        """List all Vale rules with metadata."""
        styles_dir = self._vale_config.parent / ".vale" / "styles" / "FinCompliance"
        if not styles_dir.exists():
            styles_dir = Path(__file__).parent.parent / "vale_styles" / "FinCompliance"
        rules = []
        for yml in sorted(styles_dir.glob("*.yml")):
            with open(yml) as f:
                content = f.read()
            # Extract metadata from comments and YAML
            lines = content.split("\n")
            comment_lines = [
                l.lstrip("# ").strip() for l in lines if l.startswith("#")
            ]
            description = " ".join(comment_lines[:2]) if comment_lines else ""

            # Parse YAML for level and type
            data = yaml.safe_load(content)
            rules.append({
                "name": yml.stem,
                "description": description,
                "level": data.get("level", "warning"),
                "type": data.get("extends", "unknown"),
                "regulation": self._rule_to_regulation(yml.stem),
            })
        return rules

    def _rule_to_regulation(self, rule_name: str) -> str:
        """Map rule name to regulation."""
        prefixes = {
            "BSA_": "bsa-aml",
            "SOX_": "sox",
            "PCI_": "pci-dss",
            "GLBA_": "glba",
            "NCUA_": "ncua",
            "UDAAP_": "udaap",
            "RegE_": "reg-e",
            "RegCC_": "reg-cc",
            "RegDD_": "reg-dd",
        }
        for prefix, reg in prefixes.items():
            if rule_name.startswith(prefix):
                return reg
        return "common"

    def _convert_to_markdown(self, file_path: str) -> tuple[str, str]:
        """Convert non-Markdown files. Returns (content, path_for_vale)."""
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in (".md", ".txt"):
            return path.read_text(), file_path

        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(str(path))
            content = result.text_content

            temp_dir = Path(tempfile.mkdtemp())
            temp_path = temp_dir / f"{path.stem}.md"
            temp_path.write_text(content)
            return content, str(temp_path)
        except ImportError:
            return path.read_text(), file_path

    def _run_vale(self, file_path: str) -> list[Finding]:
        """Run Vale and return findings."""
        result = subprocess.run(
            ["vale", f"--config={self._vale_config}", "--output=JSON", file_path],
            capture_output=True,
            text=True,
        )
        findings = []
        try:
            data = json.loads(result.stdout) if result.stdout.strip() else {}
        except json.JSONDecodeError:
            return findings

        for filepath, alerts in data.items():
            for alert in alerts:
                level = alert.get("Severity", "warning").lower()
                check = alert.get("Check", "").replace("FinCompliance.", "")
                findings.append(Finding(
                    rule=check,
                    level=level,
                    message=alert.get("Message", ""),
                    regulation=self._rule_to_regulation(check),
                    line=alert.get("Line", 0),
                    source="vale",
                ))
        return findings

    def _check_metadata(self, content: str) -> list[Finding]:
        """Check required document metadata."""
        findings = []
        required = {
            "Effective Date": "All compliance documents must include an effective date",
            "Last Reviewed": "Examiners check that policies are reviewed regularly",
            "Next Review Date": "Demonstrates commitment to ongoing review",
            "Approved By": "Documents must show who authorized the policy",
            "Version": "Version control is required for audit trail",
        }
        content_lower = content.lower()
        for field, reason in required.items():
            if field.lower() not in content_lower:
                findings.append(Finding(
                    rule="DocumentMetadata",
                    level="error",
                    message=f"Missing required metadata: '{field}'. {reason}.",
                    regulation="common",
                ))
        return findings

    def _check_structure(self, content: str) -> list[Finding]:
        """Check document heading structure."""
        findings = []
        lines = content.split("\n")
        if not any(line.startswith("# ") for line in lines):
            findings.append(Finding(
                rule="DocumentStructure",
                level="error",
                message="Document missing top-level heading (# Title).",
                regulation="common",
            ))
        if not any(line.startswith("## ") for line in lines):
            findings.append(Finding(
                rule="DocumentStructure",
                level="warning",
                message="Document has no section headings. Compliance documents need clear section organization.",
                regulation="common",
            ))
        return findings

    def _check_bsa_requirements(self, content: str) -> list[Finding]:
        """Check BSA/AML specific requirements."""
        findings = []
        content_lower = content.lower()

        # Five pillars
        pillars = {
            "Internal Controls": ["internal controls", "internal control", "system of controls"],
            "Independent Testing": ["independent testing", "independent audit", "independent review", "external audit"],
            "Designated BSA Compliance Officer": ["bsa compliance officer", "bsa officer", "designated compliance officer", "designated bsa"],
            "Training": ["training program", "employee training", "staff training", "annual training", "bsa/aml training"],
            "Customer Due Diligence": ["customer due diligence", "cdd", "due diligence program", "know your customer", "kyc"],
        }
        for pillar_name, terms in pillars.items():
            if not any(term in content_lower for term in terms):
                findings.append(Finding(
                    rule="BSA_FivePillars",
                    level="error",
                    message=f"BSA/AML policy is missing required pillar: '{pillar_name}'.",
                    regulation="bsa-aml",
                    citation="FFIEC BSA/AML Manual, Core Overview",
                ))

        # SAR requirements
        if "suspicious activity" in content_lower or "sar" in content_lower:
            sar_checks = {
                "SAR filing threshold": ["$5,000", "5,000", "five thousand", "filing threshold"],
                "SAR filing deadline": ["30 calendar days", "30 days", "filing deadline", "thirty days"],
                "SAR confidentiality": ["confidentiality", "confidential", "no disclosure", "shall not disclose"],
                "SAR retention": ["five-year", "five year", "5-year", "5 year", "retention"],
                "FinCEN filing": ["fincen", "financial crimes enforcement"],
            }
            for element, terms in sar_checks.items():
                if not any(term in content_lower for term in terms):
                    findings.append(Finding(
                        rule="BSA_SARRequirements",
                        level="warning",
                        message=f"SAR section may be missing: '{element}'.",
                        regulation="bsa-aml",
                        citation="31 CFR 1020.320",
                    ))

        # CTR requirements
        if "currency transaction" in content_lower or "ctr" in content_lower:
            ctr_checks = {
                "$10,000 threshold": ["$10,000", "10,000", "ten thousand"],
                "Aggregation rules": ["aggregat", "multiple transactions", "combined"],
                "Structuring monitoring": ["structur", "smurfing", "evade", "evasion"],
            }
            for element, terms in ctr_checks.items():
                if not any(term in content_lower for term in terms):
                    findings.append(Finding(
                        rule="BSA_CTRRequirements",
                        level="warning",
                        message=f"CTR section may be missing: '{element}'.",
                        regulation="bsa-aml",
                        citation="31 CFR 1010.310",
                    ))

        # CIP requirements
        if "customer identification" in content_lower or "cip" in content_lower:
            cip_checks = {
                "Identity verification methods": ["verification", "documentary", "non-documentary"],
                "Required customer information": ["date of birth", "address", "identification number"],
                "Government list screening": ["government list", "ofac", "sdn", "314(a)"],
                "Customer notice": ["customer notice", "notify", "notification"],
            }
            for element, terms in cip_checks.items():
                if not any(term in content_lower for term in terms):
                    findings.append(Finding(
                        rule="BSA_CIPRequirements",
                        level="warning",
                        message=f"CIP section may be missing: '{element}'.",
                        regulation="bsa-aml",
                        citation="31 CFR 1020.220",
                    ))

        return findings

    def _extract_cfr_citations(self, content: str) -> list[str]:
        """Extract all CFR citations from the document for regulatory change tracking."""
        patterns = [
            r'\d+\s+(?:CFR|C\.F\.R\.)\s+[\d\.]+',
            r'\d+\s+USC\s+[\d\.]+',
            r'12\s+CFR\s+(?:Part\s+)?\d+',
            r'31\s+CFR\s+(?:Part\s+)?\d+',
            r'16\s+CFR\s+(?:Part\s+)?\d+',
        ]
        citations = set()
        for pattern in patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                citations.add(match.group().strip())
        return sorted(citations)

    def _extract_cross_references(self, content: str) -> list[dict]:
        """Extract cross-document references for dependency tracking."""
        patterns = [
            r'(?:refer to|see|per|as described in|as outlined in)\s+(?:the\s+)?["\']?([A-Z][A-Za-z\s/]+(?:Policy|Manual|Procedures?|Plan|Program|Guide))["\']?',
            r'(?:refer to|see)\s+(?:Section|section)\s+([\d\.]+)',
        ]
        refs = []
        for i, line in enumerate(content.split("\n"), 1):
            for pattern in patterns:
                for match in re.finditer(pattern, line):
                    refs.append({
                        "line": i,
                        "reference": match.group(1).strip(),
                        "context": line.strip()[:120],
                    })
        return refs

    def _calculate_score(
        self, errors: int, warnings: int, suggestions: int,
    ) -> int:
        """Calculate compliance documentation score (0-100)."""
        return max(0, 100 - (errors * 10) - (warnings * 3) - (suggestions * 1))

    def _detect_document_type(self, content: str) -> dict:
        """Auto-detect which regulations a document relates to based on content."""
        content_lower = content.lower()
        detected = {
            "bsa-aml": any(term in content_lower for term in [
                "bank secrecy", "anti-money laundering", "bsa/aml", "bsa ",
                "suspicious activity", "currency transaction", "customer identification program",
                "customer due diligence", "fincen", "patriot act", "aml program",
            ]),
            "sox": any(term in content_lower for term in [
                "sarbanes-oxley", "sox ", "internal control over financial reporting",
                "icfr", "pcaob", "section 302", "section 404", "material weakness",
            ]),
            "pci-dss": any(term in content_lower for term in [
                "pci-dss", "pci dss", "payment card", "cardholder data",
                "cardholder data environment", "cde", "qualified security assessor",
            ]),
            "glba": any(term in content_lower for term in [
                "gramm-leach-bliley", "glba", "regulation s-p", "nonpublic personal",
                "privacy notice", "safeguards rule", "16 cfr 313", "16 cfr 314",
            ]),
            "udaap": any(term in content_lower for term in [
                "udaap", "unfair, deceptive", "unfair deceptive", "abusive acts",
                "consumer protection", "cfpb",
            ]),
            "reg-e": any(term in content_lower for term in [
                "regulation e", "electronic fund transfer", "12 cfr 1005",
                "unauthorized transfer", "error resolution",
            ]),
            "reg-cc": any(term in content_lower for term in [
                "regulation cc", "funds availability", "12 cfr 229",
                "deposited funds", "check hold",
            ]),
            "reg-dd": any(term in content_lower for term in [
                "regulation dd", "truth in savings", "12 cfr 1030",
                "annual percentage yield", "apy",
            ]),
            "ncua": any(term in content_lower for term in [
                "ncua", "credit union", "supervisory committee",
                "member account verification",
            ]),
        }
        return detected

    def _is_template(self, content: str) -> bool:
        """Detect if a document is a template (unfilled placeholders)."""
        content_lower = content.lower()
        # Strong indicators (any one = template)
        strong_indicators = [
            "this template", "this is a template", "sample policy",
            "model language", "starting point", "[insert ",
            "[fill in", "[company name]", "[institution name]",
            "[credit union name]", "[firm name]",
        ]
        if any(t in content_lower for t in strong_indicators):
            return True
        # Weak indicators (need 2+)
        weak_indicators = [
            "[company", "[institution", "(company)", "{company}",
            "[your ", "(your ", "___", "[name of",
            "template", "placeholder", "customize",
        ]
        indicator_count = sum(1 for t in weak_indicators if t in content_lower)
        return indicator_count >= 2

    def analyze(
        self, file_path: str, regulation: str = "bsa-aml",
    ) -> dict:
        """
        Run full analysis on a document.

        Smart analysis that:
        - Auto-detects which regulations the document relates to
        - Only runs relevant checks (BSA checks on BSA documents, etc.)
        - Detects templates and adjusts severity accordingly

        Returns structured result with findings, scores, and metadata.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in (".pdf", ".docx", ".doc", ".html", ".htm", ".rtf"):
            content, vale_path = self._convert_to_markdown(file_path)
        else:
            content = path.read_text()
            vale_path = file_path

        all_findings: list[Finding] = []
        is_template = self._is_template(content)
        detected_regs = self._detect_document_type(content)

        # Document-level checks
        metadata_findings = self._check_metadata(content)
        if is_template:
            # Downgrade metadata errors to suggestions for templates
            metadata_findings = [
                Finding(
                    rule=f.rule, level="suggestion", message=f.message + " (template detected)",
                    regulation=f.regulation, citation=f.citation,
                )
                for f in metadata_findings
            ]
        all_findings.extend(metadata_findings)
        all_findings.extend(self._check_structure(content))

        # Regulation-specific checks — only run if document is relevant
        should_run_bsa = (
            regulation in ("bsa-aml", "all")
            and (regulation == "bsa-aml" or detected_regs.get("bsa-aml", False))
        )
        if should_run_bsa:
            all_findings.extend(self._check_bsa_requirements(content))

        # Vale linting
        vale_findings = self._run_vale(vale_path)
        all_findings.extend(vale_findings)

        # Extract citations and cross-references
        citations = self._extract_cfr_citations(content)
        cross_refs = self._extract_cross_references(content)

        # Count by level
        error_count = sum(1 for f in all_findings if f.level == "error")
        warning_count = sum(1 for f in all_findings if f.level == "warning")
        suggestion_count = sum(1 for f in all_findings if f.level == "suggestion")

        score = self._calculate_score(error_count, warning_count, suggestion_count)

        # Regulation coverage
        regulation_hits = Counter(f.regulation for f in all_findings)

        # Metadata check summary
        metadata_fields = ["effective date", "last reviewed", "next review date", "approved by", "version"]
        content_lower = content.lower()
        metadata_check = {
            field: field in content_lower for field in metadata_fields
        }

        return {
            "score": score,
            "total_findings": len(all_findings),
            "error_count": error_count,
            "warning_count": warning_count,
            "suggestion_count": suggestion_count,
            "findings": [asdict(f) for f in all_findings],
            "metadata_check": metadata_check,
            "regulation_coverage": dict(regulation_hits),
            "cfr_citations": citations,
            "cross_references": cross_refs,
            "detected_regulations": {k: v for k, v in detected_regs.items() if v},
            "is_template": is_template,
        }

    def cross_document_analysis(self, all_findings: list[dict]) -> dict:
        """
        Analyze findings across multiple documents.

        Identifies:
        - Inconsistencies between documents
        - Most common finding patterns
        - Regulation coverage gaps across the suite
        """
        files_with_errors = set()
        regulation_coverage = Counter()
        rule_frequency = Counter()
        critical_gaps = []

        for f in all_findings:
            if f.get("level") == "error":
                files_with_errors.add(f.get("source_file", "unknown"))
            regulation_coverage[f.get("regulation", "unknown")] += 1
            rule_frequency[f.get("rule", "unknown")] += 1

        # Identify most common issues
        top_issues = [
            {"rule": rule, "count": count}
            for rule, count in rule_frequency.most_common(10)
        ]

        # Identify regulation coverage gaps
        all_regs = set(self.REGULATIONS.keys())
        covered_regs = set(regulation_coverage.keys()) - {"common", "unknown"}
        uncovered = all_regs - covered_regs

        return {
            "documents_with_errors": len(files_with_errors),
            "regulation_coverage": dict(regulation_coverage),
            "uncovered_regulations": sorted(uncovered),
            "top_issues": top_issues,
            "total_unique_rules_triggered": len(rule_frequency),
        }
