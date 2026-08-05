"""Generate the standalone Redoc API pages with the OpenAPI spec inlined.

The Platform REST API reference is rendered by Redoc (the maintained upstream renderer),
vendored as a standalone bundle in ``_static/redoc/redoc.standalone.js`` — no Sphinx
extension, so no Sphinx version cap and no pkg_resources dependency.

Each ``_static/redoc/platform-v{1,2}.html`` page has its OpenAPI schema **inlined** (rather
than fetched via ``spec-url``) so the reference renders with no network — including when the
built site is opened directly as local files (``file://``), matching the offline/self-contained
build. The themed pages ``reference/platform_v{1,2}.md`` embed these via an isolated iframe.

Runs on the Sphinx ``config-inited`` event; also runnable standalone.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STATIC = os.path.abspath(os.path.join(HERE, os.pardir, "_static"))
SCHEMAS = os.path.join(STATIC, "schemas")
OUT = os.path.join(STATIC, "redoc")

PAGES = [("1", "Oasis Platform v1 API"), ("2", "Oasis Platform v2 API")]

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>body{{margin:0;padding:0}}</style>
</head>
<body>
  <div id="redoc"></div>
  <script type="application/json" id="spec">{spec}</script>
  <script src="./redoc.standalone.js"></script>
  <script>
    Redoc.init(
      JSON.parse(document.getElementById("spec").textContent),
      {{ hideDownloadButton: false, expandResponses: "200,201" }},
      document.getElementById("redoc")
    );
  </script>
</body>
</html>
"""


def _inline_safe(spec_text):
    """Make a JSON string safe to embed inside a <script type=application/json> block:
    neutralise ``</script>`` (via ``<``) and the U+2028 / U+2029 separators that are
    invalid in a JS string context."""
    return (spec_text
            .replace("<", "\\u003c")
            .replace(chr(0x2028), "\\u2028")
            .replace(chr(0x2029), "\\u2029"))


def generate():
    os.makedirs(OUT, exist_ok=True)
    for ver, title in PAGES:
        with open(os.path.join(SCHEMAS, f"platform-{ver}.json"), encoding="utf-8") as fh:
            spec = fh.read()
        with open(os.path.join(OUT, f"platform-v{ver}.html"), "w", encoding="utf-8") as fh:
            fh.write(TEMPLATE.format(title=title, spec=_inline_safe(spec)))
    return len(PAGES)


def run(app=None, config=None):
    n = generate()
    msg = f"[gen_redoc] wrote {n} standalone Redoc pages (spec inlined) -> _static/redoc/"
    if app is not None:
        from sphinx.util import logging
        logging.getLogger(__name__).info(msg)
    else:
        print(msg)


def setup(app):
    app.connect("config-inited", run)
    return {"parallel_read_safe": True, "parallel_write_safe": True}


if __name__ == "__main__":
    run()
