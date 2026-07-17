# Configuration for the OasisPlatform documentation.
#
# OasisPlatform owns the docs for running Oasis as a platform: deployment,
# container/Kubernetes configuration, distributed execution, the web UI and the
# REST API. Built with the same Furo + MyST toolchain as the OasisLMF docs and
# pulled into the aggregated Oasis site via intersphinx.

project = "Oasis Platform"
copyright = "Oasis Loss Modelling Framework"
author = "OasisLMF"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.redoc",   # render the OpenAPI schemas
]

# -- REST API reference (redoc) ---------------------------------------------
# The Platform v1/v2 OpenAPI schemas are persisted in-repo under
# _static/schemas/ and rendered as interactive redoc pages. They are generated
# from the Django app with drf-spectacular (.github/workflows/build-schema.yml);
# a CI step should regenerate and commit them on release so they stay in step
# with the code (replacing the manually-committed snapshot).
redoc = [
    {
        "name": "Platform v2 API",
        "page": "reference/platform_v2",
        "spec": "_static/schemas/platform-2.json",
        "embed": True,
    },
    {
        "name": "Platform v1 API",
        "page": "reference/platform_v1",
        "spec": "_static/schemas/platform-1.json",
        "embed": True,
    },
]
# No redoc_uri: use the redoc.js bundled with sphinxcontrib-redoc (vendored into
# _static at build). This keeps the docs self-contained — no runtime CDN dependency
# and no network needed at build time.

source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

myst_enable_extensions = ["colon_fence", "deflist", "substitution", "tasklist"]
myst_heading_anchors = 3

# Cross-link to the other Oasis docs sites (populated as they publish).
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}
intersphinx_disabled_reftypes = ["*"]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "Oasis Platform"
html_static_path = ["_static"]

# Anchor links in the migrated ktools/GenerateDocs prose are noisy; keep the log usable.
linkcheck_ignore = [r"https://github\.com/.*#.*"]


# -- Cross-component links (intersphinx, aggregated site) --------------------
# The GenerateDocs orchestrator sets OASIS_INTERSPHINX_MAP (JSON) to point cross-references at
# the other components' built inventories; standalone builds add nothing. Use explicit roles,
# e.g. {external+ord:doc}`reference/tables` or :external+oed:ref:`some-label`.
import json as _ix_json, os as _ix_os
if "sphinx.ext.intersphinx" not in extensions:
    extensions = list(extensions) + ["sphinx.ext.intersphinx"]
try:
    intersphinx_mapping
except NameError:
    intersphinx_mapping = {}
intersphinx_mapping.update({
    _k: (_v[0], _v[1])
    for _k, _v in _ix_json.loads(_ix_os.environ.get("OASIS_INTERSPHINX_MAP", "{}")).items()
})
