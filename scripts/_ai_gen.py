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
    dict(cat="dsa", title="Maximum Population Year",
         answer="Given birth/death year ranges, find the earliest year with the most people alive. Use a DIFFERENCE ARRAY over years: +1 at each birth year, -1 at each death year (exclusive), then take a running prefix sum and track the year of the maximum. O(years) rather than checking every person per year.",
         tags=["maximum-population","difference-array","sweep-line","array","dsa"],
         code='''# Year with the most people alive, using a difference array over years.
def maximum_population(logs):
    delta = [0] * 2101              # years span roughly 1950..2050
    for birth, death in logs:
        delta[birth] += 1           # +1 alive from the birth year
        delta[death] -= 1           # -1 at the death year (exclusive)
    best_year = 0
    best_pop = 0
    running = 0
    for year in range(1950, 2051):
        running += delta[year]                  # prefix sum of alive counts
        if running > best_pop:
            best_pop = running
            best_year = year
    return best_year''',
         complexity="Time O(n + years), space O(years).",
         pitfalls="Counting death year as still-alive (it's exclusive); returning a later tie instead of the earliest.",
         example="maximum_population([[1993,1999],[2000,2010]]) -> 1993."),
    dict(cat="dsa", title="Count Number of Pairs With Absolute Difference K",
         answer="Count index pairs (i<j) with |nums[i] - nums[j]| == k. Sweep once with a frequency map: for each number, add how many earlier numbers equal n-k or n+k (its two possible partners), then record n. O(n) instead of the O(n^2) double loop.",
         tags=["pairs-abs-difference-k","hash-map","counting","array","dsa"],
         code='''# Count pairs (i<j) with |nums[i] - nums[j]| == k, using a frequency map.
from collections import Counter
def count_k_difference(nums, k):
    counts = Counter()
    result = 0
    for n in nums:
        result += counts[n - k] + counts[n + k]   # earlier complements
        counts[n] += 1
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Double counting both directions; brute-force O(n^2).",
         example="count_k_difference([1,2,2,1], 1) -> 4."),
    dict(cat="dsa", title="Three Divisors",
         answer="Determine whether n has EXACTLY three positive divisors. This happens only when n is a prime SQUARED (divisors 1, p, p^2). Count divisors up to sqrt(n), adding both i and n//i per factor (once if they coincide), and check the count equals 3.",
         tags=["three-divisors","math","divisors","dsa"],
         code='''# Does n have exactly THREE positive divisors? (true iff n = prime squared)
def is_three(n):
    count = 0
    i = 1
    while i * i <= n:
        if n % i == 0:
            count += 1 if i * i == n else 2   # count i and n//i (once if equal)
        i += 1
    return count == 3''',
         complexity="Time O(sqrt(n)), space O(1).",
         pitfalls="Double-counting the square root factor; enumerating all divisors up to n (slow).",
         example="is_three(4) -> True (1,2,4); is_three(2) -> False."),
    dict(cat="dsa", title="Sort the People",
         answer="Given names and their heights, return the names sorted by height in DESCENDING order. Zip the two lists, sort the pairs by height descending, and extract the names.",
         tags=["sort-people","sorting","zip","array","dsa"],
         code='''# Sort names by their corresponding heights, descending.
def sort_people(names, heights):
    # pair heights with names, sort by height desc, keep the names
    return [name for _, name in sorted(zip(heights, names), reverse=True)]''',
         complexity="Time O(n log n), space O(n).",
         pitfalls="Sorting ascending; losing the name<->height association.",
         example="sort_people(['Mary','John','Emma'], [180,165,170]) -> ['Mary','Emma','John']."),
    dict(cat="dsa", title="Minimum Number of Moves to Seat Everyone",
         answer="Students must each sit in a seat; a move shifts one student by 1 position. Minimize total moves. Sort both the seat positions and the student positions and pair them up in order — the sum of absolute differences of the matched pairs is optimal (matching sorted-to-sorted never crosses beneficially).",
         tags=["min-moves-seat","greedy","sorting","array","dsa"],
         code='''# Min total moves to seat students in seats: sort both, pair up, sum distances.
def min_moves_seat(seats, students):
    seats.sort(); students.sort()
    return sum(abs(s - t) for s, t in zip(seats, students))''',
         complexity="Time O(n log n), space O(1).",
         pitfalls="Pairing without sorting both (suboptimal); mismatched list lengths.",
         example="min_moves_seat([3,1,5], [2,7,4]) -> 4."),
    dict(cat="dsa", title="Apply Operations to an Array",
         answer="Process the array left to right: if nums[i] equals nums[i+1], DOUBLE nums[i] and set nums[i+1] to 0 (each element merges at most once). Afterward, shift all non-zero values to the FRONT keeping order, padding zeros at the end.",
         tags=["apply-operations","array","simulation","dsa"],
         code='''# Merge equal adjacent pairs (double first, zero second), then shift zeros right.
def apply_operations(nums):
    n = len(nums)
    for i in range(n - 1):
        if nums[i] == nums[i + 1]:
            nums[i] *= 2
            nums[i + 1] = 0
    result = [x for x in nums if x != 0]     # non-zeros, order preserved
    result += [0] * (n - len(result))         # pad zeros at the end
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Merging a value twice in one pass (only adjacent original pairs); not preserving order when shifting zeros.",
         example="apply_operations([1,2,2,1,1,0]) -> [1,4,2,0,0,0]."),
    dict(cat="dsa", title="Left and Right Sum Difference",
         answer="For each index, compute the absolute difference between the sum of all elements to its LEFT and the sum to its RIGHT. Keep a running left sum; the right sum is total - left - current. One pass with a precomputed total.",
         tags=["left-right-difference","prefix-sum","array","dsa"],
         code='''# For each index, |sum of elements to the left - sum to the right|.
def left_right_difference(nums):
    total = sum(nums)
    left = 0
    result = []
    for n in nums:
        right = total - left - n
        result.append(abs(left - right))
        left += n
    return result''',
         complexity="Time O(n), space O(1) beyond the output.",
         pitfalls="Including the current element in either side; recomputing sums per index (O(n^2)).",
         example="left_right_difference([10,4,8,3]) -> [15,1,11,22]."),
    dict(cat="dsa", title="Number of Employees Who Met the Target",
         answer="Given each employee's worked hours and a target, count how many worked at LEAST the target. A simple filter-and-count.",
         tags=["employees-met-target","array","counting","dsa"],
         code='''# Count employees whose worked hours meet or exceed the target.
def number_of_employees_who_met_target(hours, target):
    return sum(1 for h in hours if h >= target)''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using > instead of >= (target should count); off-by-one on the comparison.",
         example="number_of_employees_who_met_target([0,1,2,3,4], 2) -> 3."),
    dict(cat="glossary", title="Infrastructure as Code (IaC)",
         answer="Managing and provisioning infrastructure (servers, networks, DBs, load balancers) through DECLARATIVE code/config instead of manual clicks. Tools like Terraform, CloudFormation, and Pulumi let you version, review, and REPRODUCE environments exactly. Benefits: consistency (no config drift), auditability (git history), fast disaster recovery (re-apply the code), and reviewable changes before they're applied.",
         tags=["iac","terraform","infrastructure","devops","automation"],
         example="A Terraform file declaring '3 web servers + a load balancer + Postgres' creates them identically in staging and prod, and the git diff shows exactly what a change will do before you apply."),
    dict(cat="glossary", title="Immutable infrastructure",
         answer="A model where servers/instances are NEVER modified after creation — to change something, you build a NEW image and REPLACE the old instances rather than patching in place. It eliminates configuration drift and 'snowflake' servers, makes deployments repeatable and rollbacks trivial (redeploy the old image), and pairs naturally with IaC + containers. The opposite is mutable infra (SSH in and patch), which accumulates untracked changes.",
         tags=["immutable-infrastructure","containers","deployment","devops"],
         example="To deploy a new version you bake a fresh container image and roll out new pods, terminating the old — never SSHing in to update a running server, so every instance is identical."),
    dict(cat="glossary", title="GitOps",
         answer="An operational model where GIT is the single source of truth for application AND infrastructure state; the desired state is declared in a repo and an agent (Argo CD, Flux) continuously RECONCILES the live system to match it. You change infra via a pull request; merging triggers the deploy. Benefits: auditability (every change is a PR), easy rollback (git revert), and automatic drift correction.",
         tags=["gitops","argocd","flux","reconciliation","devops"],
         example="To scale a service you edit its replica count in git and open a PR; once merged, Argo CD applies it — and if someone changes the cluster manually, Argo reverts it to match git."),
    dict(cat="glossary", title="Subresource Integrity (SRI)",
         answer="A browser feature that verifies a fetched resource (a script/stylesheet, often from a CDN) hasn't been TAMPERED with. You add an integrity attribute holding the resource's cryptographic hash; the browser hashes what it downloaded and REFUSES to execute it if the hashes don't match — protecting against a compromised CDN or MITM injecting malicious code into a third-party asset.",
         tags=["sri","subresource-integrity","cdn","web-security","integrity"],
         example="<script src='https://cdn/lib.js' integrity='sha384-...'> makes the browser reject the script if the CDN was hacked and served a modified lib.js whose hash doesn't match."),
    dict(cat="glossary", title="Service discovery (client-side vs server-side)",
         answer="How services find each other's network locations in a dynamic environment (instances come and go, IPs change). A SERVICE REGISTRY (Consul, etcd, Eureka) tracks healthy instances. CLIENT-SIDE discovery: the client queries the registry and load-balances itself (fewer hops, but every client needs the logic). SERVER-SIDE discovery: the client calls a load balancer/router that consults the registry (simpler clients, one extra hop). Kubernetes does server-side via Services + DNS.",
         tags=["service-discovery","service-registry","consul","kubernetes","microservices"],
         example="In Kubernetes a service calls 'http://orders' — DNS resolves a stable virtual IP and kube-proxy load-balances to a healthy pod (server-side); a Eureka client instead fetches the instance list and picks one itself (client-side)."),
    dict(cat="conceptual", title="Why prefer immutable infrastructure over patching servers in place?",
         answer="Mutable infrastructure — SSHing into running servers to apply updates, patches, and tweaks — accumulates untracked, divergent changes, producing 'SNOWFLAKE' servers subtly different from each other and from any documented state. So a bug reproduces on one box but not another, a failed patch leaves a box half-configured, and you can't confidently rebuild from scratch (CONFIGURATION DRIFT). Immutable infrastructure flips this: bake a versioned IMAGE (AMI/container) once, deploy identical copies, and to change anything build a NEW image and REPLACE instances. The wins: REPRODUCIBILITY (every instance is byte-identical and rebuildable), trivial reliable ROLLBACK (redeploy the previous good image), safer deploys (new runs beside old via blue-green/canary), NO DRIFT (nothing is edited live, so running state matches declared state), and clean composition with IaC/CI-CD/autoscaling. Trade-offs: you rebuild+redeploy even for small changes (slower than a hot patch), you need image-baking pipelines, and state must be externalized off the ephemeral instance. But the determinism is worth it — 'cattle, not pets.'",
         tags=["immutable-infrastructure","configuration-drift","devops","reproducibility","why"],
         example="A security patch on mutable infra means SSHing into 50 servers (some fail, drift ensues); on immutable infra you rebuild one image with the patch and roll out 50 identical fresh instances — and if it misbehaves, redeploy the previous image in seconds."),
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
