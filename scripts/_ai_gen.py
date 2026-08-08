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
    dict(cat="dsa", title="Two City Scheduling (greedy)",
         answer="Fly 2n people, exactly n to city A and n to city B, minimizing total cost. Greedy: sort people by how much MORE it costs to send them to B versus A (cost_A - cost_B); the people who save the most by going to A (most negative) go to A, the rest to B.",
         tags=["two-city-scheduling","greedy","sorting","dsa"],
         code='''# Min cost to fly 2n people, n to city A and n to city B.
def two_city_sched_cost(costs):
    # sort by how much cheaper A is than B; biggest A-savings go to A
    costs.sort(key=lambda c: c[0] - c[1])
    n = len(costs) // 2
    total = 0
    for i in range(len(costs)):
        total += costs[i][0] if i < n else costs[i][1]
    return total''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Sorting by absolute cost instead of the A-vs-B difference; violating the n/n split.",
         example="two_city_sched_cost([[10,20],[30,200],[400,50],[30,20]]) -> 110."),
    dict(cat="dsa", title="Boats to Save People (greedy)",
         answer="Each boat holds at most 2 people and a weight limit; find the fewest boats to carry everyone. Sort, then two pointers: the heaviest person always takes a boat, and if the lightest also fits within the limit they share it. Advance accordingly.",
         tags=["boats-save-people","greedy","two-pointers","sorting","dsa"],
         code='''# Fewest boats (weight limit, max 2 people/boat) to carry everyone.
def num_rescue_boats(people, limit):
    people.sort()
    i, j = 0, len(people) - 1
    boats = 0
    while i <= j:
        if people[i] + people[j] <= limit:
            i += 1              # lightest also fits with the heaviest
        j -= 1                  # heaviest always takes a boat
        boats += 1
    return boats''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Trying to fit >2 per boat; not always seating the heaviest.",
         example="num_rescue_boats([3,2,2,1], 3) -> 3."),
    dict(cat="dsa", title="Maximum Units on a Truck (greedy)",
         answer="Given box types (count, units-per-box) and a truck box capacity, maximize total units. Greedy: load boxes with the MOST units per box first until the truck is full, taking a partial batch of the last type if needed.",
         tags=["maximum-units-truck","greedy","sorting","dsa"],
         code='''# Max units loadable onto a truck of given box capacity (greedy).
def maximum_units(box_types, truck_size):
    box_types.sort(key=lambda b: b[1], reverse=True)   # most units per box first
    units = 0
    for count, per_box in box_types:
        take = min(count, truck_size)
        units += take * per_box
        truck_size -= take
        if truck_size == 0:
            break
    return units''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Sorting by box count instead of units-per-box; overfilling past the capacity.",
         example="maximum_units([[1,3],[2,2],[3,1]], 4) -> 8  (1x3 + 2x2 + 1x1)."),
    dict(cat="dsa", title="Monotonic Array",
         answer="Decide whether an array is entirely non-increasing OR entirely non-decreasing. Track two flags in one pass — clear 'increasing' on any drop and 'decreasing' on any rise; the array is monotonic if either flag survives.",
         tags=["monotonic-array","array","dsa"],
         code='''# Is the array entirely non-increasing or entirely non-decreasing?
def is_monotonic(nums):
    increasing = decreasing = True
    for i in range(1, len(nums)):
        if nums[i] > nums[i - 1]:
            decreasing = False
        if nums[i] < nums[i - 1]:
            increasing = False
    return increasing or decreasing''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using strict comparisons (equal neighbours are allowed); two passes when one suffices.",
         example="is_monotonic([1,2,2,3]) -> True; is_monotonic([1,3,2]) -> False."),
    dict(cat="dsa", title="Find Pivot Index",
         answer="Find the leftmost index where the sum of elements to its LEFT equals the sum to its RIGHT. Precompute the total; sweep keeping a running left sum — the right sum is total - left - current, so a match means left == total - left - current.",
         tags=["pivot-index","prefix-sum","array","dsa"],
         code='''# Leftmost index where the left sum equals the right sum.
def pivot_index(nums):
    total = sum(nums)
    left = 0
    for i, n in enumerate(nums):
        if left == total - left - n:   # left sum == right sum
            return i
        left += n
    return -1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Including the pivot in either side; recomputing sums each step (O(n^2)).",
         example="pivot_index([1,7,3,6,5,6]) -> 3  (1+7+3 == 5+6)."),
    dict(cat="dsa", title="DI String Match",
         answer="Given a pattern of 'I' (increase) and 'D' (decrease), build ANY permutation of 0..n that follows it. Greedy two-pointer: for 'I' output the current LOW and increment low (leaving room to go up), for 'D' output the current HIGH and decrement high; append the last remaining value.",
         tags=["di-string-match","greedy","two-pointers","array","dsa"],
         code='''# Build a permutation of 0..n matching a pattern of 'I' / 'D'.
def di_string_match(s):
    low, high = 0, len(s)
    result = []
    for ch in s:
        if ch == 'I':
            result.append(low); low += 1     # leave room to increase next
        else:
            result.append(high); high -= 1   # leave room to decrease next
    result.append(low)                        # low == high at the end
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Forgetting the final appended value; swapping the low/high roles.",
         example="di_string_match('IDID') -> [0,4,1,3,2]."),
    dict(cat="dsa", title="Maximum Ascending Subarray Sum",
         answer="Find the largest sum of a strictly ASCENDING contiguous subarray. Sweep keeping a current run sum; extend it while each element is greater than the previous, otherwise restart the run at the current element. Track the best sum seen.",
         tags=["max-ascending-sum","array","greedy","dsa"],
         code='''# Largest sum of a strictly ascending contiguous subarray.
def max_ascending_sum(nums):
    best = current = nums[0]
    for i in range(1, len(nums)):
        if nums[i] > nums[i - 1]:
            current += nums[i]      # extend the ascending run
        else:
            current = nums[i]       # restart the run
        best = max(best, current)
    return best''',
         complexity="Time O(n), space O(1).",
         pitfalls="Allowing equal neighbours (must be strictly ascending); not resetting on a non-increase.",
         example="max_ascending_sum([10,20,30,5,10,50]) -> 65  (5+10+50)."),
    dict(cat="dsa", title="Degree of an Array",
         answer="The degree of an array is the maximum frequency of any element; find the SHORTEST contiguous subarray with the same degree. Track each value's first index and running count; whenever a value's count reaches (or ties) the degree, the candidate length is last_index - first_index + 1.",
         tags=["degree-of-array","hash-map","array","dsa"],
         code='''# Shortest subarray whose degree (max frequency) equals the array's degree.
def find_shortest_sub_array(nums):
    first, count = {}, {}
    degree = 0
    best = 0
    for i, n in enumerate(nums):
        if n not in first:
            first[n] = i            # first index of this value
        count[n] = count.get(n, 0) + 1
        if count[n] > degree:
            degree = count[n]
            best = i - first[n] + 1
        elif count[n] == degree:
            best = min(best, i - first[n] + 1)
    return best''',
         complexity="Time O(n), space O(n).",
         pitfalls="Not updating best on ties at the same degree; forgetting the first-index map.",
         example="find_shortest_sub_array([1,2,2,3,1]) -> 2  (the [2,2] subarray)."),
    dict(cat="glossary", title="HTTP keep-alive (persistent connections)",
         answer="Reusing a single TCP connection for MULTIPLE HTTP request/response cycles instead of opening a new one per request (the HTTP/1.0 default). It avoids repeated TCP + TLS handshakes (each costing round-trips), cutting latency and server load. HTTP/1.1 enables it by default; Connection headers and idle timeouts govern it.",
         tags=["http-keep-alive","persistent-connection","http","networking","latency"],
         example="Loading a page with 30 assets over one keep-alive connection avoids 30 separate TCP/TLS handshakes, dramatically speeding up the load."),
    dict(cat="glossary", title="HTTP/2 multiplexing",
         answer="HTTP/2 carries MULTIPLE concurrent requests/responses over a SINGLE TCP connection as interleaved, independently-framed STREAMS — so one slow response doesn't block others at the HTTP layer (fixing HTTP/1.1's need for many connections or serial pipelining). It also adds header compression (HPACK) and server push. A big latency win for many small resources.",
         tags=["http2","multiplexing","streams","networking","performance"],
         example="A page fetching 100 resources over HTTP/2 interleaves them concurrently on one connection, instead of HTTP/1.1 opening ~6 connections and queueing the rest."),
    dict(cat="glossary", title="Head-of-line blocking",
         answer="When the FIRST item in a queue/stream stalls and BLOCKS everything behind it, even items that could proceed. It appears at multiple layers: HTTP/1.1 (a slow response blocks pipelined ones) and, subtly, at the TCP layer for HTTP/2, where a single lost packet stalls ALL multiplexed streams because TCP delivers bytes in order. HTTP/3 (over QUIC/UDP) fixes the transport-level version with independent streams.",
         tags=["head-of-line-blocking","http2","tcp","quic","networking"],
         example="On HTTP/2, one dropped TCP packet halts every multiplexed stream until it's retransmitted; HTTP/3's QUIC lets the other streams keep flowing."),
    dict(cat="glossary", title="gRPC vs REST",
         answer="Two API styles. REST is resource-oriented over HTTP/1.1 with JSON — human-readable, universally supported, cache-friendly, but verbose and loosely typed. gRPC uses HTTP/2 + Protocol Buffers (binary, schema-defined) with generated typed clients — faster/smaller payloads, streaming, strong contracts, but not browser-native (needs a proxy) and less readable. Use gRPC for internal low-latency service-to-service; REST for public/browser-facing APIs.",
         tags=["grpc","rest","protobuf","http2","api-design"],
         example="Internal microservices use gRPC for compact, strongly-typed, streaming calls; a public API stays REST/JSON so any client or browser can consume it easily."),
    dict(cat="glossary", title="Index selectivity",
         answer="A measure of how well an index NARROWS a query — the ratio of distinct values to total rows (high selectivity = many distinct values = each matches few rows). The optimizer prefers HIGH-selectivity indexes because they eliminate most rows; a LOW-selectivity index (e.g. a boolean where 90% are true) is nearly useless — a full scan may beat the index lookup + row fetches. It drives whether an index is used at all.",
         tags=["index-selectivity","indexing","query-optimization","database"],
         example="An index on 'email' (unique, high selectivity) is great for lookups; an index on 'gender' (2 values, low selectivity) is usually ignored because it matches half the table."),
    dict(cat="conceptual", title="Why does HTTP/2 multiplexing not fully eliminate head-of-line blocking, and how does HTTP/3 fix it?",
         answer="HTTP/1.1 blocks at the HTTP layer: responses on a connection are serialized, so one slow response blocks everything queued behind it. HTTP/2 fixes THAT by multiplexing independent streams over one TCP connection, interleaving their frames so they progress concurrently — no HTTP-layer blocking. BUT it runs over TCP, which guarantees IN-ORDER byte delivery: if one TCP packet is lost, the kernel withholds ALL subsequently-received bytes (of any stream) until the retransmit arrives — so a single loss stalls every multiplexed stream. That's TRANSPORT-level head-of-line blocking, which HTTP/2 can't escape because the blocking lives below it in TCP. HTTP/3 moves to QUIC (over UDP), implementing streams AT THE TRANSPORT layer with per-stream loss handling, so a lost packet only stalls its own stream while others keep delivering. The lesson: a layer can only fix blocking at or above it.",
         tags=["head-of-line-blocking","http2","http3","quic","tcp","why"],
         example="On a lossy mobile network an HTTP/2 page freezes all resources when one packet drops; the same page over HTTP/3 keeps loading the unaffected resources because QUIC isolates the loss to one stream."),
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
