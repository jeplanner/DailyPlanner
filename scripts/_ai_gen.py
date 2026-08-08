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
    dict(cat="dsa", title="Convert BST to Greater Tree",
         answer="Replace each node's value with the original value PLUS the sum of all values greater than it. A REVERSE in-order traversal (right, node, left) visits values from largest to smallest, so a running total accumulates the greater values before you reach each node.",
         tags=["convert-bst-greater","bst","reverse-inorder","recursion","dsa"],
         code='''# Replace each node's value with the sum of all values >= it (reverse in-order).
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def convert_bst(root):
    running = 0
    def reverse_inorder(node):
        nonlocal running
        if node is None:
            return
        reverse_inorder(node.right)   # visit larger values first
        running += node.val
        node.val = running            # node now holds the sum of all >= it
        reverse_inorder(node.left)
    reverse_inorder(root)
    return root''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Using forward in-order (accumulates smaller values); resetting the running sum per subtree.",
         example="BST 4 -> (1 -> (0,2), 6 -> (5,7)): node 6 becomes 6+7=13, node 4 becomes 4+5+6+7=22."),
    dict(cat="dsa", title="Add Digits (digital root)",
         answer="Repeatedly sum a number's digits until a single digit remains — but do it in O(1) using the DIGITAL ROOT formula: for n>0, the result is 1 + (n-1) % 9 (and 0 for 0). This works because a number is congruent to its digit sum mod 9.",
         tags=["add-digits","digital-root","math","dsa"],
         code='''# Repeatedly sum digits until one digit remains — O(1) via the digital root.
def add_digits(num):
    if num == 0:
        return 0
    return 1 + (num - 1) % 9    # digital-root formula''',
         complexity="Time O(1), space O(1).",
         pitfalls="Special-casing 0 (formula would give 1); looping the digit sum when O(1) exists.",
         example="add_digits(38) -> 2  (3+8=11 -> 1+1=2)."),
    dict(cat="dsa", title="Self Dividing Numbers",
         answer="A self-dividing number is divisible by EVERY digit it contains and contains no zero digit. List all such numbers in [1, n] by checking each number's digits.",
         tags=["self-dividing","math","digits","dsa"],
         code='''# Numbers divisible by each of their own digits (no zero digit), in [1, n].
def self_dividing_numbers(n):
    result = []
    for num in range(1, n + 1):
        s = str(num)
        if '0' not in s and all(num % int(d) == 0 for d in s):
            result.append(num)
    return result''',
         complexity="Time O(n * digits), space O(n).",
         pitfalls="Dividing by a zero digit (must exclude any 0); off-by-one on the inclusive range.",
         example="self_dividing_numbers(22) -> [1,2,3,4,5,6,7,8,9,11,12,15,22]."),
    dict(cat="dsa", title="Perfect Number",
         answer="A perfect number equals the sum of its PROPER divisors (all positive divisors except itself). Sum divisors up to sqrt(n), adding both i and n//i for each factor pair, then compare to n. (1 is a proper divisor of any n>1.)",
         tags=["perfect-number","math","divisors","dsa"],
         code='''# Is n a perfect number (equals the sum of its proper divisors)?
def is_perfect_number(n):
    if n <= 1:
        return False
    total = 1                       # 1 is always a proper divisor
    i = 2
    while i * i <= n:
        if n % i == 0:
            total += i
            if i != n // i:
                total += n // i     # add the paired divisor
        i += 1
    return total == n''',
         complexity="Time O(sqrt(n)), space O(1).",
         pitfalls="Including n itself as a divisor; double-counting a perfect-square factor.",
         example="is_perfect_number(28) -> True (1+2+4+7+14); is_perfect_number(12) -> False."),
    dict(cat="dsa", title="Arranging Coins",
         answer="Build a staircase where row k needs k coins; given n coins, return the number of COMPLETE rows. Since k full rows use k(k+1)/2 coins, binary-search the largest k with k(k+1)/2 <= n (or solve the quadratic directly).",
         tags=["arranging-coins","binary-search","math","dsa"],
         code='''# Full rows of a staircase you can build with n coins (row k needs k coins).
def arrange_coins(n):
    lo, hi = 0, n
    while lo <= hi:
        mid = (lo + hi) // 2
        coins_used = mid * (mid + 1) // 2   # coins for mid full rows
        if coins_used == n:
            return mid
        if coins_used < n:
            lo = mid + 1
        else:
            hi = mid - 1
    return hi                        # largest k with k(k+1)/2 <= n''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Overflow of k(k+1)/2 in fixed-int languages; returning lo instead of hi.",
         example="arrange_coins(5) -> 2  (rows 1 and 2 use 3 coins; a full row 3 needs 3 more)."),
    dict(cat="dsa", title="Longest Common Prefix",
         answer="Find the longest string that is a prefix of ALL strings in an array. Start with the first string as the candidate prefix and, for each other string, trim the prefix from the right until it matches that string's start; empty means no common prefix.",
         tags=["longest-common-prefix","string","dsa"],
         code='''# Longest common prefix string among an array of strings.
def longest_common_prefix(strs):
    if not strs:
        return ""
    prefix = strs[0]
    for s in strs[1:]:
        while not s.startswith(prefix):   # shrink until it matches s's start
            prefix = prefix[:-1]
            if not prefix:
                return ""
    return prefix''',
         complexity="Time O(total characters), space O(1).",
         pitfalls="Not handling an empty input list; assuming the first string is the shortest.",
         example="longest_common_prefix(['flower','flow','flight']) -> 'fl'."),
    dict(cat="dsa", title="Implement strStr() (indexOf)",
         answer="Return the index of the first occurrence of a needle string in a haystack, or -1 (like indexOf). The straightforward approach checks each length-m window of the haystack against the needle; KMP or Rabin-Karp does it in linear time for large inputs.",
         tags=["strstr","indexof","string-matching","string","dsa"],
         code='''# Index of the first occurrence of needle in haystack, or -1 (like indexOf).
def str_str(haystack, needle):
    if needle == "":
        return 0
    n, m = len(haystack), len(needle)
    for i in range(n - m + 1):
        if haystack[i:i + m] == needle:   # check each window of length m
            return i
    return -1''',
         complexity="Time O(n*m) naive (O(n+m) with KMP), space O(1).",
         pitfalls="Off-by-one on the window range (n-m+1); not handling an empty needle.",
         example="str_str('sadbutsad','sad') -> 0; str_str('leetcode','leeto') -> -1."),
    dict(cat="dsa", title="Reverse Words in a String",
         answer="Reverse the ORDER of words in a string while collapsing extra whitespace (leading/trailing/multiple spaces). Split on runs of whitespace (which drops empty tokens), reverse the word list, and join with single spaces.",
         tags=["reverse-words","string","split","dsa"],
         code='''# Reverse the order of words, collapsing extra whitespace.
def reverse_words(s):
    words = s.split()            # split on whitespace runs, dropping empties
    return " ".join(reversed(words))''',
         complexity="Time O(n), space O(n).",
         pitfalls="Reversing characters instead of words; not collapsing multiple/leading/trailing spaces.",
         example="reverse_words('  the sky  is blue ') -> 'blue is sky the'."),
    dict(cat="glossary", title="Sidecar pattern",
         answer="A deployment pattern where a helper container/process runs ALONGSIDE the main application (same pod/host, shared network and lifecycle) and handles CROSS-CUTTING concerns — logging, metrics, TLS, proxying, config — so the app doesn't have to. It keeps business code clean and lets you add capabilities uniformly across services without changing them.",
         tags=["sidecar","microservices","proxy","cross-cutting","deployment"],
         example="An Envoy proxy sidecar beside each service handles mTLS, retries, and metrics, so the service makes plain HTTP calls while the sidecar transparently secures and observes them."),
    dict(cat="glossary", title="Service mesh",
         answer="An infrastructure layer that manages SERVICE-TO-SERVICE communication for microservices via SIDECAR proxies (the data plane) coordinated by a control plane. It provides mTLS, traffic routing/load balancing, retries/timeouts/circuit breaking, and observability — WITHOUT app code changes (Istio, Linkerd). It moves resilience and security concerns out of each service into the platform.",
         tags=["service-mesh","istio","linkerd","sidecar","microservices"],
         example="With Istio you configure a 10%-to-v2 canary split and mutual TLS in the control plane; the sidecars enforce it, so no service needs to know about routing or certificates."),
    dict(cat="glossary", title="Streaming windows (tumbling / sliding / session)",
         answer="Ways to bound an infinite stream into finite chunks for aggregation. TUMBLING windows are fixed, non-overlapping intervals (every 1 min). SLIDING windows are fixed-size but overlap, advancing by a smaller step (last 5 min, updated every 1 min). SESSION windows group events by activity, closing after a gap of inactivity. Windowing plus watermarks handles out-of-order/late events.",
         tags=["streaming-windows","tumbling","sliding","session-window","stream-processing"],
         example="Clicks-per-minute uses tumbling windows; a 5-minute moving average uses sliding windows; grouping a user's actions until they're idle 30 min uses a session window."),
    dict(cat="glossary", title="Bitmap index",
         answer="An index storing, for each distinct value of a column, a BITMAP (one bit per row) marking which rows have that value. Extremely space-efficient and fast for LOW-cardinality columns; queries combine conditions with cheap bitwise AND/OR/NOT. Great for analytical/read-heavy warehouses but poor for high-cardinality or frequently-updated columns.",
         tags=["bitmap-index","indexing","olap","low-cardinality","database"],
         example="A 'gender' bitmap index answers 'WHERE gender=F AND country=US' by AND-ing two bitmaps — near-instant and tiny, ideal for OLAP."),
    dict(cat="glossary", title="Data skew",
         answer="When data is UNEVENLY distributed across partitions/keys, so a few partitions (or reducers/workers) get far more data than others — creating STRAGGLERS that bottleneck a distributed job (one task runs 10x longer while others finish). Common with popular keys or group-bys on a hot value. Mitigated by salting keys, skew-join handling, or repartitioning.",
         tags=["data-skew","partitioning","stragglers","spark","distributed-computing"],
         example="A Spark join on user_id where one 'guest' id covers 40% of rows overloads a single reducer; salting the hot key across N buckets spreads the load evenly."),
    dict(cat="conceptual", title="Why use a sidecar / service mesh instead of a shared library in each service?",
         answer="A shared LIBRARY forces every service to adopt it, be written in a compatible language, and REDEPLOY to get a fix or new policy — painful across dozens of polyglot services. A SIDECAR/mesh moves those concerns (mTLS, retries, timeouts, routing, metrics, tracing) into a proxy process beside each service, so they're LANGUAGE-AGNOSTIC (Python and Go services behave identically), UPGRADED INDEPENDENTLY of app code (patch the proxy, not 50 services), and CONFIGURED CENTRALLY via the control plane (change a timeout or canary split fleet-wide at once). The trade-offs are added latency (an extra proxy hop), resource overhead (a proxy per instance), and operational complexity — so a mesh pays off at scale/heterogeneity but is overkill for a few homogeneous services.",
         tags=["service-mesh","sidecar","microservices","cross-cutting","why"],
         example="To enforce mTLS everywhere, a library approach needs every team to add code and redeploy; with a mesh you flip one control-plane setting and the sidecars secure all traffic — no service code changes."),
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
