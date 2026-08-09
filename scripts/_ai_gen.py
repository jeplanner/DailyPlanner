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
    dict(cat="dsa", title="Truncate Sentence",
         answer="Keep only the first k words of a space-separated sentence. Split into words and join the first k back together.",
         tags=["truncate-sentence","string","split","dsa"],
         code='''# Keep only the first k words of a sentence.
def truncate_sentence(s, k):
    return " ".join(s.split()[:k])   # split into words, keep the first k''',
         complexity="Time O(n), space O(n).",
         pitfalls="Truncating by characters instead of words; off-by-one on k.",
         example="truncate_sentence('Hello how are you Contestant', 4) -> 'Hello how are you'."),
    dict(cat="dsa", title="Sorting the Sentence",
         answer="Each word of a shuffled sentence ends with its 1-based POSITION digit; reconstruct the original sentence. Read the last character of each word as its index, strip it, and place the word at that position.",
         tags=["sorting-sentence","string","dsa"],
         code='''# Reconstruct a sentence where each word ends with its 1-based position.
def sort_sentence(s):
    words = s.split()
    result = [""] * len(words)
    for w in words:
        pos = int(w[-1])             # last char is the 1-based position
        result[pos - 1] = w[:-1]     # strip the digit, place by position
    return " ".join(result)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Not stripping the digit; using 0-based indexing (positions are 1-based).",
         example="sort_sentence('is2 sentence4 This1 a3') -> 'This is a sentence'."),
    dict(cat="dsa", title="Rank Transform of an Array",
         answer="Replace each element with its RANK: the smallest value gets rank 1, the next-distinct gets 2, and EQUAL values share a rank. Sort the distinct values, map each to its 1-based rank, then look up every element.",
         tags=["rank-transform","sorting","hash-map","array","dsa"],
         code='''# Replace each element with its rank (1 = smallest, ties share a rank).
def array_rank_transform(arr):
    rank = {v: i + 1 for i, v in enumerate(sorted(set(arr)))}
    return [rank[v] for v in arr]''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Not deduping (ties must share a rank); 0-based ranks.",
         example="array_rank_transform([40,10,20,30]) -> [4,1,2,3]; array_rank_transform([100,100,100]) -> [1,1,1]."),
    dict(cat="dsa", title="Sum of All Odd Length Subarrays",
         answer="Sum the totals of every ODD-length contiguous subarray. Instead of enumerating subarrays (O(n^2) or worse), compute each element's CONTRIBUTION: index i appears in (i+1)*(n-i) subarrays; half-ish of those (rounded up) have odd length, so it contributes ((count+1)//2) * value.",
         tags=["sum-odd-subarrays","contribution","math","array","dsa"],
         code='''# Sum over all odd-length contiguous subarrays (via each element's contribution).
def sum_odd_length_subarrays(arr):
    total = 0
    n = len(arr)
    for i in range(n):
        left = i + 1                  # choices for the subarray's start
        right = n - i                 # choices for the subarray's end
        subarrays = left * right      # subarrays containing index i
        odd = (subarrays + 1) // 2    # how many have odd length
        total += odd * arr[i]
    return total''',
         complexity="Time O(n), space O(1).",
         pitfalls="Enumerating all subarrays (slow); miscounting odd-length occurrences.",
         example="sum_odd_length_subarrays([1,4,2,5,3]) -> 58."),
    dict(cat="dsa", title="Kth Missing Positive Number",
         answer="Given a sorted array of distinct positives, find the kth MISSING positive integer. Walk the positive integers, advancing the array pointer when a number is present and counting misses otherwise; return the current number when the miss count hits k. (A binary-search O(log n) variant also exists.)",
         tags=["kth-missing-positive","array","binary-search","dsa"],
         code='''# The kth missing positive integer from a sorted array of positives.
def find_kth_positive(arr, k):
    missing = 0
    current = 1
    i = 0
    while True:
        if i < len(arr) and arr[i] == current:
            i += 1                   # this number is present
        else:
            missing += 1             # 'current' is missing
            if missing == k:
                return current
        current += 1''',
         complexity="Time O(n + k) (O(log n) with binary search), space O(1).",
         pitfalls="Off-by-one on the miss count; not advancing the array pointer on a match.",
         example="find_kth_positive([2,3,4,7,11], 5) -> 9."),
    dict(cat="dsa", title="Matrix Reshape",
         answer="Reshape an m×n matrix into r×c if the element counts match (m*n == r*c), preserving row-major order; otherwise return the original. Flatten the matrix, then slice the flat list into rows of length c.",
         tags=["matrix-reshape","matrix","dsa"],
         code='''# Reshape a matrix to r x c if the element count matches, else return it.
def matrix_reshape(mat, r, c):
    rows, cols = len(mat), len(mat[0])
    if rows * cols != r * c:
        return mat                   # incompatible reshape -> unchanged
    flat = [v for row in mat for v in row]
    return [flat[i * c:(i + 1) * c] for i in range(r)]''',
         complexity="Time O(m*n), space O(m*n).",
         pitfalls="Not checking the count compatibility; wrong slice bounds when rebuilding rows.",
         example="matrix_reshape([[1,2],[3,4]], 1, 4) -> [[1,2,3,4]]."),
    dict(cat="dsa", title="Largest Perimeter Triangle",
         answer="Find the largest perimeter of a valid triangle formed by any three of the given side lengths. Sort descending and check consecutive triples: the triangle inequality holds for the largest side iff it's less than the sum of the other two, so the first valid triple gives the max perimeter.",
         tags=["largest-perimeter-triangle","sorting","greedy","math","dsa"],
         code='''# Largest perimeter of a valid triangle from three of the given lengths.
def largest_perimeter(nums):
    nums.sort(reverse=True)
    for i in range(len(nums) - 2):
        # a valid triangle needs the two smaller sides to exceed the largest
        if nums[i] < nums[i + 1] + nums[i + 2]:
            return nums[i] + nums[i + 1] + nums[i + 2]
    return 0''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Checking the wrong inequality direction; not sorting to reach the max first.",
         example="largest_perimeter([3,6,2,3]) -> 8  (2+3+3); largest_perimeter([1,2,1]) -> 0."),
    dict(cat="dsa", title="Can Make Arithmetic Progression",
         answer="Decide whether the numbers can be reordered into an arithmetic progression (constant difference between consecutive terms). Sort them, compute the first difference, and verify every subsequent gap matches it.",
         tags=["arithmetic-progression","sorting","array","dsa"],
         code='''# Can the numbers be reordered into an arithmetic progression?
def can_make_arithmetic(arr):
    arr.sort()
    diff = arr[1] - arr[0]
    for i in range(2, len(arr)):
        if arr[i] - arr[i - 1] != diff:   # inconsistent common difference
            return False
    return True''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Not sorting first; assuming length >= 2 without checking.",
         example="can_make_arithmetic([3,5,1]) -> True (1,3,5); can_make_arithmetic([1,2,4]) -> False."),
    dict(cat="glossary", title="QUIC",
         answer="A modern transport protocol built ON TOP of UDP (the basis of HTTP/3) that delivers TCP-like reliability + TLS encryption while avoiding TCP's limits. Wins: streams are INDEPENDENT (a lost packet stalls only its own stream, killing transport-level head-of-line blocking), the handshake merges transport + TLS into ~1-RTT (0-RTT on resumption), and connections survive IP changes via a connection ID (seamless Wi-Fi<->cellular handoff). It runs in user space, so it evolves faster than kernel TCP.",
         tags=["quic","http3","transport","udp","networking"],
         example="A phone switching from Wi-Fi to cellular keeps its QUIC/HTTP/3 connection alive via the connection ID, whereas a TCP connection (tied to the IP 4-tuple) would break."),
    dict(cat="glossary", title="DNS recursion / resolution",
         answer="How a hostname becomes an IP. A stub resolver asks a RECURSIVE resolver (your ISP's or 8.8.8.8) which does the legwork: query a ROOT server (-> .com TLD servers), then the TLD server (-> the domain's authoritative nameserver), then the authoritative server (-> the IP). Results are CACHED at each level with a TTL. 'Recursive' = the resolver does the whole chain for you; 'iterative' = each server just refers you onward.",
         tags=["dns","recursion","resolution","caching","networking"],
         example="Resolving www.example.com, the recursive resolver walks root -> .com -> example.com's authoritative server, gets the IP, caches it for the TTL, and returns it."),
    dict(cat="glossary", title="OpenID Connect (OIDC)",
         answer="An IDENTITY layer on top of OAuth2. OAuth2 handles AUTHORIZATION (granting scoped access via an access token); OIDC adds AUTHENTICATION (proving who the user is) via an ID TOKEN — a signed JWT with identity claims (sub, email, name). It powers 'Sign in with Google/Apple'. In short: OAuth2 = 'can this app access X?'; OIDC = 'who is this user?'.",
         tags=["oidc","openid-connect","oauth2","authentication","sso"],
         example="'Sign in with Google' uses OIDC: after consent, Google returns an ID token (a JWT) proving the user's identity to your app, plus an access token to call Google APIs."),
    dict(cat="glossary", title="PKCE",
         answer="Proof Key for Code Exchange — an OAuth2 extension securing the authorization-code flow for PUBLIC clients (mobile apps, SPAs) that can't safely store a client secret. The app makes a random 'code verifier', sends its hash (the 'code challenge') when requesting the auth code, then sends the original verifier when exchanging the code for a token. An attacker who intercepts the code can't use it without the verifier — defeating code-interception attacks.",
         tags=["pkce","oauth2","mobile","security","authorization-code"],
         example="A mobile app using PKCE sends a hashed challenge up front; even if malware grabs the returned auth code, it can't exchange it for a token without the original code verifier."),
    dict(cat="glossary", title="Certificate pinning",
         answer="Hardcoding (pinning) the expected server certificate or public key in the CLIENT, so it trusts only THAT specific cert/key rather than any cert signed by a trusted CA. It defends against a compromised or rogue CA issuing a fraudulent certificate for your domain (a MITM). Trade-off: rotating the cert without updating the app breaks connections — so pin a backup key or the CA and plan rotation carefully.",
         tags=["certificate-pinning","tls","mitm","security","mobile"],
         example="A banking app pins its server's public key; even if an attacker tricks a CA into issuing a valid cert for the bank's domain, the app rejects it because it doesn't match the pinned key."),
    dict(cat="conceptual", title="Why did QUIC/HTTP/3 build a new protocol over UDP instead of just improving TCP?",
         answer="Two barriers made fixing TCP impractical. First, OSSIFICATION: TCP lives in the OS KERNEL and is inspected/'helped' by middleboxes (routers, firewalls, NAT, load balancers) everywhere; any change to TCP's wire format tends to be dropped or mangled by them, so new TCP features take a decade-plus and often can't deploy at all. UDP is treated as opaque datagrams, sidestepping middleboxes. Second, TCP has an inherent limit that can't be patched: it delivers a SINGLE ordered byte stream, so with HTTP/2 multiplexing one lost packet blocks ALL streams (transport-level head-of-line blocking) — fixing it needs per-stream sequencing at the transport, i.e. a different protocol. QUIC puts reliability, ordering, and independent streams IN USER SPACE over UDP: no cross-stream HOL blocking, a merged transport+TLS handshake (1-RTT/0-RTT), connection migration across IP changes, and the ability to EVOLVE via app/browser updates (no kernel/middlebox changes). So it wasn't 'UDP beats TCP' but 'UDP is the only path both deployable through today's internet AND open to redesigning the transport.'",
         tags=["quic","tcp","udp","ossification","http3","why"],
         example="Google could roll QUIC improvements to billions of Chrome users with a browser update; the equivalent TCP change would need every OS kernel and middlebox on the internet to update first — which is why HTTP/3 lives on UDP."),
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
