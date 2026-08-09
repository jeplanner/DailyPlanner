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
    dict(cat="dsa", title="Minimum Cost to Move Chips",
         answer="Chips sit at positions; moving a chip by 2 is FREE, moving it by 1 costs 1. Aligning them all costs nothing among same-parity positions (all evens can meet for free, all odds too), so the answer is the SMALLER of the even-position count and the odd-position count — bring the smaller group across the single unit gap.",
         tags=["min-cost-chips","greedy","parity","math","dsa"],
         code='''# Min cost to align all chips: moving 2 is free, moving 1 costs 1.
def min_cost_to_move_chips(position):
    even = sum(1 for p in position if p % 2 == 0)
    odd = len(position) - even
    return min(even, odd)   # move the smaller parity group (each move costs 1)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Overthinking the distances (only parity matters); returning the larger count.",
         example="min_cost_to_move_chips([1,2,3]) -> 1."),
    dict(cat="dsa", title="Minimum Moves to Equal Array Elements II",
         answer="Each move increments or decrements one element by 1; find the minimum total moves to make all elements equal. The optimal target is the MEDIAN (it minimizes the sum of absolute deviations). Sort, take the median, and sum the distances.",
         tags=["min-moves-median","median","sorting","greedy","dsa"],
         code='''# Min total moves (+-1) to make all elements equal: converge to the MEDIAN.
def min_moves2(nums):
    nums.sort()
    median = nums[len(nums) // 2]
    return sum(abs(n - median) for n in nums)   # sum of distances to the median''',
         complexity="Time O(n log n) (O(n) with quickselect), space O(1).",
         pitfalls="Using the mean (minimizes squared, not absolute, distance); off-by-one median index.",
         example="min_moves2([1,2,3]) -> 2."),
    dict(cat="dsa", title="Check if Array Is Sorted and Rotated",
         answer="Decide whether a non-decreasing sorted array could have been ROTATED to produce this one. Such an array has at most ONE 'drop' where an element is greater than the next (checking circularly). Count the drops; valid iff there's 0 or 1.",
         tags=["sorted-and-rotated","array","dsa"],
         code='''# Could a non-decreasing sorted array be rotated into this array?
def check_sorted_rotated(nums):
    n = len(nums)
    # a rotated sorted array has at most one 'drop' (nums[i] > next), circularly
    breaks = sum(1 for i in range(n) if nums[i] > nums[(i + 1) % n])
    return breaks <= 1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not checking circularly (the wrap-around from last to first); allowing more than one drop.",
         example="check_sorted_rotated([3,4,5,1,2]) -> True; check_sorted_rotated([2,1,3,4]) -> False."),
    dict(cat="dsa", title="Pairs of Songs Divisible by 60",
         answer="Count index pairs (i<j) whose durations sum to a multiple of 60. Work with remainders mod 60: for each song's remainder r, the complementary remainder is (60-r)%60 — add how many previous songs had that complement, then record r. One pass, O(n).",
         tags=["pairs-divisible-60","modular-arithmetic","hash-map","array","dsa"],
         code='''# Count pairs (i<j) with (time[i]+time[j]) % 60 == 0.
def num_pairs_divisible_by_60(time):
    remainders = [0] * 60
    count = 0
    for t in time:
        r = t % 60
        complement = (60 - r) % 60     # the remainder that pairs with r
        count += remainders[complement]
        remainders[r] += 1
    return count''',
         complexity="Time O(n), space O(1).",
         pitfalls="Mishandling r=0 (complement must be 0 via the modulo); brute-force O(n^2).",
         example="num_pairs_divisible_by_60([30,20,150,100,40]) -> 3."),
    dict(cat="dsa", title="Minimum Time Visiting All Points",
         answer="Visit points in the given order; each second you can move one step horizontally, vertically, or DIAGONALLY. The time between two points is the CHEBYSHEV distance max(|dx|, |dy|) — diagonal moves cover both axes at once. Sum it over consecutive points.",
         tags=["min-time-points","chebyshev-distance","geometry","array","dsa"],
         code='''# Min seconds to visit points in order (diagonal moves = Chebyshev distance).
def min_time_to_visit_all_points(points):
    total = 0
    for i in range(1, len(points)):
        dx = abs(points[i][0] - points[i - 1][0])
        dy = abs(points[i][1] - points[i - 1][1])
        total += max(dx, dy)          # Chebyshev distance (diagonals count as 1)
    return total''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using Manhattan (dx+dy) instead of Chebyshev; forgetting diagonals are free on both axes.",
         example="min_time_to_visit_all_points([[1,1],[3,4],[-1,0]]) -> 7."),
    dict(cat="dsa", title="Greatest Common Divisor of Strings",
         answer="Find the largest string x such that both s and t are made by repeating x. It exists ONLY if s+t == t+s (they 'commute'); when it does, the answer's length is gcd(len(s), len(t)), so return that prefix of s.",
         tags=["gcd-of-strings","string","gcd","math","dsa"],
         code='''# Largest string that divides both s and t (concatenation-based GCD).
import math
def gcd_of_strings(s, t):
    if s + t != t + s:
        return ""                     # no common divisor if they don't commute
    g = math.gcd(len(s), len(t))      # the GCD length is the answer's length
    return s[:g]''',
         complexity="Time O(len(s) + len(t)), space O(len(s)+len(t)).",
         pitfalls="Assuming a divisor always exists; not checking the commute condition s+t==t+s.",
         example="gcd_of_strings('ABCABC','ABC') -> 'ABC'; gcd_of_strings('ABABAB','ABAB') -> 'AB'."),
    dict(cat="dsa", title="Sort Integers by Number of 1 Bits",
         answer="Sort the integers ascending by their POPCOUNT (number of set bits), breaking ties by the value itself. A single sort with a composite key (popcount, value) does it.",
         tags=["sort-by-bits","bit-manipulation","sorting","dsa"],
         code='''# Sort ascending by popcount (number of set bits), ties by value.
def sort_by_bits(arr):
    return sorted(arr, key=lambda x: (bin(x).count('1'), x))''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Forgetting the value tie-breaker; counting bits inefficiently in a hot loop.",
         example="sort_by_bits([0,1,2,3,4,5,6,7,8]) -> [0,1,2,4,8,3,5,6,7]."),
    dict(cat="dsa", title="Minimum Operations to Make the Array Increasing",
         answer="Each operation adds 1 to an element; find the fewest operations to make the array STRICTLY increasing. Greedily walk left to right, forcing each element to be at least prev+1: if it's not, bump it up and count the difference.",
         tags=["min-operations-increasing","greedy","array","dsa"],
         code='''# Min +1 operations to make the array strictly increasing.
def min_operations(nums):
    operations = 0
    prev = nums[0]
    for i in range(1, len(nums)):
        if nums[i] <= prev:
            operations += prev + 1 - nums[i]   # bump up to prev+1
            prev = prev + 1
        else:
            prev = nums[i]
    return operations''',
         complexity="Time O(n), space O(1).",
         pitfalls="Allowing equal neighbours (must be strictly increasing); not updating prev after a bump.",
         example="min_operations([1,1,1]) -> 3."),
    dict(cat="glossary", title="Reverse proxy vs forward proxy",
         answer="Both sit between clients and servers but serve OPPOSITE sides. A FORWARD proxy sits in front of CLIENTS and represents them outward (corporate egress proxy, VPN, content filter) — the server sees the proxy, not the user. A REVERSE proxy sits in front of SERVERS and represents them to the world (Nginx, a CDN edge, an API gateway) — the client sees the proxy, not the backend. Reverse proxies do load balancing, TLS termination, caching, and hide/protect the origin.",
         tags=["reverse-proxy","forward-proxy","networking","nginx"],
         example="A company's forward proxy filters employees' outbound traffic; a website's reverse proxy (Nginx) terminates TLS, caches, and load-balances across backends the client never sees."),
    dict(cat="glossary", title="WAF (Web Application Firewall)",
         answer="A security layer that inspects HTTP traffic and BLOCKS malicious requests targeting web-app vulnerabilities — SQL injection, XSS, path traversal — using rule sets (e.g. the OWASP Core Rule Set) and increasingly ML. It sits in front of the app (often at the CDN/reverse-proxy edge) as defense-in-depth, catching attacks before they reach the application. It complements, not replaces, secure coding.",
         tags=["waf","web-application-firewall","owasp","security","defense-in-depth"],
         example="A WAF at the CDN edge blocks a request containing ' UNION SELECT ...' before it reaches the app, mitigating SQL injection even if a code path was vulnerable."),
    dict(cat="glossary", title="DDoS mitigation",
         answer="Defending against Distributed Denial-of-Service attacks that flood a target from many sources to exhaust its capacity. Techniques: absorb/scale with a large distributed network (CDN/anycast spreads load across PoPs), RATE LIMITING and traffic scrubbing (drop malicious patterns), SYN-flood protection, blackholing or challenges (CAPTCHA) for suspicious clients, and over-provisioning. Volumetric L3/4 floods go to scrubbing centers; L7 (application) floods need smarter request analysis.",
         tags=["ddos","mitigation","anycast","rate-limiting","security"],
         example="A volumetric UDP flood is scrubbed across a CDN's global anycast network before reaching the origin; an L7 HTTP flood is throttled with rate limits and CAPTCHAs for suspicious IPs."),
    dict(cat="glossary", title="DNSSEC",
         answer="DNS Security Extensions — adds cryptographic SIGNATURES to DNS records so resolvers can VERIFY a response genuinely came from the authoritative zone and wasn't forged (defending against DNS spoofing / cache poisoning). A chain of trust runs from the root zone down. It provides AUTHENTICITY and integrity but NOT confidentiality — queries/answers stay plaintext (that's what DoH/DoT add).",
         tags=["dnssec","dns","spoofing","cache-poisoning","security"],
         example="With DNSSEC a resolver rejects a poisoned 'bank.com -> attacker IP' response because the record's signature doesn't validate against the zone's key — stopping the redirect."),
    dict(cat="glossary", title="gzip vs brotli",
         answer="Two HTTP compression algorithms that shrink text responses (HTML/CSS/JS/JSON) to save bandwidth and speed loads; the client advertises support via Accept-Encoding and the server picks one. GZIP (DEFLATE) is universal, fast, and good. BROTLI (Google) compresses ~15-25% SMALLER at high quality (ideal for static assets precompressed at build time) but is slower at max levels, so it's often used at a lower level for dynamic content. Both are lossless.",
         tags=["gzip","brotli","compression","http","performance"],
         example="A CDN serves a pre-brotli-compressed app.js (smaller than gzip) to browsers sending 'Accept-Encoding: br', falling back to gzip for older clients."),
    dict(cat="conceptual", title="Why does the median minimize total absolute distance while the mean minimizes squared distance?",
         answer="It's about which error you penalize. To pick one point c minimizing the sum of ABSOLUTE distances Σ|x_i - c|, consider nudging c up slightly: it decreases the distance to every point above c and increases it to every point below, for a net change of (points below) - (points above). That's zero exactly when equal numbers lie on each side — the MEDIAN. So the median balances COUNTS and is robust (a far outlier is still just 'one point above'). If instead you minimize the sum of SQUARED distances Σ(x_i - c)², the derivative is 2Σ(c - x_i), zero when c equals the average — the MEAN. Squaring weights each point by its distance, so far points pull c strongly (the mean is outlier-sensitive). This is exactly why 'min ±1 moves to equalize an array' (a linear/L1 cost) converges to the MEDIAN, while least-squares regression and variance use the MEAN. The cost's shape — L1 (absolute) vs L2 (squared) — dictates the optimal center: L1 -> median, L2 -> mean.",
         tags=["median","mean","l1","l2","optimization","why"],
         example="For [1, 2, 100], equalizing with ±1 moves is cheapest at the median 2 (cost 99), not the mean ~34 (cost ~132) — absolute cost cares how many points move, not how far the outlier is."),
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
