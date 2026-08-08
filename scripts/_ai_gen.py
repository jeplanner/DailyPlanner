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
    dict(cat="dsa", title="Count Negatives in a Sorted Matrix",
         answer="Count negatives in a matrix whose rows and columns are sorted in NON-INCREASING order. Staircase walk from the bottom-left: if the current cell is negative, all cells to its right in that row are too (add them) and move up; otherwise move right. O(rows+cols).",
         tags=["count-negatives","matrix","staircase-search","dsa"],
         code='''# Count negatives in a matrix sorted descending in rows and columns.
def count_negatives(grid):
    rows, cols = len(grid), len(grid[0])
    count = 0
    r, c = rows - 1, 0                # start at the bottom-left corner
    while r >= 0 and c < cols:
        if grid[r][c] < 0:
            count += cols - c        # all cells to the right are negative too
            r -= 1                    # move up a row
        else:
            c += 1                    # move right
    return count''',
         complexity="Time O(rows + cols), space O(1).",
         pitfalls="Scanning every cell (O(m*n) — the sorted structure allows O(m+n)); wrong start corner.",
         example="count_negatives([[4,3,2,-1],[3,2,1,-1],[1,1,-1,-2],[-1,-1,-2,-3]]) -> 8."),
    dict(cat="dsa", title="Lucky Numbers in a Matrix",
         answer="A lucky number is the MINIMUM of its row AND the MAXIMUM of its column (matrix has distinct values). Compute the set of row-minimums and the set of column-maximums; their intersection is the lucky numbers.",
         tags=["lucky-numbers","matrix","set-intersection","dsa"],
         code='''# A lucky number is the min of its row and the max of its column.
def lucky_numbers(matrix):
    row_mins = {min(row) for row in matrix}
    col_maxs = {max(col) for col in zip(*matrix)}   # zip(*m) gives columns
    return list(row_mins & col_maxs)                # values that are both''',
         complexity="Time O(m*n), space O(m + n).",
         pitfalls="Confusing rows/columns; zip(*matrix) transposes to iterate columns.",
         example="lucky_numbers([[3,7,8],[9,11,13],[15,16,17]]) -> [15]."),
    dict(cat="dsa", title="Check If It Is a Straight Line",
         answer="Determine whether all given 2-D points are collinear. Use the CROSS-PRODUCT test to avoid division/slope-by-zero issues: three points are collinear when (y1-y0)(x-x0) == (y-y0)(x1-x0). Check every point against the first two.",
         tags=["straight-line","geometry","cross-product","dsa"],
         code='''# Do all points lie on a single straight line? (cross-product, no division)
def check_straight_line(coordinates):
    (x0, y0), (x1, y1) = coordinates[0], coordinates[1]
    for x, y in coordinates[2:]:
        # collinear iff slopes equal, written without division
        if (y1 - y0) * (x - x0) != (y - y0) * (x1 - x0):
            return False
    return True''',
         complexity="Time O(n), space O(1).",
         pitfalls="Dividing to compare slopes (vertical lines / float error); comparing only adjacent points.",
         example="check_straight_line([[1,2],[2,3],[3,4],[4,5]]) -> True; [[1,1],[2,2],[3,4]] -> False."),
    dict(cat="dsa", title="Valid Mountain Array",
         answer="A valid mountain STRICTLY increases to a single peak then STRICTLY decreases, with the peak neither first nor last (length >= 3). Walk up while strictly increasing, then require you're not at an end, then walk down; you must finish exactly at the last index.",
         tags=["valid-mountain","array","two-pointers","dsa"],
         code='''# Is the array a valid mountain? (strictly up, one peak, strictly down)
def valid_mountain_array(arr):
    n = len(arr)
    if n < 3:
        return False
    i = 0
    while i + 1 < n and arr[i] < arr[i + 1]:
        i += 1                       # climb up
    if i == 0 or i == n - 1:
        return False                 # peak can't be first or last
    while i + 1 < n and arr[i] > arr[i + 1]:
        i += 1                       # come down
    return i == n - 1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Allowing equal neighbours (must be strict); a plateau or a peak at the boundary.",
         example="valid_mountain_array([0,3,2,1]) -> True; valid_mountain_array([3,5,5]) -> False."),
    dict(cat="dsa", title="Kids With the Greatest Number of Candies",
         answer="Given each kid's candy count and a number of EXTRA candies, for each kid determine if giving them all the extra candies would make them have the GREATEST count (ties count). Compute the current max once, then test c + extra >= max for each kid.",
         tags=["kids-candies","array","greedy","dsa"],
         code='''# For each kid, would they have the most candies after getting 'extra' more?
def kids_with_candies(candies, extra):
    most = max(candies)
    return [c + extra >= most for c in candies]''',
         complexity="Time O(n), space O(n) for the output.",
         pitfalls="Recomputing the max inside the loop (O(n^2)); using > instead of >= (ties should count).",
         example="kids_with_candies([2,3,5,1,3], 3) -> [True,True,True,False,True]."),
    dict(cat="dsa", title="How Many Numbers Are Smaller Than the Current",
         answer="For each element, count how many OTHER elements are strictly smaller. With bounded values (0..100), use counting sort: tally counts, then a prefix sum gives, for each value v, how many elements are < v — an O(n) answer instead of O(n^2).",
         tags=["smaller-than-current","counting-sort","prefix-sum","array","dsa"],
         code='''# For each element, how many other elements are strictly smaller.
def smaller_numbers_than_current(nums):
    count = [0] * 101               # values are 0..100
    for n in nums:
        count[n] += 1
    prefix = [0] * 101
    for i in range(1, 101):
        prefix[i] = prefix[i - 1] + count[i - 1]   # how many values are < i
    return [prefix[n] for n in nums]''',
         complexity="Time O(n + K), space O(K).",
         pitfalls="O(n^2) brute force when counting-sort is O(n); off-by-one in the prefix (strictly smaller).",
         example="smaller_numbers_than_current([8,1,2,2,3]) -> [4,0,1,1,3]."),
    dict(cat="dsa", title="Decompress Run-Length Encoded List",
         answer="A list encodes pairs [freq, val, freq, val, ...]; expand it so each val appears freq times. Iterate in steps of 2, reading each (freq, val) pair and extending the output with val repeated freq times.",
         tags=["decompress-rle","run-length","array","dsa"],
         code='''# Decode pairs [freq, val, freq, val, ...] into the expanded list.
def decompress_rle_list(nums):
    result = []
    for i in range(0, len(nums), 2):
        freq, val = nums[i], nums[i + 1]
        result.extend([val] * freq)   # repeat val freq times
    return result''',
         complexity="Time O(total output length), space O(that).",
         pitfalls="Swapping freq and val; stepping by 1 instead of 2.",
         example="decompress_rle_list([1,2,3,4]) -> [2,4,4,4]."),
    dict(cat="dsa", title="Range Bitwise AND",
         answer="Compute the bitwise AND of ALL integers in [left, right]. The result is the COMMON BINARY PREFIX of left and right: any bit that differs across the range becomes 0 (since some number in the range flips it). Shift both right until they're equal, then shift the common prefix back.",
         tags=["range-bitwise-and","bit-manipulation","math","dsa"],
         code='''# Bitwise AND of all numbers in [left, right] = their common bit prefix.
def range_bitwise_and(left, right):
    shift = 0
    while left < right:              # strip differing low bits
        left >>= 1
        right >>= 1
        shift += 1
    return left << shift             # restore the common prefix''',
         complexity="Time O(log right), space O(1).",
         pitfalls="AND-ing every number (too slow for large ranges); forgetting to shift back.",
         example="range_bitwise_and(5, 7) -> 4; range_bitwise_and(0, 0) -> 0."),
    dict(cat="glossary", title="Idempotent HTTP methods",
         answer="A method is IDEMPOTENT if making the same request multiple times has the same effect as once. GET, PUT, DELETE, HEAD are idempotent (PUT sets a resource to a value; doing it twice leaves the same state; DELETE twice still ends deleted). POST is NOT (each usually creates a new resource). Safe methods (GET/HEAD) don't modify state at all. Idempotency lets clients/proxies safely RETRY on failure.",
         tags=["idempotent-methods","http","rest","retries","api"],
         example="A network glitch lets a client safely retry a PUT (same final state) or DELETE (already gone), but retrying a POST 'create order' could duplicate it — so POST needs an idempotency key."),
    dict(cat="glossary", title="HTTP status code families",
         answer="Status codes group by first digit: 1xx informational; 2xx SUCCESS (200 OK, 201 Created, 204 No Content); 3xx REDIRECTION (301 permanent, 302 temporary, 304 Not Modified); 4xx CLIENT errors (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 429 Too Many Requests); 5xx SERVER errors (500 Internal, 502 Bad Gateway, 503 Service Unavailable). The family tells you who's at fault and whether a retry could help.",
         tags=["http-status-codes","http","rest","api","errors"],
         example="A 503 (server, transient) is worth retrying with backoff; a 400 (client error) fails identically on retry, so don't."),
    dict(cat="glossary", title="ETag / conditional requests",
         answer="An ETag is a fingerprint (hash/version) of a resource the server returns. The client caches it and, next time, sends If-None-Match: <etag>; if the resource is unchanged the server replies 304 Not Modified with NO body — saving bandwidth. If-Match enables optimistic concurrency (reject a write if the ETag changed). It's how HTTP does efficient revalidation and conflict detection.",
         tags=["etag","conditional-request","caching","optimistic-concurrency","http"],
         example="A browser revalidates a cached image with If-None-Match; the server returns 304 (no body) if unchanged, so the browser reuses its cache instead of re-downloading."),
    dict(cat="glossary", title="Cookies vs tokens (JWT)",
         answer="Two ways to carry auth state. COOKIE/session auth stores a session ID in a cookie; the server keeps session state and looks it up each request — stateful, easy to revoke, but needs shared session storage to scale. TOKEN/JWT auth puts SIGNED claims in a token the client sends (usually a header); the server just verifies the signature — STATELESS and scalable, but hard to revoke before expiry and larger per request. Cookies suit browser apps (with CSRF protection); JWTs suit APIs/SPAs/microservices.",
         tags=["cookies","jwt","authentication","sessions","stateless"],
         example="A monolith web app uses a session cookie (easy server-side logout); a microservices API uses short-lived JWTs so any service verifies auth without a shared session store."),
    dict(cat="glossary", title="OAuth2 authorization flow",
         answer="OAuth2 lets a user grant a third-party app LIMITED, scoped access to their resources WITHOUT sharing their password. Authorization Code flow: the app redirects the user to the provider (Google), the user logs in and consents, the provider redirects back with a short-lived CODE, and the app exchanges that code (plus its secret) server-side for an ACCESS TOKEN (and refresh token) to call APIs with. It separates authentication (proving identity) from authorization (granting scoped access).",
         tags=["oauth2","authorization","access-token","sso","security"],
         example="'Sign in with Google': you're sent to Google, approve 'read your profile', Google redirects back with a code, your backend swaps it for an access token and fetches the profile — your Google password never touches the app."),
    dict(cat="conceptual", title="Why should PUT/DELETE be idempotent but POST not — and why does it matter for retries?",
         answer="Idempotency means repeating a request yields the same final STATE. PUT ('set resource X to this value') and DELETE ('remove X') are naturally idempotent — applied twice, the result is identical (X has the value; X is gone). POST ('create a new thing') is NOT — each call produces a NEW side effect. This matters for RETRIES on unreliable networks: a client that gets no response can't tell if the request was lost (never ran) or the ACK was lost (ran fine) — so to be safe it must retry. For idempotent methods, retrying is HARMLESS, which is why proxies, load balancers, and clients can safely auto-retry GET/PUT/DELETE. For POST, a blind retry risks DUPLICATE creation (double-charge, double-order), so you either don't auto-retry it or you make it idempotent with an IDEMPOTENCY KEY the server dedupes on. Designing writes to be idempotent (or key-protected) is exactly what makes at-least-once delivery safe.",
         tags=["idempotency","http","put","post","retries","why"],
         example="A payment 'POST /charge' retried after a timeout could charge twice; an Idempotency-Key header lets the server recognize the retry and return the original result, making the POST safe to retry like a PUT."),
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
