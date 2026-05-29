#!/bin/bash
# Test that the Numba JIT cache baked into a model_worker image is valid.
#
# Reruns the oasislmf warmup inside the image and checks that no new
# compilations occur — if the cache is valid every function is loaded from
# disk and no new .nbc files are written.
#
# Usage:
#   ./scripts/test-jit-cache.sh [image]
#
# Example:
#   ./scripts/test-jit-cache.sh coreoasis/model_worker:dev
#   ./scripts/test-jit-cache.sh coreoasis/github-actions:model_worker-<sha>

set -euo pipefail

IMAGE="${1:-coreoasis/model_worker:dev}"

echo "Testing JIT cache validity in: ${IMAGE}"
echo ""

# Write the warmup runner to a temp file to avoid single-quote conflicts
# when embedding Python inside a bash -c '...' string.
WARMUP_SCRIPT=$(mktemp /tmp/warmup_test_XXXXXX.py)
trap 'rm -f "$WARMUP_SCRIPT"' EXIT
chmod 644 "$WARMUP_SCRIPT"

cat > "$WARMUP_SCRIPT" << 'PYEOF'
import sys
import traceback
from oasislmf.warmup import warmup

errors = warmup(max_workers=1)
for name, err in errors.items():
    print(f'TASK FAILED: {name}', file=sys.stderr)
    traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)
sys.exit(1 if errors else 0)
PYEOF

docker run --rm \
    -v "${WARMUP_SCRIPT}:/tmp/warmup_test.py:ro" \
    --entrypoint bash \
    "${IMAGE}" -c '
    set -euo pipefail

    cache_dir="${NUMBA_CACHE_DIR:-/home/worker/.numba_jit_cache}"

    if [ ! -d "$cache_dir" ]; then
        echo "FAIL: NUMBA_CACHE_DIR does not exist: $cache_dir"
        exit 1
    fi

    snapshot() {
        find "$cache_dir" \( -name "*.nbi" -o -name "*.nbc" \) \
            -exec stat -c "%n %s" {} \; 2>/dev/null | sort
    }

    before=$(snapshot)
    nbi_count=$(echo "$before" | grep -c "\.nbi" || true)
    nbc_count=$(echo "$before" | grep -c "\.nbc" || true)
    echo "Cache before warmup: ${nbi_count} .nbi  ${nbc_count} .nbc"

    if [ "$nbi_count" -eq 0 ]; then
        echo "FAIL: no .nbi files found — JIT cache was not baked into the image"
        exit 1
    fi

    cd /tmp
    python3 /tmp/warmup_test.py

    after=$(snapshot)
    nbi_after=$(echo "$after" | grep -c "\.nbi" || true)
    nbc_after=$(echo "$after" | grep -c "\.nbc" || true)
    echo "Cache after  warmup: ${nbi_after} .nbi  ${nbc_after} .nbc"
    echo ""

    if [ "$before" = "$after" ]; then
        echo "PASS: cache is valid — warmup produced no new compilations"
    else
        echo "FAIL: cache was invalid — new or changed files detected:"
        diff <(echo "$before") <(echo "$after") || true
        exit 1
    fi
'
