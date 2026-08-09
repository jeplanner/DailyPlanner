"""Prompt-free batch generator for ai_sde_bank.py.

Runs as a single simple command (`python3 scripts/_ai_gen.py`) so the
permission parser can allow it — no heredocs, pipes, or && chains.
Replace the BATCH list, run it, then git add/commit/push as separate
simple commands. Validates every code block (ast.parse), dedups against
existing titles, and checks every entry has an example before writing.
"""
import ast
import importlib
import os
import sys

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())   # so `import ai_sde_bank` works from here

# ── The batch to add this iteration. ──
BATCH = [
    dict(cat="dsa", title="Minimum Number of Coins for Fruits",
         answer="Fruits are 1-indexed with prices; buying the i-th fruit (cost prices[i]) grants the next i fruits FREE (but you may still buy them to get their own offer). Minimize total coins. DP from the end: dp[i] = price(i) + min(dp[j]) over the positions j where you could resume paying (i+1 .. 2i+1).",
         tags=["min-coins-fruits","dynamic-programming","dp","dsa"],
         code='''# Min coins to get all fruits; buying the i-th (1-indexed) grants the next i free.
def minimum_coins(prices):
    n = len(prices)
    def price(i):
        return prices[i - 1]
    dp = [0] * (n + 2)                 # dp[n+1] = 0 (nothing left to buy)
    for i in range(n, 0, -1):
        # buying fruit i covers i+1..2i free; resume paying at any j in i+1..2i+1
        upper = min(n + 1, 2 * i + 1)
        dp[i] = price(i) + min(dp[j] for j in range(i + 1, upper + 1))
    return dp[1]''',
         complexity="Time O(n^2), space O(n).",
         pitfalls="Off-by-one on the free range (next i fruits, up to 2i); forgetting you can re-buy for a better offer.",
         example="minimum_coins([3,1,2]) -> 4."),
    dict(cat="dsa", title="Minimum Number of Arrows to Burst Balloons",
         answer="Balloons are intervals on the x-axis; a vertical arrow at x bursts every balloon spanning x. Find the fewest arrows to burst all. Greedy: sort by END coordinate, shoot an arrow at the first balloon's end, and only shoot a new arrow when a balloon STARTS after the last arrow's position.",
         tags=["min-arrows-balloons","greedy","intervals","sorting","dsa"],
         code='''# Fewest arrows to burst all balloons (intervals); an arrow bursts overlaps.
def find_min_arrows(points):
    if not points:
        return 0
    points.sort(key=lambda x: x[1])   # sort by end coordinate
    arrows = 1
    end = points[0][1]                # first arrow at the earliest end
    for start, finish in points[1:]:
        if start > end:               # this balloon starts after the last arrow
            arrows += 1
            end = finish
    return arrows''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Sorting by start instead of end (greedy breaks); using >= (touching intervals still overlap here).",
         example="find_min_arrows([[10,16],[2,8],[1,6],[7,12]]) -> 2."),
    dict(cat="dsa", title="Car Pooling",
         answer="Given trips (passengers, start, end) and a car capacity, decide if all trips fit without exceeding capacity at any point. DIFFERENCE ARRAY over locations: +passengers at each pickup, -passengers at each dropoff; sweep the prefix sum and check it never exceeds capacity.",
         tags=["car-pooling","difference-array","prefix-sum","array","dsa"],
         code='''# Can you carry all trips without exceeding capacity? (difference array).
def car_pooling(trips, capacity):
    stops = [0] * 1001                 # locations 0..1000
    for passengers, start, end in trips:
        stops[start] += passengers     # pick up
        stops[end] -= passengers       # drop off
    current = 0
    for change in stops:
        current += change
        if current > capacity:
            return False
    return True''',
         complexity="Time O(n + range), space O(range).",
         pitfalls="Counting the dropoff location as still occupied (drop at 'end', not end+1); recomputing sums per query.",
         example="car_pooling([[2,1,5],[3,3,7]], 4) -> False; the same with capacity 5 -> True."),
    dict(cat="dsa", title="Maximum Length of Pair Chain",
         answer="Given pairs (a, b), form the longest CHAIN where each next pair's start exceeds the previous pair's end. Greedy (activity-selection): sort by END, then keep every pair whose start is greater than the current chain end.",
         tags=["max-pair-chain","greedy","intervals","sorting","dsa"],
         code='''# Longest chain of pairs where each next pair's start > previous pair's end.
def find_longest_chain(pairs):
    pairs.sort(key=lambda p: p[1])     # sort by end
    count = 0
    current_end = float('-inf')
    for start, end in pairs:
        if start > current_end:        # can extend the chain
            count += 1
            current_end = end
    return count''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Sorting by start (suboptimal greedy); allowing start == end.",
         example="find_longest_chain([[1,2],[2,3],[3,4]]) -> 2."),
    dict(cat="dsa", title="Merge Similar Items",
         answer="Two lists of [value, weight] items; merge them by VALUE, summing weights, and return the result sorted by value. Accumulate weights per value in a map, then output sorted.",
         tags=["merge-similar-items","hash-map","sorting","array","dsa"],
         code='''# Merge two [value, weight] lists by value, summing weights; sorted by value.
def merge_similar_items(items1, items2):
    weights = {}
    for value, weight in items1 + items2:
        weights[value] = weights.get(value, 0) + weight
    return [[v, weights[v]] for v in sorted(weights)]''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Not summing duplicate values across both lists; returning unsorted output.",
         example="merge_similar_items([[1,1],[4,5],[3,8]], [[3,1],[1,5]]) -> [[1,6],[3,9],[4,5]]."),
    dict(cat="dsa", title="Count Symmetric Integers",
         answer="Count integers in [low, high] that have an EVEN number of digits and whose first-half digit sum equals the second-half digit sum. Iterate the range; for even-length numbers compare the two half-sums.",
         tags=["symmetric-integers","digits","math","dsa"],
         code='''# Count integers in [low, high] with even digits and equal half-sums.
def count_symmetric_integers(low, high):
    count = 0
    for num in range(low, high + 1):
        s = str(num)
        if len(s) % 2 == 0:
            half = len(s) // 2
            if sum(map(int, s[:half])) == sum(map(int, s[half:])):
                count += 1
    return count''',
         complexity="Time O((high-low) * digits), space O(1).",
         pitfalls="Including odd-length numbers; splitting the digit string at the wrong midpoint.",
         example="count_symmetric_integers(1, 100) -> 9  (11,22,...,99)."),
    dict(cat="dsa", title="Distribute Money to Maximum Children",
         answer="Distribute 'money' dollars among 'children' so each gets at least $1 and NO child gets exactly $4; maximize how many get exactly $8. Give everyone $1 first, then turn as many as possible into $8 with +$7 each, and fix up two edge cases (leftover money with no one to give it to, or a last child stuck at exactly $4).",
         tags=["distribute-money","greedy","math","dsa"],
         code='''# Max children who get exactly $8 (each >=1, none exactly 4).
def dist_money(money, children):
    if money < children:
        return -1                      # can't give everyone at least $1
    money -= children                  # give $1 to each first
    eights = min(money // 7, children) # each extra $7 makes a child's $8
    money -= eights * 7
    remaining = children - eights
    if remaining == 0 and money > 0:
        eights -= 1                    # leftover must go to someone (breaks an 8)
    elif remaining == 1 and money == 3:
        eights -= 1                    # the last child would get exactly $4
    return eights''',
         complexity="Time O(1), space O(1).",
         pitfalls="Missing the exactly-$4 edge case; not handling leftover money when everyone already has $8.",
         example="dist_money(20, 3) -> 1; dist_money(16, 2) -> 2."),
    dict(cat="dsa", title="Longest Arithmetic Subsequence",
         answer="Find the length of the longest subsequence with a constant common difference. DP with a per-index dictionary: dp[i][d] = length of the arithmetic subsequence ending at i with difference d = (extend the best chain ending at some j<i with the same d) + 1.",
         tags=["longest-arithmetic-subsequence","dynamic-programming","hash-map","dp","dsa"],
         code='''# Length of the longest arithmetic subsequence (any common difference), DP.
def longest_arith_seq_length(nums):
    dp = [{} for _ in nums]            # dp[i][d] = AP length ending at i with diff d
    best = 0
    for i in range(len(nums)):
        for j in range(i):
            d = nums[i] - nums[j]
            dp[i][d] = dp[j].get(d, 1) + 1   # extend j's chain, or start length 2
            best = max(best, dp[i][d])
    return best''',
         complexity="Time O(n^2), space O(n^2).",
         pitfalls="Using a 2-D array keyed by difference (differences can be negative/large — a dict per index is cleaner); base length off by one.",
         example="longest_arith_seq_length([3,6,9,12]) -> 4; longest_arith_seq_length([9,4,7,2,10]) -> 3."),
    dict(cat="glossary", title="Event sourcing",
         answer="A pattern where, instead of storing the current STATE of an entity, you store the full sequence of EVENTS that produced it (an append-only log); current state is derived by REPLAYING the events. Benefits: a complete audit trail, the ability to reconstruct any past state, natural fit for CQRS and temporal queries, and easy replay/debugging. Costs: more complexity, eventually-consistent read models, event schema evolution, and slow rebuilds (mitigated by SNAPSHOTS).",
         tags=["event-sourcing","audit-log","cqrs","architecture","events"],
         example="A bank account is stored not as 'balance=$150' but as [Deposited $100, Deposited $100, Withdrew $50]; the balance is the fold of those events — a perfect audit trail and any-date historical view."),
    dict(cat="glossary", title="CQRS",
         answer="Command Query Responsibility Segregation — separating the WRITE model (commands that change state) from the READ model (queries) into different models/paths, often different data stores. Writes use a normalized/consistent model; reads are served from denormalized PROJECTIONS tuned for query patterns, updated asynchronously. Benefits: independent scaling/optimization of reads vs writes and simpler read models. Costs: eventual consistency between them and more moving parts.",
         tags=["cqrs","read-model","write-model","projections","architecture"],
         example="An order service writes normalized order events while a separate denormalized 'order history' read store serves the UI — so heavy reads don't contend with writes and each side scales independently."),
    dict(cat="glossary", title="Expand-contract migration",
         answer="A technique (aka parallel change) for a BACKWARD-COMPATIBLE schema/API change with zero downtime, in phases. EXPAND: add the new column/field alongside the old (nullable/optional) and write to BOTH. MIGRATE: backfill old data and switch readers to the new. CONTRACT: once nothing uses the old, remove it. Because every intermediate deploy is compatible with both old and new code, you roll out gradually and can roll back safely.",
         tags=["expand-contract","migration","zero-downtime","schema-change","backward-compatible"],
         example="Renaming a column: (1) add 'email_address' and write both it and 'email'; (2) backfill and read from 'email_address'; (3) stop writing 'email' and drop it — no downtime, every step rollback-safe."),
    dict(cat="glossary", title="Canary analysis (automated)",
         answer="Automatically evaluating a CANARY deployment (a small traffic slice on the new version) by comparing its METRICS — error rate, latency, resource use — against the baseline (old version) in real time, and AUTO-promoting or AUTO-rolling-back based on statistical significance. Tools like Spinnaker's Kayenta score the canary; if it regresses, the rollout halts automatically — removing human guesswork from progressive delivery.",
         tags=["canary-analysis","progressive-delivery","kayenta","deployment","sre"],
         example="A canary gets 5% of traffic; automated analysis finds its p99 latency statistically worse than baseline and auto-rolls-back before the change reaches 100% — no engineer had to watch a dashboard."),
    dict(cat="glossary", title="Feature toggle types",
         answer="Feature flags come in kinds by lifespan and purpose. RELEASE toggles hide in-progress features for trunk-based dev (short-lived). EXPERIMENT toggles drive A/B tests (assign variants). OPS toggles are kill-switches/circuit breakers for operational control (medium-lived). PERMISSIONING toggles gate features by user/plan/entitlement (long-lived). Mixing them up (leaving a release toggle in forever) creates flag debt; each type has a different owner and cleanup expectation.",
         tags=["feature-toggles","feature-flags","release-toggle","kill-switch","deployment"],
         example="A 'new-checkout' RELEASE toggle is removed once shipped; a 'premium-reports' PERMISSIONING toggle stays forever gating paid users; an 'enable-recommendations' OPS toggle is a kill switch during incidents."),
    dict(cat="conceptual", title="Why use CQRS (separate read and write models), and when is it worth the complexity?",
         answer="In a simple CRUD app one model serves both reads and writes fine. But some systems have a fundamental MISMATCH: writes need a normalized, consistent, validated model (to enforce invariants), while reads want denormalized, pre-joined, query-shaped data (to be fast), and the workloads differ wildly in scale (e.g. 1000x more reads) and consistency needs. Forcing both through one model means every read pays for write-side normalization (expensive joins), writes contend with read load, and you can't scale them independently. CQRS SEPARATES them: commands flow through a write model optimized for correctness, while one or more READ projections are built asynchronously, each denormalized for a specific query/UI — so reads are fast and scale out (replicas/caches) without touching writes, and each side evolves independently. It pairs naturally with event sourcing (events feed the projections). The COST is real: the read side is EVENTUALLY consistent (a projection lags, so a user may not immediately see their own write), you maintain multiple models plus the projection pipeline, and debugging spans more components. Worth it when reads and writes have very different scale or shape, you need multiple specialized read views, the domain is complex enough that a shared model bottlenecks, or you're already event-sourcing. OVERKILL for simple/low-scale CRUD or when strong read-your-writes consistency is essential. The rule: adopt CQRS to solve a real read/write asymmetry, not by default.",
         tags=["cqrs","read-write-separation","eventual-consistency","architecture","why"],
         example="A social feed reads 10,000x more than it writes and needs many denormalized views (home, profile, notifications) — CQRS lets writes append posts while separate read projections serve each view fast; a small admin CRUD tool should NOT use CQRS because the added eventual consistency buys nothing."),
]


def qsrc(e):
    s = f"    Q({e['cat']!r}, {e['title']!r},\n      {e['answer']!r},\n      {e['tags']!r}"
    for f in ("code", "example", "complexity", "pitfalls", "followups"):
        if e.get(f):
            s += f",\n      {f}={e[f]!r}"
    return s + "),\n"


# Validate every code block parses before we touch the file.
for e in BATCH:
    if e.get("code"):
        ast.parse(e["code"])

# Skip any titles already present (so re-running never double-inserts).
_existing = {e["title"] for e in importlib.import_module("ai_sde_bank").ENTRIES}
BATCH = [e for e in BATCH if e["title"] not in _existing]
if not BATCH:
    print("nothing new to insert (all titles already present)")
    raise SystemExit(0)

block = "".join(qsrc(e) for e in BATCH)
path = "ai_sde_bank.py"
text = open(path).read()
marker = "),\n]\n\n# Fill tags: explicit + category-derived."
assert text.count(marker) == 1, "insert marker not found/unique"
text = text.replace(marker, "),\n" + block + "]\n\n# Fill tags: explicit + category-derived.")
open(path, "w").write(text)

b = importlib.import_module("ai_sde_bank")
importlib.reload(b)
for e in b.ENTRIES:
    if e.get("code"):
        ast.parse(e["code"])
missing = [e["title"] for e in b.ENTRIES if not e.get("example")]
assert not missing, f"missing example: {missing}"
print(f"inserted {len(BATCH)} | total {len(b.ENTRIES)} | missing example: {len(missing)}")
