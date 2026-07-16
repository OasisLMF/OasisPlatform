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
]

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
