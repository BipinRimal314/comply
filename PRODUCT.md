# Comply — Product Document

## Vision

The compliance documentation tool that credit unions and community banks actually need. Not another GRC dashboard. Not another workflow platform. A linter that reads your compliance docs and tells you what's wrong before the examiner does.

## Market

- **8,600 addressable institutions** (4,287 credit unions + ~3,953 community banks, 2025)
- **200-500 compliance documents per institution** maintained by 0-1 dedicated staff
- **$165K-$350K annual compliance spend** at small credit unions
- **$25K-$60K goes to compliance software** — our price ceiling is $1K-5K/month
- **$17-24B global RegTech market** growing at 19-23% CAGR

## Why Now

1. No compliance documentation linter exists. Not one. Anywhere.
2. AI hallucination rates in legal/compliance are 17-33% — pure AI tools won't be trusted. Hybrid (deterministic + AI) is the only architecture regulators accept.
3. Credit unions are consolidating (shrinking count) but survivors are growing in complexity. Compliance burden increases while staff doesn't.
4. NCUA examination cycles are accelerating. Institutions need examiner-ready documentation faster.

## Competitive Positioning

| Competitor | What they do | What they don't do |
|---|---|---|
| Ncontracts / CU PolicyPro | Template-based policy management | Don't lint, don't check quality, don't cross-reference |
| Vanta / Drata / Sprinto | Compliance automation (evidence collection) | Focus on SOC 2/ISO, not financial regs. Don't check document quality. |
| Compliance.ai / Corlytics | Regulatory change intelligence | Monitor regulations, don't check your documents against them |
| MetricStream / LogicGate | Enterprise GRC platforms | $25K-130K/yr, not accessible to credit unions |
| **Comply** | **Lints your actual documents against regulatory requirements** | **The only tool in this category** |

## Architecture

```
Document (PDF/Word/MD) → Format Conversion → Vale Linting → AI Analysis → Gap Report
                                                │                    │
                                          Deterministic         Fuzzy matching
                                          (60-70%)              (30-40%)
                                                │                    │
                                          Structure, terms,    Intent, cross-refs,
                                          required sections,   contradictions,
                                          prohibited language  regulatory mapping
```

## Revenue Model

### Open Source (Free)
- Vale rule package (FinCompliance)
- Regulatory requirements YAML library
- CLI tool

### Pro ($1,000/month)
- AI-powered substantive adequacy checks
- Cross-document consistency analysis
- Examiner-ready gap reports (PDF)
- Regulatory change alerts + document impact analysis

### Enterprise ($3,000-5,000/month)
- Multi-institution support (holding company / CUSO)
- Custom rule development
- Examination prep packages
- API access for integration with existing systems

## Go-to-Market

1. **Open source first.** Ship the Vale package. Get adoption from compliance officers who Google "compliance documentation linter."
2. **Community.** Credit unions talk to each other. One adoption leads to five referrals through state leagues and CUSOs.
3. **Content.** Blog posts on compliance documentation best practices, targeting long-tail SEO. "How to write a BSA/AML policy" gets searched by the exact people who need this tool.
4. **Conference circuit.** CUNA, state league meetings, compliance conferences. Demo the linter live against a real policy document. Every compliance officer in the room has felt the pain.
5. **Former examiner advisory board.** One former NCUA examiner endorsing this tool is worth more than any marketing spend.

## Phase Roadmap

### Phase 1: Open Source Vale Package (Weeks 1-4) — CURRENT
- 30-50 Vale rules across BSA/AML + Common
- Sample documents and test suite
- Regulatory requirements YAML library (BSA/AML)
- GitHub release + blog post announcement

### Phase 2: CLI + Format Conversion (Weeks 5-8)
- Python CLI wrapping Vale
- PDF/Word → Markdown conversion (MarkItDown / PyMuPDF4LLM)
- Cross-document reference checking (not possible in Vale alone)
- Gap report generation (Markdown → HTML/PDF)

### Phase 3: AI Augmentation (Weeks 9-16)
- Claude API integration for substantive adequacy checks
- Confidence scoring (deterministic = high confidence, AI = flagged for human review)
- Cross-document contradiction detection
- Regulatory-to-document mapping

### Phase 4: Regulatory Change Tracking (Weeks 17+)
- Monitor Federal Register for regulatory updates
- Map regulatory changes to affected internal documents
- Generate change impact reports
- This is the recurring-revenue hook — compliance never stops changing

## Success Metrics

| Metric | Month 1 | Month 3 | Month 6 | Month 12 |
|---|---|---|---|---|
| GitHub stars | 50 | 200 | 500 | 1,000 |
| Institutions using free tier | 5 | 20 | 50 | 200 |
| Pro subscribers | 0 | 2 | 10 | 30 |
| MRR | $0 | $2,000 | $10,000 | $30,000 |
| Regulation coverage | BSA/AML | +SOX, PCI | +GLBA, NCUA | All major |

## Connection to AI Trace Auditor

The AI Trace Auditor (built for EU AI Act compliance) shares ~30-40% architecture:
- YAML requirements registry → reuse pattern, new content
- Scoring/grading engine → reuse directly
- Report generation → reuse pattern
- CI/CD integration → reuse directly

The remaining 60-70% is new: document ingestion, natural language analysis, the regulatory YAML library (10-50x larger), and multi-document cross-referencing.

## The Moat

1. **The regulatory YAML library.** First machine-readable representation of US financial compliance requirements. This is the OSCAL equivalent for financial regulations. It takes months to build correctly and is the foundation everything else runs on.
2. **Vale rules developed with compliance officer feedback.** Rules tuned to real examination findings, not theoretical requirements.
3. **Open-source community.** Once compliance officers contribute rules from their own examination experiences, the knowledge compounds.
4. **Cross-document graph.** No other tool maps how your documents reference each other and what breaks when one changes.
