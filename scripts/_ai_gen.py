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
    dict(cat="dsa", title="Closest Binary Search Tree Value",
         answer="Find the value in a BST closest to a target. Walk down using the BST ordering (go left if target < node, else right), tracking the closest value seen. The ordering means you only follow one root-to-leaf path — O(height), not O(n).",
         tags=["closest-bst-value","bst","binary-search","dsa"],
         code='''# Value in the BST closest to a target (walk down using BST ordering).
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def closest_value(root, target):
    closest = root.val
    node = root
    while node:
        if abs(node.val - target) < abs(closest - target):
            closest = node.val       # a nearer value
        node = node.left if target < node.val else node.right
    return closest''',
         complexity="Time O(h), space O(1).",
         pitfalls="Scanning the whole tree (the BST order lets you go straight down); tie-breaking rule.",
         example="For BST 4 -> (2 -> (1,3), 5), closest_value(root, 3.7) -> 4."),
    dict(cat="dsa", title="Binary Tree Tilt",
         answer="A node's TILT is the absolute difference between the sums of its left and right subtrees; return the sum of all nodes' tilts. Post-order DFS returns each subtree's total sum while accumulating the tilt at every node.",
         tags=["binary-tree-tilt","binary-tree","dfs","recursion","dsa"],
         code='''# Sum of every node's tilt (abs difference of its subtree sums).
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def find_tilt(root):
    total_tilt = 0
    def subtree_sum(node):
        nonlocal total_tilt
        if node is None:
            return 0
        left = subtree_sum(node.left)
        right = subtree_sum(node.right)
        total_tilt += abs(left - right)   # this node's tilt
        return node.val + left + right    # subtree total for the parent
    subtree_sum(root)
    return total_tilt''',
         complexity="Time O(n), space O(h).",
         pitfalls="Returning the tilt instead of the subtree sum from the recursion; forgetting the abs.",
         example="For tree 1 -> (2, 3), tilt = |2-3| + 0 + 0 = 1."),
    dict(cat="dsa", title="Count Good Pairs",
         answer="Count index pairs (i, j) with i < j and nums[i] == nums[j]. For each value that appears c times, it forms C(c,2) = c*(c-1)/2 pairs; sum over the value counts — O(n) instead of the O(n^2) double loop.",
         tags=["count-good-pairs","counting","combinatorics","array","dsa"],
         code='''# Number of index pairs (i<j) with nums[i] == nums[j].
from collections import Counter
def num_identical_pairs(nums):
    counts = Counter(nums)
    # each value with count c contributes c*(c-1)/2 pairs
    return sum(c * (c - 1) // 2 for c in counts.values())''',
         complexity="Time O(n), space O(n).",
         pitfalls="Brute-force O(n^2); off-by-one in the C(c,2) formula.",
         example="num_identical_pairs([1,2,3,1,1,3]) -> 4."),
    dict(cat="dsa", title="XOR Operation in an Array",
         answer="Given n and start, the array is nums[i] = start + 2*i for i in [0, n); return the XOR of all its elements. Just accumulate the XOR in a loop (a closed-form O(1) formula also exists).",
         tags=["xor-operation","bit-manipulation","math","dsa"],
         code='''# XOR of the array where nums[i] = start + 2*i, for i in [0, n).
def xor_operation(n, start):
    result = 0
    for i in range(n):
        result ^= start + 2 * i
    return result''',
         complexity="Time O(n), space O(1).",
         pitfalls="Miscomputing the element formula (start + 2*i); initializing result wrong.",
         example="xor_operation(5, 0) -> 8  (0^2^4^6^8)."),
    dict(cat="dsa", title="Subtract the Product and Sum of Digits",
         answer="Return the product of an integer's digits MINUS the sum of its digits. Extract digits with %10 and //10, multiplying into a running product and adding into a running sum, then subtract.",
         tags=["product-sum-digits","math","digits","dsa"],
         code='''# Product of digits minus sum of digits of an integer.
def subtract_product_and_sum(n):
    product = 1
    total = 0
    while n:
        d = n % 10
        product *= d
        total += d
        n //= 10
    return product - total''',
         complexity="Time O(digits), space O(1).",
         pitfalls="Initializing product to 0 (kills it); summing instead of multiplying for the product.",
         example="subtract_product_and_sum(234) -> 15  (2*3*4=24, 2+3+4=9, 24-9=15)."),
    dict(cat="dsa", title="Find Center of Star Graph",
         answer="In a star graph, one CENTER node connects to every other node, so it appears in EVERY edge. Therefore the center is the node shared by the first two edges — check which endpoint of edge 0 also appears in edge 1.",
         tags=["find-center-star","graph","dsa"],
         code='''# The center node of a star graph appears in every edge.
def find_center(edges):
    a, b = edges[0]
    c, d = edges[1]
    # the center is the common endpoint of the first two edges
    return a if a in (c, d) else b''',
         complexity="Time O(1), space O(1).",
         pitfalls="Counting degrees over all edges (unnecessary — two edges suffice); index errors.",
         example="find_center([[1,2],[2,3],[4,2]]) -> 2."),
    dict(cat="dsa", title="Sum of Unique Elements",
         answer="Sum the elements that appear EXACTLY ONCE in the array. Count frequencies, then add up the values whose count is 1.",
         tags=["sum-unique","counting","hash-map","array","dsa"],
         code='''# Sum of elements that appear exactly once in the array.
from collections import Counter
def sum_of_unique(nums):
    counts = Counter(nums)
    return sum(n for n, c in counts.items() if c == 1)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Summing distinct values (that's different — this excludes any repeated value entirely).",
         example="sum_of_unique([1,2,3,2]) -> 4  (1 + 3)."),
    dict(cat="dsa", title="Three Consecutive Odds",
         answer="Return whether the array contains three CONSECUTIVE odd numbers. Track a running streak of odds, resetting to 0 on any even; return True as soon as the streak reaches 3.",
         tags=["three-consecutive-odds","array","dsa"],
         code='''# Are there three consecutive odd numbers anywhere in the array?
def three_consecutive_odds(arr):
    streak = 0
    for x in arr:
        if x % 2 == 1:
            streak += 1
            if streak == 3:
                return True
        else:
            streak = 0            # any even resets the streak
    return False''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not resetting the streak on an even; off-by-one on the streak length.",
         example="three_consecutive_odds([2,6,4,1]) -> False; three_consecutive_odds([1,2,34,3,4,5,7,23,12]) -> True."),
    dict(cat="glossary", title="CORS (Cross-Origin Resource Sharing)",
         answer="A browser mechanism that RELAXES the same-origin policy so a page can call a DIFFERENT origin, but only if the target server OPTS IN via response headers (Access-Control-Allow-Origin, etc.). For unsafe requests the browser first sends a PREFLIGHT OPTIONS request to check permission. CORS is enforced by the BROWSER (protecting the user), not the server, so it is NOT a server-side access control.",
         tags=["cors","same-origin-policy","browser","web-security"],
         example="A frontend at app.com calling api.otherco.com is blocked unless otherco returns Access-Control-Allow-Origin: https://app.com; the browser preflights a POST to confirm."),
    dict(cat="glossary", title="CSRF (Cross-Site Request Forgery)",
         answer="An attack where a malicious site tricks a logged-in user's BROWSER into sending an unwanted authenticated request to another site — abusing the fact that the browser auto-attaches the user's cookies. Defended with CSRF TOKENS (a per-request secret the attacker can't read), SameSite cookies, and checking the Origin/Referer header.",
         tags=["csrf","web-security","cookies","samesite","attack"],
         example="While you're logged into your bank, visiting evil.com auto-submits a POST to bank.com/transfer with your session cookie; a CSRF token evil.com can't read blocks it."),
    dict(cat="glossary", title="XSS (Cross-Site Scripting)",
         answer="Injecting malicious JavaScript into a page that OTHER users view, so it runs in their browser with the site's privileges (stealing cookies/tokens, keylogging, defacing). Types: stored (persisted), reflected (echoed from a request), DOM-based. Defended by ESCAPING/encoding user output, a Content Security Policy, and never trusting user input in HTML/JS contexts.",
         tags=["xss","web-security","injection","javascript","attack"],
         example="A comment field that renders <script>steal(document.cookie)</script> unescaped runs it for every viewer; HTML-escaping the comment on output neutralizes it."),
    dict(cat="glossary", title="SQL injection",
         answer="An attack where unsanitized user input alters the STRUCTURE of a SQL query, letting an attacker read/modify/delete data or bypass auth (classic: input ' OR '1'='1 makes a check always true). The fix is PARAMETERIZED/prepared statements (bind values separately from the SQL text) — never concatenate user input into SQL — plus least-privilege DB accounts and validation.",
         tags=["sql-injection","web-security","prepared-statement","injection","attack"],
         example="\"SELECT * FROM users WHERE name='\" + input + \"'\" with input '; DROP TABLE users; -- is catastrophic; a parameterized query makes the input pure data, not SQL."),
    dict(cat="glossary", title="Content Security Policy (CSP)",
         answer="A browser security header that WHITELISTS which sources of scripts, styles, images, etc. a page may load or execute — strong defense-in-depth against XSS. Declaring 'only run scripts from my own domain' (and forbidding inline scripts) means even injected <script> tags won't execute. It doesn't replace output escaping but sharply limits the blast radius; violation reports help find issues.",
         tags=["csp","content-security-policy","xss","web-security","defense-in-depth"],
         example="A CSP of script-src 'self' blocks an XSS-injected inline <script> because it isn't from an allowed source — even if the attacker got it into the HTML."),
    dict(cat="conceptual", title="Why does the browser enforce the same-origin policy, and why do we then need CORS?",
         answer="The SAME-ORIGIN POLICY (SOP) is a foundational browser rule: script from one origin (scheme+host+port) can't READ responses from a different origin. Without it, any site you visit could silently call your bank/email (your browser auto-sends your cookies) and read the responses — stealing your data or acting as you. SOP isolates origins so a malicious page can't exfiltrate another site's authenticated data. But the modern web legitimately needs cross-origin calls (a frontend on app.com talking to api.com, CDNs, third-party APIs), so CORS is the controlled EXEMPTION: rather than blindly blocking all cross-origin reads, the target SERVER can explicitly opt in via Access-Control-Allow-Origin headers, and the browser enforces those grants (preflighting risky requests). Crucially the BROWSER (protecting the user) enforces both — a non-browser client like curl isn't bound by them, which is why CORS is not server-side access control (you still need real auth). SOP is 'deny by default for safety'; CORS is 'the server-declared allowlist that safely re-enables legitimate cross-origin cases.'",
         tags=["same-origin-policy","cors","browser","web-security","why"],
         example="SOP stops evil.com's script from reading your logged-in bank.com data; CORS lets your own app.com frontend read api.app.com only because that API server explicitly allow-listed app.com."),
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
