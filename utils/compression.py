"""Gzip responses on the way out.

The app served everything uncompressed. That is invisible on a laptop on
home wifi and brutal everywhere else: the AI SDE bank alone was a 3 MB JSON
body, and the ordinary pages run 120-170 KB of HTML apiece. Text compresses
by roughly 85-90%, so this is the cheapest large win available — no markup
changes, no cache invalidation, nothing to keep in sync.

Deliberately stdlib rather than flask-compress: it is ~40 lines, the
dependency list is already long, and the rules below are ones we want to
read and own rather than inherit.

WHAT IS NOT COMPRESSED, and why each exclusion is load-bearing:

  * Anything the client did not say it could decode. No `gzip` in
    Accept-Encoding means send it plain.
  * Anything already encoded. Double-gzipping produces a body no browser
    will unwrap.
  * Anything that is not text. JPEGs, PNGs and woff2 are compressed
    already; running deflate over them burns CPU to add bytes.
  * Small bodies. Below a couple of KB the gzip header and the CPU cost
    outweigh the saving, and most of our API replies are a status blob.
  * `direct_passthrough` responses. That is Flask streaming a file handle;
    touching `.data` would buffer the whole thing into memory, which is
    exactly what streaming exists to avoid.
  * Anything that is not a plain 200. A 206 carries a byte range that
    compression would invalidate, and a 304 has no body to compress.

`Vary: Accept-Encoding` is not optional. Without it a shared cache can
hand a gzipped body to a client that never asked for one.
"""
import gzip

#: Below this, compression costs more than it saves.
MIN_BYTES = 1024

#: Text-ish content types worth compressing. Matched as a prefix, so
#: "application/json; charset=utf-8" hits "application/json".
COMPRESSIBLE = (
    "text/html", "text/css", "text/plain", "text/xml",
    "application/json", "application/javascript", "text/javascript",
    "application/manifest+json", "image/svg+xml",
)

#: 6 is zlib's default and the right trade here. 9 costs noticeably more
#: CPU for around 1% fewer bytes, which on a single-worker dyno is a bad
#: swap — the time is better spent answering the next request.
LEVEL = 6


def _compressible(response):
    ctype = (response.content_type or "").split(";")[0].strip().lower()
    return any(ctype == c for c in COMPRESSIBLE)


def gzip_response(response, accept_encoding):
    """Gzip `response` in place when every rule above allows it.

    Returns the same response object either way, so it can be dropped
    straight into an `after_request` chain.
    """
    if "gzip" not in (accept_encoding or "").lower():
        return response
    if response.status_code != 200:
        return response
    if response.direct_passthrough:
        return response
    if response.headers.get("Content-Encoding"):
        return response
    if not _compressible(response):
        return response

    data = response.get_data()
    if len(data) < MIN_BYTES:
        return response

    # mtime=0 keeps the output byte-identical for identical input, so an
    # ETag computed over the compressed body stays stable across restarts.
    packed = gzip.compress(data, LEVEL, mtime=0)
    # Refuse to make things worse. Rare for text, but a tiny or already
    # dense body can come out larger, and shipping that would be silly.
    if len(packed) >= len(data):
        return response

    response.set_data(packed)
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = str(len(packed))
    return response


def init_app(app):
    """Register the after_request hook."""
    @app.after_request
    def _gzip(response):                       # pragma: no cover - trivial glue
        from flask import request
        response.headers.setdefault("Vary", "Accept-Encoding")
        vary = response.headers.get("Vary", "")
        if "accept-encoding" not in vary.lower():
            response.headers["Vary"] = f"{vary}, Accept-Encoding".strip(", ")
        try:
            return gzip_response(response, request.headers.get("Accept-Encoding"))
        except Exception:
            # A body we cannot compress must still be served. Never let an
            # optimisation take a page down.
            return response
    return app
