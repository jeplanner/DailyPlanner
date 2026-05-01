"""In-app classifier for the Tasks Bucket.

Multinomial Naive Bayes over whole-sentence example data — no external
LLM, no per-token weight rules. The model is built on the fly from
`tasks_bucket_examples` (global seed sentences shipped with the app +
the user's own past classifications appended as `source = 'user'`).

Why Bayes over the keyword-counting approach we tried first:
  Keyword scoring treats each token independently. A line like
  "buy stocks" matches "buy" → Grocery and "stocks" → Portfolio with
  comparable weight, and the additive sum can flip on noise. Bayes
  evaluates the joint log-probability of the whole sentence given each
  category, so distinguishing tokens dominate and noise tokens cancel.
  And the model improves automatically every time the user
  reclassifies — `learn()` just appends another labelled example.

Performance: examples are loaded once per user and cached in-process
under `_models`. Calling `learn()` evicts the cache so the next
`classify()` rebuilds from the new corpus.
"""

import logging
import math
import re
import threading
from collections import Counter, defaultdict

from supabase_client import get, post

logger = logging.getLogger("daily_plan")

CATEGORIES = ["Health", "Grocery", "Portfolio", "Checklist", "TravelReads", "ProjectTask"]

# A category needs to beat the runner-up by at least this much
# log-probability to win — otherwise the line goes to Unclassified
# so the user can label it.
MIN_LOG_GAP = 1.0

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_URL_RE = re.compile(r"https?://", re.I)
_MONEY_RE = re.compile(
    r"(\$|₹|£|€)\s?\d|\b\d+\s?(usd|inr|eur|gbp|cr|crore|lakh|lakhs|k)\b",
    re.I,
)
_TICKER_RE = re.compile(r"\b[A-Z]{3,5}\b")  # e.g. AAPL, NIFTY, INFY

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at",
    "for", "with", "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "i", "me", "my", "you", "we", "us", "our",
    "they", "them", "their", "this", "that", "these", "those", "it",
    "its", "as", "by", "from", "up", "down", "out", "off", "so", "if",
    "then", "than", "also", "just", "very", "not", "no", "yes", "ok",
    "have", "has", "had", "will", "would", "should", "can", "could",
    "get", "got", "go", "going", "need", "want", "wanna", "gonna",
    "today", "tomorrow", "tonight", "morning", "evening", "afternoon",
    "again", "later", "soon", "next", "last", "every", "some", "any",
    "one", "two", "three", "all", "more", "less", "few",
}

# Cached trained models keyed by user_id. None entry → rebuild needed.
_models = {}
_models_lock = threading.Lock()


def _tokens(text):
    """Lowercase tokens with stop-words and bare digits removed.
    Adds two special tokens — <url> and <money> — so URL- or money-shaped
    inputs influence the model the same way real words do."""
    if not text:
        return []
    out = [t for t in _TOKEN_RE.findall(text.lower())
           if t not in _STOPWORDS and not t.isdigit()]
    if _URL_RE.search(text):
        out.append("<url>")
    if _MONEY_RE.search(text) or _TICKER_RE.search(text):
        out.append("<money>")
    return out


class _NBModel:
    """Multinomial Naive Bayes with Laplace smoothing.

    Built once per user from the union of global seed examples and the
    user's own labelled history.
    """

    def __init__(self, examples):
        self.cat_doc_count = Counter()
        self.cat_token_total = Counter()
        self.cat_token_freq = defaultdict(Counter)
        self.vocab = set()
        for cat, text in examples:
            if cat not in CATEGORIES:
                continue
            toks = _tokens(text)
            if not toks:
                continue
            self.cat_doc_count[cat] += 1
            self.cat_token_total[cat] += len(toks)
            for t in toks:
                self.cat_token_freq[cat][t] += 1
                self.vocab.add(t)
        self.total_docs = sum(self.cat_doc_count.values())

    @property
    def trained(self):
        return self.total_docs > 0 and bool(self.vocab)

    def classify(self, text):
        if not self.trained:
            return None, 0.0, []
        toks = _tokens(text)
        if not toks:
            return None, 0.0, []

        v_size = len(self.vocab)
        scores = {}
        evidence = {}

        for cat, ndocs in self.cat_doc_count.items():
            log_prior = math.log(ndocs / self.total_docs)
            cat_total = self.cat_token_total[cat]
            log_p = log_prior
            cat_evidence = []
            for t in toks:
                freq = self.cat_token_freq[cat].get(t, 0)
                # Laplace smoothing: every token has a non-zero probability
                # so an unseen word doesn't zero out an entire category.
                p = (freq + 1) / (cat_total + v_size)
                log_p += math.log(p)
                if freq > 0:
                    cat_evidence.append({"keyword": t, "category": cat, "weight": freq})
            scores[cat] = log_p
            evidence[cat] = cat_evidence

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_cat, top_lp = ranked[0]
        runner_lp = ranked[1][1] if len(ranked) > 1 else top_lp - 10
        gap = top_lp - runner_lp

        # Confidence: 0..1 derived from how decisively the top category
        # beats the runner-up. Sigmoid keeps it bounded.
        confidence = round(1.0 / (1.0 + math.exp(-gap)), 2)

        winner_evidence = evidence.get(top_cat, [])
        # Refuse to commit if the gap is too small, or if no observed
        # token actually appeared in the winner's corpus (i.e. all tokens
        # were unseen and the prior alone won).
        if gap < MIN_LOG_GAP or not winner_evidence:
            return None, confidence, winner_evidence
        return top_cat, confidence, winner_evidence


def _load_examples(user_id):
    """Fetch every example sentence relevant to this user — global seeds
    plus the user's own labelled history."""
    try:
        rows = get(
            "tasks_bucket_examples",
            params={
                "or": f"(user_id.is.null,user_id.eq.{user_id})",
                "select": "category,text",
                "limit": "10000",
            },
        ) or []
    except Exception:
        logger.exception("Failed to load classifier examples")
        return []
    return [(r.get("category"), r.get("text") or "") for r in rows]


def _get_model(user_id):
    with _models_lock:
        cached = _models.get(user_id)
        if cached is not None:
            return cached
    # Build outside the lock so concurrent users don't queue.
    examples = _load_examples(user_id)
    model = _NBModel(examples)
    with _models_lock:
        _models[user_id] = model
    return model


def _invalidate(user_id):
    with _models_lock:
        _models.pop(user_id, None)


def classify(user_id, text):
    """Return (category|None, confidence, matched_tokens).

    matched_tokens is a list of {keyword, category, weight} for the
    *winning* category — used by the UI's "why this category?" tooltip.
    """
    model = _get_model(user_id)
    return model.classify(text)


def learn(user_id, text, category):
    """Append a labelled example to the user's training corpus.

    The next classification rebuilds the cached model from the larger
    corpus, so the user's vocabulary is folded in without any explicit
    retraining step.
    """
    if category not in CATEGORIES:
        return
    text = (text or "").strip()
    if not text:
        return
    try:
        post(
            "tasks_bucket_examples",
            {
                "user_id": user_id,
                "category": category,
                "text": text[:500],
                "source": "user",
            },
        )
    except Exception:
        logger.exception("learn(): example insert failed")
        return
    _invalidate(user_id)
