#!/bin/bash
# Comply — Test Harness
# Validates that Vale rules and Python CLI produce expected results.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PASS=0
FAIL=0
TOTAL=0

pass() {
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
    echo "  ✓ $1"
}

fail() {
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
    echo "  ✗ $1"
    echo "    Expected: $2"
    echo "    Got: $3"
}

echo "═══════════════════════════════════════════"
echo "  Comply Test Suite"
echo "═══════════════════════════════════════════"
echo ""

# ── Test 1: Good BSA policy should have 0 errors ──
echo "Test 1: Good BSA policy (0 errors expected)"
ERRORS=$(PYTHONPATH=src python3 src/fincompliance/cli.py examples/sample-bsa-policy.md --format json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
errors = sum(1 for f in data.get('document_findings', []) if f['level'] == 'error')
vale = data.get('vale_findings', {})
for filepath, alerts in vale.items():
    errors += sum(1 for a in alerts if a.get('Severity','').lower() == 'error')
print(errors)
")
if [ "$ERRORS" = "0" ]; then
    pass "Good BSA policy: 0 errors"
else
    fail "Good BSA policy: expected 0 errors" "0" "$ERRORS"
fi

# ── Test 2: Weak BSA policy should have errors ──
echo "Test 2: Weak BSA policy (errors expected)"
ERRORS=$(PYTHONPATH=src python3 src/fincompliance/cli.py tests/fail/weak-bsa-policy.md --format json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
errors = sum(1 for f in data.get('document_findings', []) if f['level'] == 'error')
vale = data.get('vale_findings', {})
for filepath, alerts in vale.items():
    errors += sum(1 for a in alerts if a.get('Severity','').lower() == 'error')
print(errors)
")
if [ "$ERRORS" -gt "5" ]; then
    pass "Weak BSA policy: $ERRORS errors detected"
else
    fail "Weak BSA policy: expected >5 errors" ">5" "$ERRORS"
fi

# ── Test 3: Weak BSA missing metadata ──
echo "Test 3: Missing metadata detection"
METADATA_ERRORS=$(PYTHONPATH=src python3 src/fincompliance/cli.py tests/fail/weak-bsa-policy.md --format json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
count = sum(1 for f in data.get('document_findings', []) if f['rule'] == 'DocumentMetadata')
print(count)
")
if [ "$METADATA_ERRORS" -ge "4" ]; then
    pass "Missing metadata: $METADATA_ERRORS fields detected"
else
    fail "Missing metadata detection" ">=4" "$METADATA_ERRORS"
fi

# ── Test 4: Weak BSA missing pillars ──
echo "Test 4: Missing BSA pillars detection"
PILLAR_ERRORS=$(PYTHONPATH=src python3 src/fincompliance/cli.py tests/fail/weak-bsa-policy.md --format json 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
count = sum(1 for f in data.get('document_findings', []) if f['rule'] == 'BSA_FivePillars')
print(count)
")
if [ "$PILLAR_ERRORS" -ge "3" ]; then
    pass "Missing BSA pillars: $PILLAR_ERRORS detected"
else
    fail "Missing BSA pillars detection" ">=3" "$PILLAR_ERRORS"
fi

# ── Test 5: SOX control deficiencies caught ──
echo "Test 5: SOX control deficiency detection"
SOX_ERRORS=$(vale --config=.vale.ini --output=JSON tests/fail/weak-sox-controls.md 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
count = 0
for filepath, alerts in data.items():
    count += sum(1 for a in alerts if 'SOX_Control' in a.get('Check', ''))
print(count)
")
if [ "$SOX_ERRORS" -ge "3" ]; then
    pass "SOX deficiencies: $SOX_ERRORS detected"
else
    fail "SOX deficiency detection" ">=3" "$SOX_ERRORS"
fi

# ── Test 6: PCI prohibited storage caught ──
echo "Test 6: PCI prohibited storage detection"
PCI_ERRORS=$(vale --config=.vale.ini --output=JSON tests/fail/weak-pci-policy.md 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
count = 0
for filepath, alerts in data.items():
    count += sum(1 for a in alerts if 'PCI_' in a.get('Check', ''))
print(count)
")
if [ "$PCI_ERRORS" -ge "5" ]; then
    pass "PCI violations: $PCI_ERRORS detected"
else
    fail "PCI violation detection" ">=5" "$PCI_ERRORS"
fi

# ── Test 7: JSON output format works ──
echo "Test 7: JSON output format"
JSON_VALID=$(PYTHONPATH=src python3 src/fincompliance/cli.py examples/sample-bsa-policy.md --format json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print('valid' if 'document_findings' in data and 'vale_findings' in data else 'invalid')
except:
    print('invalid')
")
if [ "$JSON_VALID" = "valid" ]; then
    pass "JSON output: valid structure"
else
    fail "JSON output format" "valid" "$JSON_VALID"
fi

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  Results: $PASS passed, $FAIL failed (of $TOTAL)"
echo "═══════════════════════════════════════════"

if [ "$FAIL" -gt "0" ]; then
    exit 1
fi
