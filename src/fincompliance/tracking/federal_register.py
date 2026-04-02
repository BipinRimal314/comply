"""
Federal Register Regulatory Change Tracker

Monitors the Federal Register API for changes to CFR sections
referenced in the institution's compliance documents. When a
regulation changes, identifies which internal documents need updating.

This is the recurring revenue feature — compliance never stops changing.

Usage:
    tracker = FederalRegisterTracker()
    changes = tracker.check_changes(["31 CFR 1020", "12 CFR 1005"])
    impact = tracker.assess_impact(changes, document_citations)
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError


@dataclass(frozen=True)
class RegulatoryChange:
    title: str
    document_number: str
    publication_date: str
    cfr_references: list[str]
    abstract: str
    url: str
    agency: str
    action_type: str  # "Final Rule", "Proposed Rule", "Notice"


# Financial regulatory agencies to monitor
MONITORED_AGENCIES = [
    "Financial Crimes Enforcement Network",
    "National Credit Union Administration",
    "Office of the Comptroller of the Currency",
    "Consumer Financial Protection Bureau",
    "Federal Deposit Insurance Corporation",
    "Securities and Exchange Commission",
    "Federal Trade Commission",
    "Federal Reserve System",
    "Federal Financial Institutions Examination Council",
]

# CFR titles relevant to financial compliance
FINANCIAL_CFR_TITLES = {
    "12": "Banks and Banking",
    "16": "Commercial Practices (FTC)",
    "17": "Securities and Exchanges (SEC)",
    "31": "Money and Finance (FinCEN/Treasury)",
}


class FederalRegisterTracker:
    """Track regulatory changes via the Federal Register API."""

    BASE_URL = "https://www.federalregister.gov/api/v1"

    def fetch_recent_changes(
        self,
        days_back: int = 30,
        cfr_title: str | None = None,
    ) -> list[RegulatoryChange]:
        """Fetch recent regulatory changes from the Federal Register API."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        params = {
            "conditions[publication_date][gte]": start_date.strftime("%Y-%m-%d"),
            "conditions[publication_date][lte]": end_date.strftime("%Y-%m-%d"),
            "conditions[type][]": ["RULE", "PRORULE", "NOTICE"],
            "per_page": 50,
            "order": "newest",
            "fields[]": [
                "title", "document_number", "publication_date",
                "cfr_references", "abstract", "html_url",
                "agencies", "type",
            ],
        }

        # Build URL
        query_parts = []
        for key, value in params.items():
            if isinstance(value, list):
                for v in value:
                    query_parts.append(f"{key}={v}")
            else:
                query_parts.append(f"{key}={value}")

        # Filter by relevant agencies
        for agency in MONITORED_AGENCIES:
            query_parts.append(
                f"conditions[agencies][]={agency.replace(' ', '+')}"
            )

        if cfr_title:
            query_parts.append(f"conditions[cfr][title]={cfr_title}")

        url = f"{self.BASE_URL}/documents.json?{'&'.join(query_parts)}"

        try:
            req = Request(url, headers={"Accept": "application/json"})
            with urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
        except (URLError, json.JSONDecodeError):
            return []

        changes = []
        for doc in data.get("results", []):
            cfr_refs = []
            for ref in doc.get("cfr_references", []):
                title = ref.get("title", "")
                parts = ref.get("parts", [])
                for part in parts:
                    cfr_refs.append(f"{title} CFR {part}")

            agencies = [
                a.get("name", "") for a in doc.get("agencies", [])
            ]

            changes.append(RegulatoryChange(
                title=doc.get("title", ""),
                document_number=doc.get("document_number", ""),
                publication_date=doc.get("publication_date", ""),
                cfr_references=cfr_refs,
                abstract=doc.get("abstract", "") or "",
                url=doc.get("html_url", ""),
                agency=", ".join(agencies),
                action_type=doc.get("type", ""),
            ))

        return changes

    def check_changes_for_citations(
        self,
        document_citations: list[str],
        days_back: int = 30,
    ) -> list[dict]:
        """
        Check if any CFR sections cited in compliance documents have changed.

        Takes a list of CFR citations extracted from the institution's documents
        and checks the Federal Register for recent changes to those sections.
        """
        # Fetch changes for relevant CFR titles
        all_changes = []
        for title in FINANCIAL_CFR_TITLES:
            changes = self.fetch_recent_changes(days_back=days_back, cfr_title=title)
            all_changes.extend(changes)

        # Match changes against document citations
        impacts = []
        for change in all_changes:
            matched_citations = []
            for doc_citation in document_citations:
                for change_ref in change.cfr_references:
                    # Fuzzy match: check if the CFR part numbers overlap
                    if self._citations_overlap(doc_citation, change_ref):
                        matched_citations.append(doc_citation)

            if matched_citations:
                impacts.append({
                    "change": {
                        "title": change.title,
                        "date": change.publication_date,
                        "type": change.action_type,
                        "agency": change.agency,
                        "url": change.url,
                        "abstract": change.abstract[:300],
                    },
                    "affected_citations": matched_citations,
                    "action_required": change.action_type == "Rule",
                    "review_recommended": True,
                })

        return impacts

    def _citations_overlap(self, doc_citation: str, change_ref: str) -> bool:
        """Check if a document citation overlaps with a regulatory change reference."""
        # Normalize both citations
        doc_norm = doc_citation.lower().replace(".", "").replace("§", "").strip()
        change_norm = change_ref.lower().replace(".", "").replace("§", "").strip()

        # Extract CFR part numbers
        import re
        doc_parts = re.findall(r'(\d+)\s*cfr\s*(\d+)', doc_norm)
        change_parts = re.findall(r'(\d+)\s*cfr\s*(\d+)', change_norm)

        for d_title, d_part in doc_parts:
            for c_title, c_part in change_parts:
                if d_title == c_title and d_part == c_part:
                    return True

        return False

    def generate_change_report(
        self,
        document_citations: list[str],
        days_back: int = 90,
    ) -> dict:
        """
        Generate a regulatory change impact report.

        This is the premium feature: "Which of my documents need updating
        because a regulation changed?"
        """
        impacts = self.check_changes_for_citations(document_citations, days_back)

        action_required = [i for i in impacts if i["action_required"]]
        review_only = [i for i in impacts if not i["action_required"]]

        return {
            "report_date": datetime.now().isoformat(),
            "period_days": days_back,
            "citations_monitored": len(document_citations),
            "changes_detected": len(impacts),
            "action_required": len(action_required),
            "review_recommended": len(review_only),
            "impacts": impacts,
        }
