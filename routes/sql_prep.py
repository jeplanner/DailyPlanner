"""SQL bank — routes.

  /sql                    the browsable bank
  /api/sql                the THIN list (headers only)
  /api/sql/entry/<id>     one full entry, fetched when a card is opened
  /api/sql/schema/<name>  the DDL and seed data a query runs against

THE LIST IS THIN FROM DAY ONE, for the reason java_prep.py records: the
AI/SDE bank shipped every field of every entry on page load and reached a
3 MB body before anyone noticed, because the list screen renders none of
it. The split costs nothing to write now and cannot be retrofitted
cheaply.

WHY THERE IS A SCHEMA ENDPOINT. Every query in this bank is stated against
a named schema, and a reader who cannot see the tables cannot check the
result. The schema is served once per name and cached by the browser
rather than repeated on every one of the 45 cards.
"""
import logging

from flask import Blueprint, jsonify, render_template

from services.login_service import login_required

import ai_sde_summary
import sql_bank

logger = logging.getLogger("daily_plan")

sql_prep_bp = Blueprint("sql_prep", __name__)


#: What the collapsed card header and the filters read. Everything else
#: arrives per-card.
_LIST_FIELDS = ("title", "cat", "difficulty", "frequency", "schema")

#: Held explicitly rather than as "everything not in _LIST_FIELDS", so
#: that adding a field to the bank is a decision about which side of the
#: line it falls on rather than a silent payload regression.
_BODY_FIELDS = ("plain", "answer", "query", "output", "gotcha",
                "portability", "example", "pitfalls", "followups",
                "mnemonic", "tags", "examples")


def _build_list():
    """The thin list, built once at import — the bank is a static literal."""
    rows = []
    for i, e in enumerate(sql_bank.ENTRIES):
        row = {"id": f"sq{i}"}
        row.update({k: e.get(k, "") for k in _LIST_FIELDS})
        # Flags the filters use, computed once rather than shipping the
        # fields they are derived from.
        row["has_query"] = bool(e.get("query"))
        row["has_trap"] = bool(e.get("gotcha"))
        row["has_portability"] = bool(e.get("portability"))
        row["cat_label"] = sql_bank.CATEGORIES.get(e["cat"], e["cat"])
        # Derived from `plain`, same as /java: for a language bank the
        # plain-English answer was written to be the first thing read.
        row["summary"] = ai_sde_summary.summarise_text(e.get("plain"))
        rows.append(row)
    return rows


_LIST = _build_list()
# "sq", not "q" — the behavioural bank already uses "q{i}" and the
# prep scheduler resolves an id by its prefix.
_BY_ID = {f"sq{i}": e for i, e in enumerate(sql_bank.ENTRIES)}


@sql_prep_bp.route("/sql", methods=["GET"])
@login_required
def sql_page():
    return render_template("sql.html")


@sql_prep_bp.route("/api/sql", methods=["GET"])
@login_required
def sql_list():
    """Headers only. Card bodies come from /api/sql/entry/<id>."""
    return jsonify({
        # CATEGORY_ORDER, not sorted keys — the ladder is the teaching
        # order, and alphabetical would put aggregates before basics and
        # traps before joins.
        "categories": [{"key": k, "label": sql_bank.CATEGORIES[k]}
                       for k in sql_bank.CATEGORY_ORDER],
        "entries": _LIST,
        "total": len(_LIST),
        "schemas": sorted(sql_bank.SCHEMAS),
    })


@sql_prep_bp.route("/api/sql/entry/<entry_id>", methods=["GET"])
@login_required
def sql_entry(entry_id):
    e = _BY_ID.get(entry_id)
    if not e:
        return jsonify({"error": "not found"}), 404
    body = {k: e.get(k, "") for k in _BODY_FIELDS}
    body["id"] = entry_id
    body["title"] = e["title"]
    body["schema"] = e["schema"]
    return jsonify(body)


@sql_prep_bp.route("/api/sql/schema/<name>", methods=["GET"])
@login_required
def sql_schema(name):
    """The tables a query runs against.

    Returned as the literal statements rather than a prettified
    description, because the point is that a reader can paste them into
    any SQLite prompt and reproduce every result on the page exactly.
    """
    stmts = sql_bank.SCHEMAS.get(name)
    if stmts is None:
        return jsonify({"error": "unknown schema"}), 404
    ddl = [s for s in stmts if s.lstrip().lower().startswith("create")]
    seed = [s for s in stmts if not s.lstrip().lower().startswith("create")]
    return jsonify({
        "name": name,
        "ddl": ddl,
        "seed": seed,
        "sql": ";\n".join(stmts) + ";",
    })
