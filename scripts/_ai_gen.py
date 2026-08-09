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
    dict(cat="dsa", title="Shuffle String",
         answer="Rearrange a string so the character at position i moves to position indices[i]. Allocate a result array and place each character at its target index.",
         tags=["shuffle-string","array","string","dsa"],
         code='''# Rearrange string so that char i moves to position indices[i].
def restore_string(s, indices):
    result = [''] * len(s)
    for ch, idx in zip(s, indices):
        result[idx] = ch          # place each char at its target position
    return "".join(result)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Reading vs writing the index direction; building the string by concatenation (slow).",
         example="restore_string('aiohn', [3,1,4,2,0]) -> 'nihao'."),
    dict(cat="dsa", title="Minimum Absolute Difference",
         answer="Return all pairs (as sorted lists) whose absolute difference equals the MINIMUM absolute difference in the array. Sort first — the minimum difference is always between ADJACENT sorted elements — find that min, then collect all adjacent pairs achieving it.",
         tags=["min-abs-difference","sorting","array","dsa"],
         code='''# All pairs with the smallest absolute difference, sorted ascending.
def minimum_abs_difference(arr):
    arr.sort()
    min_diff = min(arr[i + 1] - arr[i] for i in range(len(arr) - 1))
    return [[arr[i], arr[i + 1]] for i in range(len(arr) - 1)
            if arr[i + 1] - arr[i] == min_diff]''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Comparing all pairs (O(n^2)); the min diff is only between adjacent sorted values.",
         example="minimum_abs_difference([4,2,1,3]) -> [[1,2],[2,3],[3,4]]."),
    dict(cat="dsa", title="Average Salary Excluding the Minimum and Maximum",
         answer="Compute the average of the salaries after removing exactly ONE minimum and ONE maximum. Sum all, subtract the min and max, divide by (n - 2).",
         tags=["average-salary","array","math","dsa"],
         code='''# Average of salaries, dropping the single minimum and maximum.
def average_salary(salary):
    total = sum(salary) - min(salary) - max(salary)
    return total / (len(salary) - 2)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Dividing by n instead of n-2; removing all occurrences of min/max instead of one each.",
         example="average_salary([4000,3000,1000,2000]) -> 2500.0."),
    dict(cat="dsa", title="Maximum Gap (bucket sort)",
         answer="Find the largest gap between successive values in the sorted order, in O(n) without fully sorting. Pigeonhole insight: with n numbers spanning [lo, hi], the max gap is at least ceil((hi-lo)/(n-1)); use buckets of that size so the max gap always spans EMPTY buckets — track each bucket's min/max and compare across buckets.",
         tags=["maximum-gap","bucket-sort","pigeonhole","array","dsa"],
         code='''# Largest gap between successive elements in sorted order, in O(n).
def maximum_gap(nums):
    if len(nums) < 2:
        return 0
    lo, hi = min(nums), max(nums)
    if lo == hi:
        return 0
    n = len(nums)
    bucket_size = max(1, (hi - lo) // (n - 1))
    bucket_count = (hi - lo) // bucket_size + 1
    buckets = [[None, None] for _ in range(bucket_count)]   # [min, max] per bucket
    for num in nums:
        b = (num - lo) // bucket_size
        bmin, bmax = buckets[b]
        buckets[b][0] = num if bmin is None else min(bmin, num)
        buckets[b][1] = num if bmax is None else max(bmax, num)
    max_gap = 0
    prev_max = lo
    for bmin, bmax in buckets:
        if bmin is None:
            continue                                # skip empty buckets
        max_gap = max(max_gap, bmin - prev_max)     # gap across empty buckets
        prev_max = bmax
    return max_gap''',
         complexity="Time O(n), space O(n).",
         pitfalls="Sorting (O(n log n)) when O(n) is required; wrong bucket sizing/count.",
         example="maximum_gap([3,6,9,1]) -> 3."),
    dict(cat="dsa", title="Find Lucky Integer in an Array",
         answer="A 'lucky' integer has a frequency equal to its own value; return the LARGEST lucky integer, or -1 if none. Count frequencies, then take the max value whose count equals the value.",
         tags=["find-lucky","counting","hash-map","array","dsa"],
         code='''# Largest value whose frequency equals its value ('lucky'), or -1.
from collections import Counter
def find_lucky(arr):
    counts = Counter(arr)
    lucky = [v for v, c in counts.items() if v == c]
    return max(lucky) if lucky else -1''',
         complexity="Time O(n), space O(n).",
         pitfalls="Returning the first match instead of the largest; forgetting the -1 default.",
         example="find_lucky([2,2,3,4]) -> 2; find_lucky([1,2,2,3,3,3]) -> 3."),
    dict(cat="dsa", title="Count Items Matching a Rule",
         answer="Each item is [type, color, name]; count how many match a rule given by a key ('type'/'color'/'name') and a value. Map the rule key to the tuple index and count matches.",
         tags=["count-items-rule","array","filtering","dsa"],
         code='''# Count items whose given attribute (type/color/name) matches ruleValue.
def count_matches(items, rule_key, rule_value):
    idx = {"type": 0, "color": 1, "name": 2}[rule_key]
    return sum(1 for item in items if item[idx] == rule_value)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Hardcoding the wrong index for the rule key; case sensitivity of values.",
         example="count_matches([['phone','blue','pixel'],['computer','silver','lenovo']], 'color', 'silver') -> 1."),
    dict(cat="dsa", title="Unique Morse Code Words",
         answer="Each lowercase word maps to a Morse-code string (concatenating per-letter codes); count how many DISTINCT transformations the words produce. Build each word's code, add to a set, and return the set size.",
         tags=["unique-morse","hash-set","string","encoding","dsa"],
         code='''# Number of distinct Morse-code transformations of the words.
def unique_morse_representations(words):
    morse = [".-","-...","-.-.","-..",".","..-.","--.","....","..",".---",
             "-.-",".-..","--","-.","---",".--.","--.-",".-.","...","-",
             "..-","...-",".--","-..-","-.--","--.."]
    seen = set()
    for word in words:
        code = "".join(morse[ord(c) - ord('a')] for c in word)
        seen.add(code)
    return len(seen)''',
         complexity="Time O(total characters), space O(number of words).",
         pitfalls="Off-by-one in the letter->index mapping; comparing words instead of their codes.",
         example="unique_morse_representations(['gin','zen','gig','msg']) -> 2."),
    dict(cat="dsa", title="String to Integer (atoi)",
         answer="Parse a leading 32-bit integer from a string like C's atoi: skip leading whitespace, read an optional +/- sign, consume consecutive digits (stopping at the first non-digit), and CLAMP the result to the signed 32-bit range.",
         tags=["atoi","string","parsing","overflow","dsa"],
         code='''# Parse a leading integer from a string (atoi): spaces, sign, digits, clamp.
def my_atoi(s):
    s = s.lstrip()               # 1) skip leading whitespace
    if not s:
        return 0
    sign = 1
    i = 0
    if s[0] in "+-":             # 2) optional sign
        sign = -1 if s[0] == '-' else 1
        i = 1
    num = 0
    while i < len(s) and s[i].isdigit():   # 3) consume digits
        num = num * 10 + int(s[i])
        i += 1
    num *= sign
    return max(-2**31, min(num, 2**31 - 1))   # 4) clamp to 32-bit range''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not clamping to 32-bit bounds; mishandling the sign or trailing non-digits.",
         example="my_atoi('   -042') -> -42; my_atoi('4193 with words') -> 4193; my_atoi('words 987') -> 0."),
    dict(cat="glossary", title="Load balancer: L4 vs L7",
         answer="Two layers a load balancer can operate at. L4 (TRANSPORT) balances by IP/port, forwarding TCP/UDP connections without inspecting content — very fast, protocol-agnostic, but 'dumb' (can't route by URL/header). L7 (APPLICATION) understands HTTP, so it can route by path/host/header/cookie, terminate TLS, do content-based routing, retries, and sticky sessions — smarter but higher overhead. Use L4 for raw throughput/non-HTTP; L7 for HTTP microservice routing.",
         tags=["load-balancer","l4","l7","networking","routing"],
         example="An L4 LB just sends each TCP connection to some backend; an L7 LB routes /api/* to the API service and /images/* to a static service, and can retry a failed HTTP request."),
    dict(cat="glossary", title="Sticky sessions (session affinity)",
         answer="A load-balancing feature that routes a given user's requests to the SAME backend every time (usually via a cookie or IP hash). Needed when a server holds per-user in-memory session state. Downsides: it undermines even load distribution and breaks if that server dies (the user loses their session). Better to keep servers STATELESS with session state in a shared store (Redis) so any server can serve any request.",
         tags=["sticky-sessions","session-affinity","load-balancing","statelessness"],
         example="A cart in one server's memory needs sticky sessions to hit the same server; storing the cart in Redis lets any server serve you, so the LB balances freely."),
    dict(cat="glossary", title="Health check (liveness vs readiness)",
         answer="A periodic probe (e.g. GET /healthz) a load balancer/orchestrator sends to each backend to decide if it should receive traffic. Unhealthy instances are pulled OUT of rotation and re-added on recovery — self-healing and zero-downtime deploys. Distinguish LIVENESS (is the process alive? restart if not) from READINESS (is it ready to serve? hold traffic until yes).",
         tags=["health-check","liveness","readiness","kubernetes","reliability"],
         example="Kubernetes uses a readiness probe to hold traffic from a pod until it's warmed up, and a liveness probe to restart a deadlocked pod — so users never hit a broken instance."),
    dict(cat="glossary", title="mTLS (mutual TLS)",
         answer="An extension of TLS where BOTH sides authenticate with certificates, not just the server — the client also presents a cert the server verifies, so each party cryptographically proves its identity. It's the backbone of zero-trust service-to-service auth (and service meshes): services accept connections only from peers with valid certs, encrypting and authenticating internal traffic without passwords/tokens.",
         tags=["mtls","mutual-tls","zero-trust","service-mesh","security"],
         example="In a service mesh every service presents a short-lived cert; a payment service accepts a call from the orders service only after verifying its mTLS cert, so a rogue pod without a valid cert can't talk to it."),
    dict(cat="glossary", title="BGP (Border Gateway Protocol)",
         answer="The routing protocol that glues the internet together — it exchanges REACHABILITY information between autonomous systems (ISPs, large networks) so they pick the best path to any block of IPs. It's policy-driven (business relationships, not just shortest path) and trust-based, which is why BGP misconfigurations or hijacks can black-hole or reroute huge swaths of traffic. Anycast (CDNs/DNS) relies on BGP announcing the same IP from many locations.",
         tags=["bgp","routing","internet","anycast","networking"],
         example="A CDN announces the same anycast IP via BGP from PoPs worldwide, so BGP routes each user to the nearest PoP — and a bad BGP announcement can misroute a big chunk of traffic."),
    dict(cat="conceptual", title="Why (and when) choose L7 load balancing over L4?",
         answer="L4 and L7 trade SMARTS for SPEED/generality. An L4 load balancer works at the transport layer — it sees only IP/port and forwards whole TCP/UDP connections without looking inside — so it's extremely fast, low-overhead, and protocol-agnostic (any TCP/UDP, not just HTTP), but 'dumb': it can't route by URL/header/cookie, terminate TLS, or do HTTP-aware retries. An L7 load balancer parses the HTTP request, enabling CONTENT-BASED ROUTING (/api vs /images, by Host/header), TLS termination, request-level retries and circuit breaking, cookie-based sticky sessions, rate limiting, and per-route observability — the features microservice/web stacks need. The cost is more CPU/latency per request (it buffers and parses) and it only speaks the protocols it's built for. So: choose L7 when you need HTTP-aware routing/features (the common web/microservices case — an API gateway or ingress); choose L4 for raw throughput, ultra-low latency, or non-HTTP traffic (databases, custom TCP, UDP games). Many stacks combine them: an L4 LB spreads connections across L7 proxies that do the smart routing.",
         tags=["load-balancer","l4","l7","routing","why"],
         example="A public API uses an L7 ingress to route /orders vs /users and terminate TLS; a high-throughput database or UDP game server front-ends with an L4 LB because it just needs to spread connections fast without parsing content."),
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
