# Configuration for the OasisPlatform documentation.
#
# OasisPlatform owns the docs for running Oasis as a platform: deployment,
# container/Kubernetes configuration, distributed execution, the web UI and the
# REST API. Built with the same Furo + MyST toolchain as the OasisLMF docs and
# pulled into the aggregated Oasis site via intersphinx.
import os
import sys

sys.path.insert(0, os.path.abspath("_ext"))

project = "Oasis Platform"
copyright = "Oasis Loss Modelling Framework"
author = "OasisLMF"

extensions = [
    "myst_parser",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinx.ext.intersphinx",
    "gen_redoc",   # generate the standalone Redoc API pages (spec inlined) at build time
]

# -- REST API reference (Redoc) ---------------------------------------------
# The Platform v1/v2 OpenAPI schemas are persisted in-repo under _static/schemas/
# and rendered with Redoc — the maintained upstream renderer, vendored as a
# standalone bundle in _static/redoc/ (no Sphinx extension, so no Sphinx version
# cap and no pkg_resources dependency; fully offline/self-contained). The themed
# pages reference/platform_v{1,2}.md embed the standalone _static/redoc/*.html via
# an isolated iframe. Schemas are generated from the Django app with
# drf-spectacular (.github/workflows/build-schema.yml); a CI step should
# regenerate and commit them on release so they stay in step with the code.

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
# -- Oasis shared branding (logo, palette, home link) -----------------------
import os as _os_brand
if globals().get("html_theme") == "furo":
    if "_static" not in (globals().get("html_static_path") or []):
        html_static_path = list(globals().get("html_static_path") or []) + ["_static"]
    try:
        html_theme_options
    except NameError:
        html_theme_options = {}
    html_theme_options.setdefault("light_logo", "OASIS_LMF_COLOUR.png")
    html_theme_options.setdefault("dark_logo", "OASIS_LMF_WHITE.png")
    _lcv = html_theme_options.setdefault("light_css_variables", {})
    _lcv.setdefault("color-brand-primary", "#862633")
    _lcv.setdefault("color-brand-content", "#d22630")
    _lcv.setdefault("font-stack", "Raleway, sans-serif")
    _dcv = html_theme_options.setdefault("dark_css_variables", {})
    _dcv.setdefault("color-brand-primary", "#e2919b")
    _dcv.setdefault("color-brand-content", "#ef8b93")
    _home = _os_brand.environ.get("OASIS_DOCS_HOME", "https://oasislmf.github.io/index.html")
    html_theme_options.setdefault(
        "announcement",
        '<a href="' + _home + '" style="color:inherit;font-weight:600;text-decoration:none">'
        '&#8962; Oasis documentation home</a>')
    if "https://fonts.googleapis.com/css?family=Raleway" not in (globals().get("html_css_files") or []):
        html_css_files = list(globals().get("html_css_files") or []) + ["https://fonts.googleapis.com/css?family=Raleway"]
