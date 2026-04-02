# Comply — Financial Compliance Documentation Linter

The first open-source linting package for financial compliance documentation. Built on [Vale](https://vale.sh).

## The Problem

Credit unions and community banks maintain 200-500 compliance documents with 0-1 dedicated compliance staff. When regulators examine these documents, vague language, missing sections, inconsistent terminology, and outdated references are findings that lead to enforcement actions. No tool currently checks compliance documents for these issues before the examiner does.

## What Comply Does

Comply is a Vale style package (`FinCompliance`) that catches compliance documentation issues deterministically:

- **Missing required elements** — Does your BSA/AML policy address all five pillars?
- **Weak commitment language** — "We will endeavor to comply" is not compliance
- **Vague regulatory references** — "Per applicable regulations" fails examiner scrutiny
- **Prohibited phrases** — "TBD", "under development", "budget permitting" in a compliance doc is a finding
- **Informal terminology** — "customer info" instead of "customer information"
- **Inconsistent date formats** — MM/DD/YY when your standard is YYYY-MM-DD
- **Abbreviation consistency** — Expand on first use, abbreviate thereafter

## Quick Start

```bash
# Install Vale
brew install vale  # macOS
# or: https://vale.sh/docs/vale-cli/installation/

# Clone this repo
git clone https://github.com/BipinRimal314/comply.git
cd comply

# Lint your compliance document
vale --config=.vale.ini path/to/your/bsa-policy.md
```

## Supported Regulations

| Regulation | Rules | Status |
|---|---|---|
| **Common** (cross-regulation) | 11 rules | Available |
| **BSA/AML** (Bank Secrecy Act / Anti-Money Laundering) | 2 rules + CLI checks | Available |
| **SOX** (Sarbanes-Oxley) | 2 rules | Available |
| **PCI-DSS** (Payment Card Industry) | 2 rules | Available |
| **GLBA** (Gramm-Leach-Bliley) | 1 rule | Available |
| **NCUA** (Credit Union specific) | 1 rule | Available |

## Example Output

```
tests/fail/weak-bsa-policy.md

 3:64   error    Risky language in BSA/AML document: 'when resources
                 permit'. Examiners interpret this as non-compliance.
 5:20   error    Risky language in BSA/AML document: 'under development'.
 5:42   error    Risky language in BSA/AML document: 'we plan to implement'.
 9:22   warning  Vague regulatory reference: 'per applicable regulations'.
                 Include specific section/part numbers.
 19:11  warning  Date format appears inconsistent. Use YYYY-MM-DD or
                 Month DD, YYYY consistently.

✖ 9 errors, 15 warnings and 2 suggestions in 1 file.
```

## Architecture

**Phase 1 (current):** Pure Vale rules. Deterministic. No AI. No API keys. Runs offline.

**Phase 2:** CLI wrapper with document format conversion (PDF/Word → Markdown via MarkItDown).

**Phase 3:** AI augmentation via Claude API for substantive adequacy checks, cross-document consistency, and regulatory change impact analysis.

**Phase 4:** Regulatory change tracking. When a regulation updates, automatically identify which internal documents need revision.

## Regulatory Requirements Library

`regulatory-requirements/` contains machine-readable YAML definitions of regulatory requirements. This is the first open-source equivalent of NIST OSCAL for financial regulations. Currently covers BSA/AML (31 CFR Chapter X).

## Contributing

We need help with:
- Additional regulation rule packages (SOX, PCI-DSS, GLBA)
- Testing against real compliance documents
- Regulatory requirements YAML for additional frameworks
- False positive reduction

## License

MIT
