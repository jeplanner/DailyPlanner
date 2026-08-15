"""Gzip on the way out — the rules that matter, not the plumbing."""
import gzip
import json

from utils.compression import MIN_BYTES, gzip_response


class _Resp:
    """Minimal stand-in with the Response surface gzip_response touches."""

    def __init__(self, data=b"", ctype="application/json", status=200,
                 encoding=None, passthrough=False):
        self._data = data
        self.content_type = ctype
        self.status_code = status
        self.direct_passthrough = passthrough
        self.headers = {}
        if encoding:
            self.headers["Content-Encoding"] = encoding

    def get_data(self):
        return self._data

    def set_data(self, d):
        self._data = d


BIG = json.dumps([{"answer": "the quick brown fox " * 20} for _ in range(40)]).encode()


def test_a_large_json_body_is_compressed_and_round_trips():
    r = gzip_response(_Resp(BIG), "gzip, deflate, br")
    assert r.headers["Content-Encoding"] == "gzip"
    assert gzip.decompress(r.get_data()) == BIG
    assert int(r.headers["Content-Length"]) == len(r.get_data())
    # Repetitive JSON is the case this exists for; anything less than a
    # 5x saving means the rules above are not doing their job.
    assert len(r.get_data()) < len(BIG) / 5


def test_nothing_is_compressed_for_a_client_that_cannot_decode_it():
    for accept in ("", None, "deflate, br", "identity"):
        r = gzip_response(_Resp(BIG), accept)
        assert "Content-Encoding" not in r.headers, accept
        assert r.get_data() == BIG


def test_an_already_encoded_body_is_left_alone():
    """Double-gzipping produces something no browser will unwrap."""
    pre = gzip.compress(BIG)
    r = gzip_response(_Resp(pre, encoding="gzip"), "gzip")
    assert r.get_data() == pre


def test_streaming_responses_are_never_buffered():
    """direct_passthrough is Flask handing back a file handle. Reading .data
    would pull the whole file into memory — the exact thing streaming avoids."""
    r = gzip_response(_Resp(BIG, passthrough=True), "gzip")
    assert "Content-Encoding" not in r.headers


def test_binary_and_partial_and_small_bodies_are_skipped():
    # Already-compressed formats: deflate would add bytes, not remove them.
    for ctype in ("image/png", "image/jpeg", "font/woff2", "application/pdf"):
        assert "Content-Encoding" not in gzip_response(_Resp(BIG, ctype), "gzip").headers, ctype
    # A 206 carries a byte range that compression invalidates; a 304 has no body.
    for status in (206, 304, 404, 500):
        assert "Content-Encoding" not in gzip_response(_Resp(BIG, status=status), "gzip").headers
    # Below the floor the gzip header costs more than it saves.
    small = b'{"ok":true}'
    assert len(small) < MIN_BYTES
    assert "Content-Encoding" not in gzip_response(_Resp(small), "gzip").headers


def test_the_real_app_compresses_pages_and_declares_it_varies(auth_client):
    r = auth_client.get("/ai-sde", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers.get("Content-Encoding") == "gzip"
    assert "accept-encoding" in r.headers.get("Vary", "").lower(), \
        "a shared cache could serve a gzipped body to a client that cannot read it"
    assert b"<title>" in gzip.decompress(r.get_data())


def test_a_client_without_gzip_still_gets_a_readable_page(auth_client):
    r = auth_client.get("/ai-sde", headers={"Accept-Encoding": "identity"})
    assert r.status_code == 200
    assert "Content-Encoding" not in r.headers
    assert b"<title>" in r.get_data()
