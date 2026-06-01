#!/usr/bin/env python3
"""Run oasislmf.warmup serially to dodge an upstream parallel cache race.

The upstream `oasislmf.warmup` ProcessPoolExecutor parallelises 9 task
groups across CPU cores. Several of them call shared `@njit` functions
(notably `mv_read` in `oasislmf.pytools.common`). When two task groups
concurrently compile the same shared function with subtly different
signature variants (e.g. `class(float32)` vs `dtype(float32)`), the
cache index ends up in a mixed state and a later task fails type
inference at "Pass nopython_type_inference". Upstream is aware — the
`_compile_modelpy_gulpy_gulmc` task already chains gulpy+gulmc
sequentially with the same justification — but other task groups
(aalpy, eltpy, pltpy) can still race against modelpy_gulpy_gulmc.

Forcing serial execution at the task-group level eliminates the race.
The CLI doesn't expose `max_workers`, so we call the Python API
directly.
"""

import sys
import traceback

from oasislmf.warmup import ALL_SILENT_TASKS, warmup

print(
    f"Warming Numba JIT cache ({len(ALL_SILENT_TASKS)} tasks, serial, 2 passes) ...",
    flush=True,
)

# Pass 1: compile all task groups serially.
errors = warmup(max_workers=1)

# Pass 2: the subprocess pipelines inside each task (e.g. evepy|modelpy|gulpy)
# run as concurrent OS processes and can race to write the shared .nbi index,
# leaving some type variants missing after pass 1. A second serial pass finds
# those missing variants and fills them in, stabilising the cache.
if not errors:
    print("Pass 1 done, running pass 2 to recover subprocess race gaps ...", flush=True)
    errors = warmup(max_workers=1)

for name, err in errors.items():
    print(f"\nTASK FAILED: {name}", file=sys.stderr)
    traceback.print_exception(type(err), err, err.__traceback__, file=sys.stderr)

sys.exit(1 if errors else 0)
