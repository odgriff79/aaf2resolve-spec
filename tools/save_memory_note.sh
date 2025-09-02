#!/usr/bin/env bash
set -euo pipefail

TITLE_SLUG="${1:-note}"
TS="$(date -u +"%Y-%m-%dT%%H:%M:%SZ")"
OUT="docs/notes/MEMORY_${TS}_${TITLE_SLUG}.md"

mkdir -p docs/notes
BODY="$(cat)"

cat > "$OUT" <<EOF
# Memory Note — ${TITLE_SLUG}
Generated: ${TS}
Context: Working on branch \$(git branch --show-current)

${BODY}
EOF

echo "✅ Saved memory note: $OUT"
