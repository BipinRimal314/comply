# Comply — Financial Compliance Documentation Linter

Open-source Vale package for linting financial compliance documentation. The first deterministic compliance doc checker for credit unions, community banks, and fintech companies.

## What this is

A Vale style package (`FinCompliance`) that checks compliance documents against regulatory requirements. Deterministic rules catch 60-70% of issues (structure, terminology, required sections, prohibited language). AI augmentation (Phase 2+) handles the remaining 30-40% (intent matching, cross-references, contradiction detection).

## Why this exists

- 8,600 credit unions and community banks in the US
- Each maintains 200-500 compliance documents with 0-1 dedicated compliance staff
- No compliance documentation linter exists anywhere
- Even 60-70% automated checking is a massive help (per EkLine boss, April 2026)
- Extends the AI Trace Auditor architecture to US financial regulations

## Project structure

```
comply/
├── .vale/styles/FinCompliance/    # The Vale package
│   ├── Common/                    # Cross-regulation rules
│   ├── BSA_AML/                   # Bank Secrecy Act / Anti-Money Laundering
│   ├── SOX/                       # Sarbanes-Oxley
│   ├── PCI_DSS/                   # Payment Card Industry Data Security Standard
│   ├── GLBA/                      # Gramm-Leach-Bliley Act
│   └── NCUA/                      # National Credit Union Administration
├── regulatory-requirements/       # YAML regulatory requirements library
├── examples/                      # Sample compliance documents
├── tests/                         # Test documents (pass/fail)
└── scripts/                       # Cross-document analysis (Phase 2)
```

## Development workflow

```bash
# Install Vale
brew install vale  # or download from vale.sh

# Run against a document
vale --config=.vale.ini examples/sample-bsa-policy.md

# Run tests
./scripts/run-tests.sh
```

## Phase roadmap

- **Phase 1 (current):** Pure Vale package. 30-50 rules for BSA/AML + Common. No AI dependency.
- **Phase 2:** CLI wrapper + document format conversion (PDF/Word → Markdown).
- **Phase 3:** AI augmentation via Claude API (substantive adequacy, cross-document consistency).
- **Phase 4:** Regulatory change tracking + cascade detection.

## Rules

- Every Vale rule must have a corresponding test (pass and fail document)
- Rules reference specific regulation sections (e.g., 31 USC 5311)
- Severity levels: error (must fix), warning (should fix), suggestion (consider)
- No false positive is acceptable for error-level rules
