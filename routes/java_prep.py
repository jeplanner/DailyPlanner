"""Java bank — routes.

  /java                    the browsable bank
  /java/quiz               multiple choice, hand-written distractors
  /api/java                the THIN list (headers only)
  /api/java/entry/<id>     one full entry, fetched when a card is opened
  /api/java/quiz           the quiz payload

WHY THE LIST IS THIN AT 28 ENTRIES, WHEN IT WOULD FIT IN ONE PAYLOAD TODAY.
The AI/SDE bank shipped every field of every entry on page load and reached a
3 MB JSON body before anyone noticed, because the list screen renders none of
it — every card is collapsed until clicked. Fixing it later meant reworking
the route, the template and the search. This bank is small now and its entries
carry ten-section deep dives, so the same growth is coming. The split costs
nothing to write today and cannot be retrofitted cheaply.

PROGRESS IS CLIENT-SIDE, on purpose. "I have studied this" is a personal note,
not shared data, and putting it in localStorage means no table, no migration
and no round trip on every checkbox. If it ever needs to sync across devices
that is a real decision to make then, not a default to inherit now.
"""
import logging

from flask import Blueprint, jsonify, render_template, request

from services.login_service import login_required

import ai_sde_summary
import java_bank

logger = logging.getLogger("daily_plan")

java_prep_bp = Blueprint("java_prep", __name__)


#: What the collapsed card header and the filters actually read. Everything
#: else arrives per-card from /api/java/entry/<id>.
_LIST_FIELDS = ("title", "cat", "difficulty", "frequency", "version")

#: The card summary. Derived from `plain` rather than `answer`, because for
#: a LANGUAGE bank the plain-English answer IS the summary — it was written
#: to be the first thing read. Shipped in the list rather than fetched
#: separately: 45 entries of a few hundred characters is a few KB, where the
#: AI/SDE bank's 1,120 made it a 50 KB decision.

#: Held as an explicit list rather than "everything not in _LIST_FIELDS", so
#: that adding a field to the bank is a conscious decision about which side of
#: the line it falls on rather than a silent payload regression.
_BODY_FIELDS = ("plain", "answer", "code", "output", "gotcha", "bytecode",
                "example", "complexity", "pitfalls", "followups", "mnemonic",
                "diagram", "tags", "examples")


def _build_list():
    """The thin list, built once at import.

    The bank is a static Python literal — it cannot change between requests,
    so rebuilding this per request would be pure waste.
    """
    rows = []
    for i, e in enumerate(java_bank.ENTRIES):
        row = {"id": f"j{i}"}
        row.update({k: e.get(k, "") for k in _LIST_FIELDS})
        # Flags the filters use, computed once rather than shipping the fields
        # they are derived from.
        row["has_code"] = bool(e.get("code"))
        row["has_trap"] = bool(e.get("gotcha"))
        row["has_deep"] = bool(e.get("examples"))
        row["cat_label"] = java_bank.CATEGORIES.get(e["cat"], e["cat"])
        row["summary"] = ai_sde_summary.summarise_text(e.get("plain"))
        rows.append(row)
    return rows


_LIST = _build_list()
_BY_ID = {f"j{i}": e for i, e in enumerate(java_bank.ENTRIES)}


@java_prep_bp.route("/java", methods=["GET"])
@login_required
def java_page():
    return render_template("java.html")


@java_prep_bp.route("/java/quiz", methods=["GET"])
@login_required
def java_quiz_page():
    return render_template("java_quiz.html")


@java_prep_bp.route("/api/java", methods=["GET"])
@login_required
def java_list():
    """Headers only. Card bodies come from /api/java/entry/<id>."""
    return jsonify({
        # CATEGORY_ORDER, not CATEGORIES.keys() sorted — the ladder is the
        # teaching order and shuffling it into alphabetical would put
        # concurrency before basics.
        "categories": [{"key": k, "label": java_bank.CATEGORIES[k]}
                       for k in java_bank.CATEGORY_ORDER],
        "entries": _LIST,
        "total": len(_LIST),
    })


@java_prep_bp.route("/api/java/entry/<entry_id>", methods=["GET"])
@login_required
def java_entry(entry_id):
    e = _BY_ID.get(entry_id)
    if not e:
        return jsonify({"error": "not found"}), 404
    body = {k: e.get(k, "") for k in _BODY_FIELDS}
    body["id"] = entry_id
    body["title"] = e["title"]
    # The quiz arrives ALREADY SHUFFLED and with its explanation relabelled,
    # so the browse page and the quiz page can never disagree about which
    # option is which.
    body["quiz"] = java_bank.presented_quiz(e)
    body["recall"] = java_bank.recall_for(e)
    return jsonify(body)


@java_prep_bp.route("/api/java/quiz", methods=["GET"])
@login_required
def java_quiz():
    """A quiz drawn from the bank.

    `cat` narrows it to one rung of the ladder; `n` caps the length. The order
    is shuffled per request — unlike the AI/SDE quiz's stable daily set,
    because this bank is small enough that a fixed daily draw would repeat
    within a week.
    """
    import random

    cat = (request.args.get("cat") or "").strip()
    try:
        n = max(3, min(30, int(request.args.get("n", 10))))
    except (TypeError, ValueError):
        n = 10

    items = java_bank.quiz_items()
    if cat:
        items = [q for q in items if q["cat"] == cat]
    random.shuffle(items)
    items = items[:n]

    return jsonify({
        "count": len(items), "cat": cat, "questions": items,
        "categories": [{"key": k, "label": java_bank.CATEGORIES[k]}
                       for k in java_bank.CATEGORY_ORDER],
    })
