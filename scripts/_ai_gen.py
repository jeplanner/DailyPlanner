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
    dict(cat="dsa", title="3Sum",
         answer="Find all UNIQUE triplets in an array that sum to zero. Sort first, then fix each element and use a two-pointer scan on the rest to find pairs that complete the sum. Skip duplicate values at the fixed element and both pointers to avoid repeated triplets. Sorting is what enables both the two-pointer move and easy de-duplication.",
         tags=["3sum","two-pointers","sorting","array","dsa"],
         code='''# All unique triplets that sum to zero (sorted two-pointer approach).
def three_sum(nums):
    nums.sort()
    result = []
    for i in range(len(nums) - 2):
        if i > 0 and nums[i] == nums[i-1]:
            continue                      # skip duplicate first elements
        left, right = i + 1, len(nums) - 1
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            if total < 0:
                left += 1
            elif total > 0:
                right -= 1
            else:
                result.append([nums[i], nums[left], nums[right]])
                left += 1
                right -= 1
                while left < right and nums[left] == nums[left-1]:
                    left += 1             # skip duplicate second elements
                while left < right and nums[right] == nums[right+1]:
                    right -= 1            # skip duplicate third elements
    return result''',
         complexity="Time O(n^2), space O(1) beyond the output.",
         pitfalls="Not skipping duplicates (repeated triplets); forgetting to move both pointers after a hit.",
         example="three_sum([-1,0,1,2,-1,-4]) -> [[-1,-1,2],[-1,0,1]]."),
    dict(cat="dsa", title="Valid Sudoku",
         answer="Check whether a 9x9 Sudoku board is valid — no digit repeats within any row, column, or 3x3 box (empty cells are '.'). Encode each constraint as a hashable key: (value,'row',r), (value,'col',c), and (value,'box',r//3,c//3). If any key is seen twice, it's invalid. Single pass over 81 cells.",
         tags=["valid-sudoku","hash-set","matrix","validation","dsa"],
         code='''# Check a 9x9 Sudoku has no duplicate in any row, column, or 3x3 box.
def is_valid_sudoku(board):
    seen = set()
    for r in range(9):
        for c in range(9):
            val = board[r][c]
            if val == '.':
                continue
            keys = ((val, 'r', r), (val, 'c', c), (val, 'b', r // 3, c // 3))
            for key in keys:
                if key in seen:
                    return False          # a duplicate constraint -> invalid
                seen.add(key)
    return True''',
         complexity="Time O(81) = O(1), space O(1).",
         pitfalls="Wrong box index (use r//3, c//3); forgetting to skip empty '.' cells.",
         example="A board with two 5s in the same row -> False; an otherwise-consistent board -> True."),
    dict(cat="dsa", title="First Missing Positive",
         answer="Find the smallest missing positive integer in O(n) time and O(1) space. Use the array itself as a hash: place each value v in [1,n] at index v-1 by swapping (cyclic sort). Then the first index whose value isn't index+1 gives the answer; if all match, it's n+1.",
         tags=["first-missing-positive","cyclic-sort","array","in-place","hard","dsa"],
         code='''# Smallest missing positive integer in O(n) time and O(1) space.
def first_missing_positive(nums):
    n = len(nums)
    for i in range(n):
        # place each value v in [1,n] at index v-1 by swapping
        while 1 <= nums[i] <= n and nums[nums[i] - 1] != nums[i]:
            target = nums[i] - 1
            nums[i], nums[target] = nums[target], nums[i]
    for i in range(n):
        if nums[i] != i + 1:
            return i + 1                  # first slot holding the wrong value
    return n + 1''',
         complexity="Time O(n), space O(1).",
         pitfalls="Infinite swap loop without the 'already placed' guard; ignoring out-of-range/negative values.",
         example="first_missing_positive([3,4,-1,1]) -> 2."),
    dict(cat="dsa", title="Jump Game (reachability)",
         answer="Decide whether you can reach the last index, where nums[i] is the max jump length from i. Greedy: track the FARTHEST index reachable so far while scanning; if the current index ever exceeds that reach you're stuck. If the loop finishes, the end is reachable.",
         tags=["jump-game","greedy","array","dsa"],
         code='''# Can you reach the last index? nums[i] = max jump length from i.
def can_jump(nums):
    farthest = 0
    for i in range(len(nums)):
        if i > farthest:
            return False                  # can't even reach index i
        farthest = max(farthest, i + nums[i])
    return True''',
         complexity="Time O(n), space O(1).",
         pitfalls="Overcomplicating with DP (greedy suffices); off-by-one on the reachability check.",
         example="can_jump([2,3,1,1,4]) -> True; can_jump([3,2,1,0,4]) -> False."),
    dict(cat="dsa", title="Group Anagrams",
         answer="Group words that are anagrams of one another. The key insight: two words are anagrams iff their sorted letters are identical, so use the sorted string (or a letter-count tuple) as a dictionary key and bucket words under it.",
         tags=["group-anagrams","hash-map","sorting","string","dsa"],
         code='''# Group words that are anagrams of each other.
from collections import defaultdict
def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        key = "".join(sorted(w))          # anagrams share a sorted signature
        groups[key].append(w)
    return list(groups.values())''',
         complexity="Time O(n * k log k) for k-length words, space O(n*k).",
         pitfalls="Using an unhashable list as the key (use a string or tuple); case/whitespace inconsistencies.",
         example="group_anagrams(['eat','tea','tan','ate','nat','bat']) -> [['eat','tea','ate'],['tan','nat'],['bat']]."),
    dict(cat="dsa", title="Sort Colors (Dutch National Flag)",
         answer="Sort an array of 0s, 1s, and 2s in a SINGLE pass, in place. Three pointers: low (boundary of 0s), mid (scanner), high (boundary of 2s). Swap 0s to the front and 2s to the back; leave 1s in the middle. When you swap a 2 back, don't advance mid (the swapped-in value is unexamined).",
         tags=["sort-colors","dutch-national-flag","three-pointers","in-place","dsa"],
         code='''# Sort an array of 0s, 1s, 2s in one pass (Dutch national flag).
def sort_colors(nums):
    low, mid, high = 0, 0, len(nums) - 1
    while mid <= high:
        if nums[mid] == 0:
            nums[low], nums[mid] = nums[mid], nums[low]   # 0 to the front
            low += 1; mid += 1
        elif nums[mid] == 1:
            mid += 1                                      # 1 stays put
        else:
            nums[mid], nums[high] = nums[high], nums[mid] # 2 to the back
            high -= 1                                     # re-examine this slot
    return nums''',
         complexity="Time O(n), space O(1).",
         pitfalls="Advancing mid after swapping a 2 back (skips an unchecked value); wrong loop bound (mid <= high).",
         example="sort_colors([2,0,2,1,1,0]) -> [0,0,1,1,2,2]."),
    dict(cat="dsa", title="Subarray Product Less Than K",
         answer="Count contiguous subarrays whose product is strictly less than k (positive numbers). Sliding window: expand right multiplying in nums[right]; while the product is >= k, shrink from the left by dividing it out. Every window ending at 'right' with the current left is valid, adding (right-left+1) each step.",
         tags=["subarray-product","sliding-window","array","dsa"],
         code='''# Count contiguous subarrays whose product is strictly less than k.
def num_subarray_product_less_than_k(nums, k):
    if k <= 1:
        return 0                          # no positive product is < 1
    product = 1
    left = 0
    count = 0
    for right in range(len(nums)):
        product *= nums[right]
        while product >= k:
            product //= nums[left]        # shrink until product < k
            left += 1
        count += right - left + 1         # all windows ending at 'right'
    return count''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not handling k <= 1 (no valid subarrays); counting windows wrong (it's right-left+1).",
         example="num_subarray_product_less_than_k([10,5,2,6], 100) -> 8."),
    dict(cat="dsa", title="Find Median from Data Stream (two heaps)",
         answer="Support add_num and find_median on a growing stream in O(log n) / O(1). Keep two heaps: a MAX-heap for the smaller half and a MIN-heap for the larger half, balanced so their sizes differ by at most one. The median is the top of the larger heap (odd count) or the average of both tops (even count).",
         tags=["median-stream","two-heaps","heap","design","dsa"],
         code='''# Maintain a running median of a stream using a max-heap and a min-heap.
import heapq
class MedianFinder:
    def __init__(self):
        self.low = []      # max-heap (negated) of the smaller half
        self.high = []     # min-heap of the larger half

    def add_num(self, num):
        heapq.heappush(self.low, -num)                        # add to low half
        heapq.heappush(self.high, -heapq.heappop(self.low))   # move its top over
        if len(self.high) > len(self.low):                    # rebalance
            heapq.heappush(self.low, -heapq.heappop(self.high))

    def find_median(self):
        if len(self.low) > len(self.high):
            return -self.low[0]                               # odd -> low's top
        return (-self.low[0] + self.high[0]) / 2              # even -> avg of tops''',
         complexity="add_num O(log n), find_median O(1); space O(n).",
         pitfalls="Letting the heaps get unbalanced; negating incorrectly for the max-heap.",
         example="After adding 1,2,3 the median is 2; after only 1,2 it is 1.5."),
    dict(cat="glossary", title="Exploration vs exploitation",
         answer="The core tension in sequential decision-making (bandits, RL, recommendations): EXPLOIT the option currently believed best to earn reward now, or EXPLORE uncertain options to gather information that may pay off later. Too much exploitation gets stuck on a local best; too much exploration wastes reward. Good policies (epsilon-greedy, UCB, Thompson sampling) balance the two.",
         tags=["exploration-exploitation","bandits","reinforcement-learning","recommendation"],
         example="A news recommender should EXPLOIT topics you like but occasionally EXPLORE new ones — otherwise it never discovers a category you'd love."),
    dict(cat="glossary", title="Epsilon-greedy",
         answer="The simplest exploration strategy for bandits/RL: with probability epsilon pick a RANDOM action (explore), otherwise pick the current best-estimated action (exploit). Easy and effective; epsilon is often DECAYED over time so you explore a lot early and exploit more as estimates firm up.",
         tags=["epsilon-greedy","bandits","exploration","reinforcement-learning"],
         example="With epsilon=0.1, an ad system shows its best ad 90% of the time and a random ad 10% of the time to keep learning newer ads' click rates."),
    dict(cat="glossary", title="Thompson sampling",
         answer="A Bayesian exploration strategy for bandits: keep a POSTERIOR distribution over each action's reward, SAMPLE one value from each posterior, and play the action with the highest sample. Uncertain actions have wide posteriors, so they occasionally win the draw — giving natural, self-tuning exploration that's often more efficient than epsilon-greedy.",
         tags=["thompson-sampling","bandits","bayesian","exploration"],
         example="For test arms, Thompson sampling draws from each arm's Beta posterior of click-rate and serves the winner — sending more traffic to promising arms while still probing others."),
    dict(cat="glossary", title="Position bias",
         answer="In ranked lists, users click higher-positioned items MORE regardless of true relevance, simply because they're seen first — so click logs conflate relevance with position. Ignoring it teaches a ranker that 'top = good', reinforcing itself. It's corrected with position-debiased models, inverse-propensity weighting by examination probability, or randomization.",
         tags=["position-bias","ranking","click-models","debiasing"],
         example="An item at rank 1 gets far more clicks than the same item at rank 5; a ranker trained on raw clicks wrongly concludes rank-1 items are more relevant unless you debias for position."),
    dict(cat="ml_system_design", title="Design an ETA Prediction system",
         answer="Predict the estimated time of arrival for a trip/delivery. (1) CLARIFY & SCALE: accurate real-time ETA for routing/pricing/UX; millions of requests, low latency, live traffic. (2) DATA & LABELS: historical trips with ACTUAL durations (the label), GPS traces, timestamps. (3) FEATURES: route/distance, road segments and their live speeds, time of day / day of week, weather, historical segment speeds, origin/destination. (4) MODEL: a segment-based approach (sum predicted per-segment times) or an end-to-end gradient-boosted/deep model on route + context; predict QUANTILES for uncertainty (give a range). (5) EVAL: MAE/MAPE on held-out FUTURE trips plus uncertainty calibration; slice by trip length and region. (6) SERVING/MONITORING/AB: real-time features from a streaming traffic pipeline, cache segment speeds, recompute on reroutes, A/B on ETA error and downstream cancellations, monitor drift from construction/events.",
         tags=["eta-prediction","time-series","routing","regression","ml-system-design"],
         example="For a ride request, the model sums predicted times over the route's segments using live speeds + time-of-day, returning '14 min' with a confidence band, later scored against the actual duration."),
    dict(cat="ml_system_design", title="Design an Anomaly Detection service",
         answer="Detect unusual events/metrics (fraud, outages, sensor faults) in streaming or batch data. (1) CLARIFY & SCALE: flag anomalies with a low false-alarm rate, often UNSUPERVISED (few labels), real-time; define 'anomaly' per use case. (2) DATA & LABELS: mostly-normal historical data, few/no labels, maybe some confirmed incidents. (3) FEATURES: the metric time series and context (seasonality, related signals); for multivariate, the full feature vector. (4) MODEL: statistical baselines (z-score, seasonal decomposition, EWMA control limits), unsupervised models (isolation forest, autoencoder reconstruction error, one-class SVM), or forecast-RESIDUAL methods (predict expected value, flag big residuals). (5) EVAL: precision/recall on known incidents and alert volume vs miss rate; tune thresholds by alert-fatigue cost. (6) SERVING/MONITORING/AB: streaming scoring with per-metric thresholds, dedup/aggregate alerts, human feedback to cut false positives, adapt to seasonality/drift, and attach explanations.",
         tags=["anomaly-detection","unsupervised","monitoring","time-series","ml-system-design"],
         example="A service watches p99 latency per endpoint; a seasonal forecast predicts the expected p99, and when the actual exceeds the band by 3x an alert fires to on-call with the contributing metric."),
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
