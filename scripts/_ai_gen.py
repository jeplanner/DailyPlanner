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
    dict(cat="dsa", title="Single Number II (appears once among triples)",
         answer="Every element appears three times except one that appears once — find it in O(n) time, O(1) space. Count set bits at each bit position across all numbers; a position's count mod 3 is nonzero only where the lone number has a 1. Reassemble those bits (and fix sign for 32-bit two's-complement).",
         tags=["single-number","bit-manipulation","counting","array","dsa"],
         code='''# The element appearing once when every other appears three times.
def single_number_ii(nums):
    result = 0
    for bit in range(32):
        count = 0
        for n in nums:
            if (n >> bit) & 1:
                count += 1            # count set bits at this position
        if count % 3:                 # the lone number owns this bit
            result |= (1 << bit)
    if result >= 2 ** 31:             # interpret as signed 32-bit
        result -= 2 ** 32
    return result''',
         complexity="Time O(32n), space O(1).",
         pitfalls="Ignoring negative numbers (Python ints are unbounded — fix the sign); using XOR (that only works for pairs).",
         example="single_number_ii([2,2,3,2]) -> 3."),
    dict(cat="dsa", title="Longest Repeating Character Replacement",
         answer="Find the longest substring that becomes all one character after replacing at most k characters. Sliding window tracking the count of the MOST frequent char in the window: the window is valid while (window size - max frequency) <= k (those are the chars to replace); shrink from the left when it isn't.",
         tags=["character-replacement","sliding-window","string","dsa"],
         code='''# Longest substring of one repeated char after replacing at most k chars.
from collections import defaultdict
def character_replacement(s, k):
    counts = defaultdict(int)
    left = 0
    max_freq = 0
    best = 0
    for right in range(len(s)):
        counts[s[right]] += 1
        max_freq = max(max_freq, counts[s[right]])   # commonest char in window
        while (right - left + 1) - max_freq > k:      # too many to replace
            counts[s[left]] -= 1
            left += 1
        best = max(best, right - left + 1)
    return best''',
         complexity="Time O(n), space O(1) (at most 26 keys).",
         pitfalls="Recomputing max_freq exactly (not needed — a stale max still gives the right answer); off-by-one on window size.",
         example="character_replacement('AABABBA', 1) -> 4."),
    dict(cat="dsa", title="Permutation in String",
         answer="Determine whether s2 contains any PERMUTATION of s1 as a contiguous substring. Slide a fixed window of length len(s1) over s2, maintaining a character-count map; the window is a permutation exactly when its counts match s1's counts. Update counts incrementally as the window moves.",
         tags=["permutation-in-string","sliding-window","anagram","string","dsa"],
         code='''# Does s2 contain any permutation of s1 as a substring? (sliding window)
from collections import Counter
def check_inclusion(s1, s2):
    if len(s1) > len(s2):
        return False
    need = Counter(s1)
    window = Counter(s2[:len(s1)])           # the first window
    if window == need:
        return True
    for i in range(len(s1), len(s2)):
        window[s2[i]] += 1                    # add the entering char
        left = s2[i - len(s1)]
        window[left] -= 1                     # remove the leaving char
        if window[left] == 0:
            del window[left]                 # keep the counters comparable
        if window == need:
            return True
    return False''',
         complexity="Time O(len(s2)), space O(1) (fixed alphabet).",
         pitfalls="Not deleting zero counts (Counter equality then fails); mis-indexing the leaving character.",
         example="check_inclusion('ab', 'eidbaooo') -> True  ('ba')."),
    dict(cat="dsa", title="Find Peak Element (binary search)",
         answer="Return the index of ANY peak (an element strictly greater than its neighbours) in O(log n). Binary search on the slope: if nums[mid] < nums[mid+1] you're on an ascending slope so a peak lies to the right; otherwise a peak is at mid or to the left. Treat out-of-bounds as -infinity.",
         tags=["find-peak","binary-search","array","dsa"],
         code='''# Find any peak (greater than its neighbours) index via binary search.
def find_peak_element(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] < nums[mid + 1]:
            lo = mid + 1              # ascending -> a peak is to the right
        else:
            hi = mid                  # descending -> peak at mid or left
    return lo''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Comparing to mid-1 without a bounds guard; using lo <= hi (can overshoot — use lo < hi).",
         example="find_peak_element([1,2,3,1]) -> 2  (value 3)."),
    dict(cat="dsa", title="Search in Rotated Sorted Array",
         answer="Find a target's index in a sorted array that's been rotated at an unknown pivot, in O(log n). At each step one half (left or right of mid) is still sorted — determine which, check if the target falls in that sorted half's range, and recurse into the correct side.",
         tags=["search-rotated","binary-search","array","dsa"],
         code='''# Search for target in a rotated sorted array in O(log n).
def search_rotated(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[lo] <= nums[mid]:         # the left half is sorted
            if nums[lo] <= target < nums[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                              # the right half is sorted
            if nums[mid] < target <= nums[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Wrong boundary comparisons (use <= carefully); forgetting which half is guaranteed sorted.",
         example="search_rotated([4,5,6,7,0,1,2], 0) -> 4."),
    dict(cat="dsa", title="Find Minimum in Rotated Sorted Array",
         answer="Find the minimum element of a rotated sorted array in O(log n). Compare nums[mid] to nums[hi]: if nums[mid] > nums[hi] the rotation point (and minimum) is to the RIGHT of mid; otherwise the minimum is at mid or to its left. Converges to the single smallest element.",
         tags=["find-minimum-rotated","binary-search","array","dsa"],
         code='''# Find the minimum in a rotated sorted array (binary search on rotation).
def find_min_rotated(nums):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] > nums[hi]:
            lo = mid + 1              # minimum is in the right half
        else:
            hi = mid                  # minimum is at mid or to the left
    return nums[lo]''',
         complexity="Time O(log n), space O(1).",
         pitfalls="Comparing to nums[lo] instead of nums[hi] (breaks on some rotations); using lo <= hi.",
         example="find_min_rotated([3,4,5,1,2]) -> 1."),
    dict(cat="dsa", title="Koko Eating Bananas (binary search on the answer)",
         answer="Find the minimum integer eating speed so Koko finishes all banana piles within h hours. The answer is monotonic (faster speed never needs more hours), so BINARY SEARCH on the speed in [1, max pile]: for a candidate speed, sum ceil(pile/speed) hours; if it fits within h, try slower, else faster.",
         tags=["koko-bananas","binary-search-on-answer","array","dsa"],
         code='''# Min eating speed to finish all piles within h hours (binary search on answer).
import math
def min_eating_speed(piles, h):
    lo, hi = 1, max(piles)
    while lo < hi:
        speed = (lo + hi) // 2
        hours = sum(math.ceil(p / speed) for p in piles)   # hours at this speed
        if hours <= h:
            hi = speed                # feasible -> try a slower speed
        else:
            lo = speed + 1            # too slow -> speed up
    return lo''',
         complexity="Time O(n log(max pile)), space O(1).",
         pitfalls="Searching over the wrong range; using floor instead of ceil for per-pile hours.",
         example="min_eating_speed([3,6,7,11], 8) -> 4."),
    dict(cat="dsa", title="Capacity to Ship Packages Within D Days",
         answer="Find the least ship capacity to ship packages (in given order) within 'days' days. Feasibility is monotonic in capacity, so binary search on capacity in [max weight, total weight]: greedily simulate days needed for a candidate capacity; if it fits within the day limit, try smaller, else larger.",
         tags=["ship-packages","binary-search-on-answer","greedy","array","dsa"],
         code='''# Least ship capacity to ship all packages in order within 'days' days.
def ship_within_days(weights, days):
    lo, hi = max(weights), sum(weights)   # capacity must fit the biggest package
    def needed(cap):
        d, load = 1, 0
        for w in weights:
            if load + w > cap:
                d += 1                # start a new day
                load = 0
            load += w
        return d
    while lo < hi:
        mid = (lo + hi) // 2
        if needed(mid) <= days:
            hi = mid                  # feasible -> try smaller capacity
        else:
            lo = mid + 1
    return lo''',
         complexity="Time O(n log(sum)), space O(1).",
         pitfalls="Lower bound must be max(weights), not 1; off-by-one in the day count.",
         example="ship_within_days([1,2,3,4,5,6,7,8,9,10], 5) -> 15."),
    dict(cat="glossary", title="UCB (Upper Confidence Bound)",
         answer="A bandit strategy that picks the action with the highest OPTIMISTIC estimate: its mean reward plus an exploration bonus that shrinks as the action is tried more. 'Optimism in the face of uncertainty' — rarely-tried actions get a big bonus so they're explored, while well-known ones lean on their mean. It comes with strong (logarithmic) regret guarantees.",
         tags=["ucb","bandits","exploration","optimism","reinforcement-learning"],
         example="UCB1 scores each arm as mean + sqrt(2·ln(t)/n_arm); an arm pulled only twice gets a large bonus, so it's tried again before being written off."),
    dict(cat="glossary", title="Regret (online learning)",
         answer="In bandits/online learning, the cumulative difference between the reward you actually earned and the reward of the BEST fixed action in hindsight. Lower regret means closer to optimal. Good algorithms achieve SUBLINEAR regret (average regret -> 0), meaning they eventually learn the best action. It's the standard yardstick for exploration strategies.",
         tags=["regret","bandits","online-learning","evaluation"],
         example="If the best slot machine pays 1.0/pull and over 1000 pulls you averaged 0.9, total regret is ~100 — a good algorithm keeps regret growing slower than linearly."),
    dict(cat="glossary", title="CUPED (variance reduction)",
         answer="Controlled-experiment Using Pre-Experiment Data — a variance-reduction technique for A/B tests. It adjusts each user's metric using a pre-experiment covariate (e.g. their baseline activity), removing predictable variation unrelated to the treatment. This shrinks the metric's variance, so you detect the same effect with a MUCH smaller sample or shorter test.",
         tags=["cuped","variance-reduction","ab-testing","experimentation"],
         example="Using each user's pre-experiment spend to adjust their in-experiment spend can cut variance ~50%, roughly halving the users needed to reach significance."),
    dict(cat="glossary", title="Sample ratio mismatch (SRM)",
         answer="When the observed traffic split in an A/B test differs significantly from the intended split (e.g. you wanted 50/50 but got 52/48) — a red flag that the experiment is BROKEN (bad randomization, logging bugs, differential dropout). Any results are untrustworthy until fixed. Detected with a chi-square test on the assignment counts.",
         tags=["sample-ratio-mismatch","srm","ab-testing","data-quality"],
         example="A test meant to be 50/50 shows 51,000 vs 49,000 users; a chi-square test flags SRM (p<0.001), so you halt and debug before trusting any lift."),
    dict(cat="ml_system_design", title="Design a Dynamic Pricing system",
         answer="Set prices that change with demand, supply, and context to optimize revenue/utilization (surge pricing, hotels, e-commerce). (1) CLARIFY & SCALE: pick the objective (revenue, conversion, utilization) with fairness/rule constraints; real-time, per-item/region; avoid runaway prices. (2) DATA & LABELS: historical prices, demand, conversions, competitor prices, inventory — plus the COUNTERFACTUAL challenge that you only observe outcomes at prices you set. (3) FEATURES: demand/supply signals, time, location, inventory, seasonality, user segment, competitor prices. (4) MODEL: estimate a DEMAND CURVE (price -> conversion/quantity) via regression, then optimize expected revenue = price × predicted demand under constraints; contextual bandits to explore prices and learn elasticity. (5) EVAL: offline counterfactual/off-policy estimation; online A/B on revenue plus guardrails (conversion, complaints). (6) SERVING/MONITORING/AB: real-time pricing service with price caps/floors and smoothing, monitor elasticity drift and fairness, and explore carefully.",
         tags=["dynamic-pricing","demand-curve","elasticity","bandits","ml-system-design"],
         example="During a rain surge the model predicts higher ride demand, estimates riders' price sensitivity, and raises the multiplier to the revenue-maximizing point within a cap — validated by A/B against a fixed-price control."),
    dict(cat="ml_system_design", title="Design a Real-Time Bidding (RTB) system",
         answer="Bid in real time for ad impressions in an auction (tens of ms per request). (1) CLARIFY & SCALE: maximize advertiser value (conversions) within budget while bidding profitably; billions of auctions/day, <10-50ms, budget PACING. (2) DATA & LABELS: impression/click/conversion logs with win/loss and price; delayed conversions. (3) FEATURES: user, context (site, device, time), ad, and predicted pCTR/pCVR. (4) MODEL: predict CALIBRATED P(click) and P(conversion), compute expected value, then BID = value × pConversion adjusted by budget pacing and bid-shading for the auction type (first vs second price). (5) EVAL: calibration of pCTR/pCVR, ROI/CPA, win rate vs spend; offline replay + online. (6) SERVING/MONITORING/AB: ultra-low-latency serving with a feature store, a budget-pacing controller, monitoring of spend/CPA and calibration drift, and A/B on advertiser ROI.",
         tags=["real-time-bidding","rtb","ads","auction","calibration","ml-system-design"],
         example="For an incoming impression the system predicts a 2% conversion probability worth $50, bids ~$1.00 shaded for a first-price auction and paced against the remaining daily budget — all within 20ms."),
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
