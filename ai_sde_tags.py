"""Six-dimension interview tags for every entry in ai_sde_bank.py.

Tagged for a final-year CSE (AI/DS) student preparing for NEW-GRAD AI/SDE
interviews.  Purely additive: nothing in ENTRIES is reworded, reordered,
renumbered or dropped - `apply(entries)` attaches the tags by exact title.

CONTROLLED VOCABULARY.  Exactly one value per dimension per entry, no blanks,
and no value outside these lists (enforced by tests/test_smoke.py):

    TOPIC     DSA | Core-CS | Python | Math-Stats | Classical-ML |
              Deep-Learning | NLP-LLM | System-Design | MLOps | Behavioral
    LEVEL     Easy | Medium | Hard            (calibrated to the NEW-GRAD bar)
    PRIORITY  Must-Know | Common | Rare       (real interview frequency, NOT
                                               how interesting the topic is)
    FORMAT    Coding | Conceptual | Math | Design | Debug | Behavioral
    STAGE     Screen | Onsite | Either
    TIME      Quick | Medium | Deep

FLAG is optional and holds a one-line reason whenever a tag is a best guess
rather than a clean fit.  Ambiguous entries are flagged, never silently
force-fitted.

STRUCTURAL FLAG, recorded once here rather than on 353 rows: the `glossary`
category holds TERMS TO KNOW, not questions anybody asks out loud ("QUIC",
"Entropy").  FORMAT/STAGE/TIME are therefore a mild force-fit for that whole
category; they default to Conceptual / Either / Quick unless the term is
genuinely heavier.  TOPIC, LEVEL and PRIORITY are still judged per entry.

NOTE ON PRIORITY vs THE BANK'S OWN priority FIELD.  The bank already carries a
computed P0-P3 stack rank, but that score rises as an entry gains worked
examples - so it partly measures how much content has been WRITTEN, not how
often the topic is ASKED.  Where the two disagree, this file is the judgment
about interview frequency and the P0-P3 rank is the judgment about study
order.  The mismatches are deliberately visible.
"""

TOPICS = ("DSA", "Core-CS", "Python", "Math-Stats", "Classical-ML",
          "Deep-Learning", "NLP-LLM", "System-Design", "MLOps", "Behavioral")
LEVELS = ("Easy", "Medium", "Hard")
PRIORITIES = ("Must-Know", "Common", "Rare")
FORMATS = ("Coding", "Conceptual", "Math", "Design", "Debug", "Behavioral")
STAGES = ("Screen", "Onsite", "Either")
TIMES = ("Quick", "Medium", "Deep")

DIMENSIONS = ("topic", "level", "priority", "format", "stage", "time")
_VOCAB = {"topic": TOPICS, "level": LEVELS, "priority": PRIORITIES,
          "format": FORMATS, "stage": STAGES, "time": TIMES}

# Categories whose FORMAT/STAGE/TIME carry the structural flag described above.
_STRUCTURAL_FLAG_CATS = ("glossary",)
_STRUCTURAL_FLAG = ("glossary term rather than a spoken question - "
                    "FORMAT/STAGE/TIME are a category-level default")


def T(topic, level, priority, fmt, stage, time, flag=""):
    """One tag row.  Positional order matches the six columns."""
    return {"topic": topic, "level": level, "priority": priority,
            "format": fmt, "stage": stage, "time": time, "flag": flag}


# ═══════════════════════════════════════════════════════════════════════════
# TAGS: exact entry title -> T(...)
# ═══════════════════════════════════════════════════════════════════════════

TAGS = {}


def apply(entries):
    """Attach tags to entries in place.  Returns (tagged, untagged) counts."""
    tagged = 0
    for e in entries:
        row = TAGS.get(e["title"])
        if row is None:
            continue
        e["tag_topic"] = row["topic"]
        e["tag_level"] = row["level"]
        e["tag_priority"] = row["priority"]
        e["tag_format"] = row["format"]
        e["tag_stage"] = row["stage"]
        e["tag_time"] = row["time"]
        flag = row["flag"]
        if not flag and e.get("cat") in _STRUCTURAL_FLAG_CATS:
            flag = _STRUCTURAL_FLAG
        e["tag_flag"] = flag
        tagged += 1
    return tagged, len(entries) - tagged


def validate(entries=None):
    """Raise on any vocabulary violation or any key that matches no entry.

    A mis-keyed title silently drops its tags with no error, which has bitten
    this bank before with the example dicts - so it is an explicit check.
    """
    problems = []
    for title, row in TAGS.items():
        for dim in DIMENSIONS:
            value = row.get(dim)
            if value not in _VOCAB[dim]:
                problems.append("%r: %s=%r not in vocabulary" % (title, dim, value))
    if entries is not None:
        known = {e["title"] for e in entries}
        for title in TAGS:
            if title not in known:
                problems.append("%r: matches no entry title" % title)
    if problems:
        raise ValueError("ai_sde_tags problems:\n  " + "\n  ".join(problems))
    return True


def counts(entries):
    """Per-dimension counts over the TAGGED entries, for the calibration check."""
    from collections import Counter
    out = {}
    for dim in DIMENSIONS:
        key = "tag_" + dim
        out[dim] = Counter(e[key] for e in entries if key in e)
    return out

# ── DSA: P0 band ───────────────────────────────────────────────────────────
# FORMAT is Coding throughout except the PATTERN entries (flagged), which
# teach a technique rather than pose a problem. STAGE leans Screen for the
# easy warm-ups, Onsite for anything needing a real derivation.

_PATTERN = "pattern/teaching entry, not a problem anyone poses verbatim"

TAGS.update({
 "Balanced Binary Tree":                    T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Climbing Stairs":                         T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Diameter of a Binary Tree":               T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Flood Fill":                              T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Invert a Binary Tree":                    T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Maximum Depth of Binary Tree":            T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Merge Two Sorted Lists":                  T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Min Cost Climbing Stairs (DP)":           T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Path Sum (root-to-leaf boolean)":         T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Subtree of Another Tree":                 T("DSA","Easy","Common","Coding","Screen","Quick"),
 "3Sum":                                    T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Binary Tree Right Side View":             T("DSA","Medium","Common","Coding","Either","Medium"),
 "Clone Graph (DFS)":                       T("DSA","Medium","Common","Coding","Either","Medium"),
 "Coin Change (fewest coins)":              T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Decode Ways (DP)":                        T("DSA","Medium","Common","Coding","Either","Medium"),
 "Generate Parentheses (backtracking)":     T("DSA","Medium","Common","Coding","Either","Medium"),
 "Graphs — BFS, DFS, and when to use each": T("DSA","Medium","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Linked Lists — reversal & fast/slow pointers": T("DSA","Medium","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Longest Increasing Subsequence (patience + binary search)": T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Longest Substring Without Repeating Characters": T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Lowest Common Ancestor of a Binary Tree": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Maximum Product Subarray":                T("DSA","Medium","Common","Coding","Either","Medium"),
 "Merge Intervals":                         T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Number of Connected Components":          T("DSA","Medium","Common","Coding","Either","Medium"),
 "Number of Islands (DFS flood-fill)":      T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Pacific Atlantic Water Flow":             T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Partition Equal Subset Sum":              T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Permutations (backtracking)":             T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Remove Nth Node From End of List":        T("DSA","Medium","Common","Coding","Screen","Quick"),
 "Topological Sort (Kahn's algorithm)":     T("DSA","Medium","Common","Coding","Either","Medium"),
 "Trees — BFS vs DFS":                      T("DSA","Medium","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Word Break (DP)":                         T("DSA","Medium","Common","Coding","Either","Medium"),
 "Word Search (backtracking)":              T("DSA","Medium","Common","Coding","Either","Medium"),
 "Middle of the Linked List":               T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Move Zeroes":                             T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Palindrome Linked List":                  T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Reverse Linked List":                     T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Squares of a Sorted Array":               T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Backtracking — subsets, permutations, combinations": T("DSA","Hard","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Binary Tree Maximum Path Sum":            T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Dijkstra's Shortest Path (min-heap)":     T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Dynamic Programming — the 4-question method": T("DSA","Hard","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Word Ladder (shortest transformation, BFS)": T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Binary Search — including 'search on the answer'": T("DSA","Medium","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Binary Tree Level Order Traversal":       T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Combination Sum (reusable candidates)":   T("DSA","Medium","Common","Coding","Either","Medium"),
 "Container With Most Water":               T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Course Schedule (topological sort)":      T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Design an LRU Cache":                     T("DSA","Medium","Must-Know","Coding","Onsite","Deep",
                                              "often called a design question; it is implement-a-class, so FORMAT is Coding"),
 "Find First and Last Position (sorted array)": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Find Minimum in Rotated Sorted Array":    T("DSA","Medium","Common","Coding","Either","Medium"),
 "Find Peak Element (binary search)":       T("DSA","Medium","Common","Coding","Either","Medium"),
 "Find the Duplicate Number (Floyd's cycle)": T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Heap / Top-K — when 'K largest/most frequent' appears": T("DSA","Medium","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Intervals — merge, insert, overlap":      T("DSA","Medium","Common","Conceptual","Either","Medium", _PATTERN),
 "K Closest Points to Origin (heap)":       T("DSA","Medium","Common","Coding","Either","Medium"),
 "Kth Largest Element":                     T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Letter Combinations of a Phone Number":   T("DSA","Medium","Common","Coding","Either","Medium"),
 "Longest Palindromic Substring (expand around center)": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Longest Repeating Character Replacement": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Meeting Rooms II (minimum rooms)":        T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Non-overlapping Intervals (min removals)": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Rotting Oranges (multi-source BFS)":      T("DSA","Medium","Common","Coding","Either","Medium"),
 "Search a 2D Matrix":                      T("DSA","Medium","Common","Coding","Either","Medium"),
 "Search in Rotated Sorted Array":          T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Sliding Window — recognize & apply":      T("DSA","Medium","Must-Know","Conceptual","Either","Deep", _PATTERN),
 "Subarray Sum Equals K":                   T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Subsets (power set)":                     T("DSA","Medium","Common","Coding","Either","Medium"),
 "Top K Frequent Elements":                 T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Two Pointers — recognize & apply":        T("DSA","Medium","Must-Know","Conceptual","Either","Medium", _PATTERN),
 "Union-Find / Disjoint Set Union (DSU)":   T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Find Median from Data Stream (two heaps)": T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Merge k Sorted Lists (min-heap)":         T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Minimum Window Substring (sliding window)": T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Trapping Rain Water":                     T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Union-Find (Disjoint Set Union)":         T("DSA","Hard","Common","Coding","Onsite","Deep",
                                              "near-duplicate of the DSU entry above; kept as-is per the no-drop rule"),
})

# ── DSA: P1 band, first slice ──────────────────────────────────────────────
TAGS.update({
 "Insert Interval":                         T("DSA","Medium","Common","Coding","Either","Medium"),
 "Trie (Prefix Tree)":                      T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Assign Cookies":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Average of Levels in Binary Tree":        T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Binary Tree Tilt":                        T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Pairs Whose Sum is Less than Target": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "DI String Match":                         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Meeting Rooms (can attend all)":          T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Merge Similar Items":                     T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Merge Two Binary Trees":                  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Depth of Binary Tree":            T("DSA","Easy","Common","Coding","Screen","Quick"),
 "N-th Tribonacci Number":                  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Rank Transform of an Array":              T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sum of Left Leaves":                      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Valid Palindrome II (delete at most one)": T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Symmetric Tree":                          T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Best Time to Buy and Sell Stock with Cooldown": T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Binary Tree Zigzag Level-Order Traversal": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Bipartite Graph Check (BFS 2-coloring)":  T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Boats to Save People":                    T("DSA","Medium","Rare","Coding","Either","Quick"),
 "Count Good Nodes in a Binary Tree":       T("DSA","Medium","Rare","Coding","Either","Quick"),
 "Divide Players Into Teams of Equal Skill": T("DSA","Medium","Rare","Coding","Screen","Quick"),
 "Find Right Interval":                     T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "House Robber II (circular street)":       T("DSA","Medium","Common","Coding","Either","Medium"),
})

# ── DSA: P1 band, second slice ─────────────────────────────────────────────
TAGS.update({
 "Integer Break (DP)":                      T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Jump Game II (fewest jumps)":             T("DSA","Medium","Common","Coding","Either","Medium"),
 "Longest Arithmetic Subsequence":          T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Longest Palindromic Subsequence":         T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Maximal Square (DP)":                     T("DSA","Medium","Common","Coding","Onsite","Medium"),
 "Maximum Length of Pair Chain":            T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Minimum Number of Arrows to Burst Balloons": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Minimum Number of Coins for Fruits":      T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Minimum Path Sum":                        T("DSA","Medium","Common","Coding","Either","Medium"),
 "Network Delay Time (Dijkstra application)": T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Palindrome Partitioning (backtracking)":  T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Path Sum II (all root-to-leaf paths)":    T("DSA","Medium","Common","Coding","Either","Medium"),
 "Path Sum III (prefix sum)":               T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Perfect Squares (DP)":                    T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Reorganize String (greedy heap)":         T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Sum Root to Leaf Numbers":                T("DSA","Medium","Rare","Coding","Either","Quick"),
 "Triangle (Minimum Path Sum)":             T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Unique Paths II (grid with obstacles)":   T("DSA","Medium","Common","Coding","Either","Medium"),
 "Wiggle Subsequence (greedy)":             T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Arranging Coins":                         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Backspace String Compare":                T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Check if Two Strings Are Almost Equivalent": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Closest Binary Search Tree Value":        T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Number of Pairs With Absolute Difference K": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Degree of an Array":                      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find Center of Star Graph":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find Lucky Integer in an Array":          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find Pivot Index":                        T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Find Words That Can Be Formed by Characters": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find the Highest Altitude":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "First Unique Character in a String":      T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Flipping an Image":                       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "How Many Numbers Are Smaller Than the Current": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Intersection of Two Arrays II":           T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Is Subsequence":                          T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Isomorphic Strings":                      T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Kth Distinct String in an Array":         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Kth Largest Element in a Stream":         T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Kth Missing Positive Number":             T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Last Stone Weight (max-heap)":            T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Left and Right Sum Difference":           T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Maximum Score After Splitting a String":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Common Value":                    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Recolors to Get K Consecutive Black Blocks": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Points That Intersect With Cars":         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Ransom Note":                             T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Remove Duplicates from Sorted List":      T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Remove Linked List Elements":             T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Reverse String (in place)":               T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Running Sum of 1d Array":                 T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Search Insert Position":                  T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Search in a Binary Search Tree":          T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Sort Array By Parity":                    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sqrt(x) — integer square root (binary search)": T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Sum of Unique Elements":                  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Summary Ranges":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Two Sum IV - Input is a BST":             T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Valid Mountain Array":                    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Valid Perfect Square":                    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Word Pattern":                            T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Bellman-Ford (shortest path with negative edges)": T("DSA","Hard","Rare","Coding","Onsite","Deep"),
 "Prim's Minimum Spanning Tree":            T("DSA","Hard","Rare","Coding","Onsite","Deep"),
 "01 Matrix (distance to nearest zero)":    T("DSA","Medium","Common","Coding","Either","Medium"),
 "Binary Search Lower Bound (bisect_left)": T("DSA","Medium","Common","Conceptual","Either","Medium", _PATTERN),
 "Car Pooling":                             T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Cheapest Flights Within K Stops (Bellman-Ford)": T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Corporate Flight Bookings":               T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Kth Largest Element in an Array":         T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Number of Provinces":                     T("DSA","Medium","Common","Coding","Either","Medium"),
 "Odd Even Linked List":                    T("DSA","Medium","Rare","Coding","Either","Quick"),
 "Pairs of Songs Divisible by 60":          T("DSA","Medium","Rare","Coding","Screen","Quick"),
 "Partition Labels (greedy)":               T("DSA","Medium","Common","Coding","Either","Medium"),
 "Permutation in String":                   T("DSA","Medium","Common","Coding","Either","Medium"),
 "Redundant Connection (Union-Find)":       T("DSA","Medium","Common","Coding","Onsite","Medium"),
 "Rotate List":                             T("DSA","Medium","Rare","Coding","Either","Quick"),
 "Shortest Path in Binary Matrix (8-directional BFS)": T("DSA","Medium","Common","Coding","Either","Medium"),
 "String Compression (in place)":           T("DSA","Medium","Common","Coding","Either","Medium"),
 "Subarray Product Less Than K":            T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Subsets II (with duplicates)":            T("DSA","Medium","Common","Coding","Either","Medium"),
 "Surrounded Regions":                      T("DSA","Medium","Common","Coding","Onsite","Medium"),
 "Swap Nodes in Pairs":                     T("DSA","Medium","Common","Coding","Either","Quick"),
 "Best Time to Buy and Sell Stock II (greedy)": T("DSA","Medium","Common","Coding","Screen","Quick"),
 "Capacity to Ship Packages Within D Days": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Construct Binary Tree from Preorder and Inorder": T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Edit Distance (Levenshtein)":             T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "House Robber":                            T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Jump Game":                               T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Kth Smallest Element in a BST":           T("DSA","Medium","Common","Coding","Either","Medium"),
 "Longest Common Subsequence":              T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Maximum Subarray (Kadane's algorithm)":   T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Merge Sort":                              T("DSA","Medium","Common","Coding","Either","Medium"),
 "Quick Sort":                              T("DSA","Medium","Common","Coding","Either","Medium"),
 "Task Scheduler (cooldown)":               T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Unique Paths (grid DP)":                  T("DSA","Medium","Common","Coding","Either","Medium"),
 "Validate Binary Search Tree":             T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Kruskal's Minimum Spanning Tree":         T("DSA","Hard","Rare","Coding","Onsite","Deep"),
 "Hashing — the 'have I seen this?' pattern": T("DSA","Easy","Must-Know","Conceptual","Either","Medium", _PATTERN),
 "Linked List Cycle":                       T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Majority Element (Boyer-Moore voting)":   T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Missing Number":                          T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Number of 1 Bits (popcount)":             T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Single Number (XOR)":                     T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Valid Parentheses":                       T("DSA","Easy","Must-Know","Coding","Screen","Quick"),
 "Asteroid Collision (stack)":              T("DSA","Medium","Common","Coding","Either","Medium"),
 "Count Primes (Sieve of Eratosthenes)":    T("DSA","Medium","Common","Coding","Either","Medium"),
 "Daily Temperatures (monotonic stack)":    T("DSA","Medium","Common","Coding","Either","Medium"),
 "Decode String (stack)":                   T("DSA","Medium","Common","Coding","Either","Medium"),
 "Design a Min Stack":                      T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Evaluate Reverse Polish Notation":        T("DSA","Medium","Common","Coding","Either","Medium"),
 "Group Anagrams":                          T("DSA","Medium","Must-Know","Coding","Either","Medium"),
})

# ── DSA: P1 tail + P2 band, first slice ────────────────────────────────────
TAGS.update({
 "Koko Eating Bananas (binary search on the answer)": T("DSA","Medium","Common","Coding","Either","Medium"),
 "Longest Consecutive Sequence":            T("DSA","Medium","Common","Coding","Either","Medium"),
 "Next Greater Element (monotonic stack)":  T("DSA","Medium","Common","Coding","Either","Medium"),
 "Pow(x, n) — fast exponentiation":         T("DSA","Medium","Common","Coding","Either","Medium"),
 "Product of Array Except Self":            T("DSA","Medium","Must-Know","Coding","Either","Medium"),
 "Quickselect (kth largest)":               T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Rotate Image (90 degrees, in place)":     T("DSA","Medium","Common","Coding","Either","Medium"),
 "Set Matrix Zeroes (O(1) space)":          T("DSA","Medium","Common","Coding","Either","Medium"),
 "Sort Colors (Dutch National Flag)":       T("DSA","Medium","Common","Coding","Either","Medium"),
 "Spiral Matrix":                           T("DSA","Medium","Common","Coding","Either","Medium"),
 "String to Integer (atoi)":                T("DSA","Medium","Rare","Coding","Either","Medium",
                                              "a specification exercise rather than an algorithm; asked more in C/embedded loops"),
 "Valid Sudoku":                            T("DSA","Medium","Common","Coding","Either","Medium"),
 "Array Partition I":                       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Largest Perimeter Triangle":              T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Maximum Product Difference Between Two Pairs": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Maximum Units on a Truck (greedy)":       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Number of Moves to Seat Everyone": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Sum of Four Digit Number After Splitting Digits": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Same Tree":                               T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Split a Number into Two Parts with Minimum Sum": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "First Missing Positive":                  T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Largest Rectangle in Histogram (monotonic stack)": T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Maximum Number of Coins You Can Get":     T("DSA","Medium","Rare","Coding","Screen","Quick"),
 "Maximum Product of Three Numbers":        T("DSA","Medium","Rare","Coding","Screen","Quick"),
 "Minimum Moves to Equal Array Elements II": T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Queue Reconstruction by Height":          T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Two City Scheduling (greedy)":            T("DSA","Medium","Common","Coding","Either","Medium"),
 "Can Make Arithmetic Progression":         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Can Place Flowers (greedy)":              T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Convert Sorted Array to BST":             T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Count Tested Devices After Test Operations": T("DSA","Easy","Rare","Coding","Screen","Quick",
                                              "low-profile recent LC easy; drill volume rather than interview likelihood"),
 "Counting Sort":                           T("DSA","Easy","Common","Coding","Either","Medium"),
 "Distribute Candies":                      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Distribute Money to Maximum Children":    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find Target Indices After Sorting Array": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Height Checker":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Kids With the Greatest Number of Candies": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Largest Odd Number in String":            T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Lemonade Change (greedy)":                T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Maximum Ascending Subarray Sum":          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Maximum Product of Two Elements in an Array": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimize String Length (keep distinct characters)": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Absolute Difference":             T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Cost to Move Chips":              T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Operations to Make the Array Increasing": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Range Sum of BST":                        T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Sort Array by Increasing Frequency":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sort Integers by Number of 1 Bits":       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sort the People":                         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Split a String in Balanced Strings":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Water Bottles":                           T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Coin Change II (count ways)":             T("DSA","Medium","Common","Coding","Onsite","Deep"),
 "Convert BST to Greater Tree":             T("DSA","Medium","Rare","Coding","Either","Quick"),
 "Flatten Binary Tree to Linked List":      T("DSA","Medium","Common","Coding","Onsite","Medium"),
 "Gas Station (greedy circuit)":            T("DSA","Medium","Common","Coding","Onsite","Medium"),
 "Largest Number (custom sort)":            T("DSA","Medium","Common","Coding","Either","Medium"),
 "Lowest Common Ancestor of a BST":         T("DSA","Medium","Common","Coding","Screen","Quick"),
 "Minimum Add to Make Parentheses Valid":   T("DSA","Medium","Rare","Coding","Screen","Quick"),
 "Minimum Cost to Make Array Non-decreasing (increasing via increments)": T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Minimum Deletions to Make Character Frequencies Unique": T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Minimum Operations to Make Array Equal to Target": T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Non-decreasing Array With One Modification": T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Remove Duplicate Letters":                T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Sort Characters By Frequency":            T("DSA","Medium","Common","Coding","Either","Quick"),
 "Count and Say":                           T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Majority Element II (> n/3)":             T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Maximum Gap (bucket sort)":               T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Next Greater Element II (circular)":      T("DSA","Medium","Common","Coding","Either","Medium"),
 "Number of Steps to Reduce a Number in Binary to One": T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Range Bitwise AND":                       T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Reverse Integer":                         T("DSA","Medium","Common","Coding","Screen","Quick"),
 "Reverse Words in a String":               T("DSA","Medium","Common","Coding","Screen","Quick"),
 "Rotate Array by k (reversal trick)":      T("DSA","Medium","Common","Coding","Either","Medium"),
 "Single Number II (appears once among triples)": T("DSA","Medium","Rare","Coding","Onsite","Deep"),
 "Single Number III (two uniques)":         T("DSA","Medium","Rare","Coding","Onsite","Medium"),
 "Spiral Matrix II (generate)":             T("DSA","Medium","Rare","Coding","Either","Medium"),
 "Basic Calculator (with parentheses)":     T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Sliding Window Maximum (deque)":          T("DSA","Hard","Common","Coding","Onsite","Deep"),
 "Add Binary":                              T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Add Digits (digital root)":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Add Strings":                             T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Add to Array-Form of Integer":            T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Alternating Digit Sum":                   T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Apply Operations to an Array":            T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Average Salary Excluding the Minimum and Maximum": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Base 7 Conversion":                       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Check If It Is a Straight Line":          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Check if Array Is Sorted and Rotated":    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Elements With Strictly Smaller and Greater Elements": T("DSA","Easy","Rare","Coding","Screen","Quick"),
})

# ── DSA: P2 tail (easy warm-ups / LC-easy drill volume) ────────────────────
# Almost all Rare on purpose: these are typing-speed and syntax drills, not
# questions a new-grad loop actually poses. The handful that DO get asked as
# openers or as classic implement-this problems are marked Common.
TAGS.update({
 "Count Good Pairs":                        T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Items Matching a Rule":             T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Negatives in a Sorted Matrix":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Odd Numbers in an Interval Range":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count Symmetric Integers":                T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Count the Number of Consistent Strings":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Day of the Year":                         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Decode XORed Array":                      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Decompress Run-Length Encoded List":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Defanging an IP Address":                 T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Design HashMap":                          T("DSA","Easy","Common","Coding","Either","Medium",
                                              "LC labels it Easy; as an implement-a-structure question it plays Medium"),
 "Detect Capital":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Excel Sheet Column Number":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find All Numbers Disappeared in an Array": T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Find First Palindromic String in the Array": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find Words Containing Character":         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find the Difference (XOR)":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Find the Difference of Two Arrays":       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Fizz Buzz":                               T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Greatest Common Divisor of Strings":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Hamming Distance":                        T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Happy Number":                            T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Implement Stack using Queues":            T("DSA","Easy","Common","Coding","Either","Quick"),
 "Implement a Queue using two Stacks":      T("DSA","Easy","Must-Know","Coding","Either","Quick"),
 "Implement strStr() (indexOf)":            T("DSA","Easy","Common","Coding","Either","Medium"),
 "Jewels and Stones":                       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Longest Common Prefix":                   T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Lucky Numbers in a Matrix":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Matrix Diagonal Sum":                     T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Matrix Reshape":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Maximum Population Year":                 T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Absolute Difference in BST":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Bit Flips to Convert Number":     T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Right Shifts to Sort the Array":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Minimum Time Visiting All Points":        T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Monotonic Array":                         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Number Complement":                       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Number of Arithmetic Triplets":           T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Number of Employees Who Met the Target":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Number of Senior Citizens":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Number of Steps to Reduce a Number to Zero": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Number to Excel Column Title":            T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Palindrome Number":                       T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Perfect Number":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Plus One":                                T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Power of Three":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Power of Two":                            T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Relative Sort Array":                     T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Remove Trailing Zeros From a String":     T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Repeated Substring Pattern":              T("DSA","Easy","Rare","Coding","Either","Medium"),
 "Replace Elements with Greatest Element on Right Side": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Reverse Bits":                            T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Richest Customer Wealth":                 T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Robot Return to Origin":                  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Roman to Integer":                        T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Self Dividing Numbers":                   T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Separate the Digits in an Array":         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Set Mismatch":                            T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Shuffle String":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Smallest Even Multiple":                  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sorting the Sentence":                    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Subtract the Product and Sum of Digits":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sum of All Odd Length Subarrays":         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sum of Digits in Base 10 After Convert":  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sum of Squares of Special Elements":      T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Sum of Values at Indices With K Set Bits": T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Third Maximum Number":                    T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Three Consecutive Odds":                  T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Three Divisors":                          T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Toeplitz Matrix":                         T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Transpose Matrix":                        T("DSA","Easy","Common","Coding","Screen","Quick"),
 "Truncate Sentence":                       T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Ugly Number":                             T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Unique Morse Code Words":                 T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "Unique Number of Occurrences":            T("DSA","Easy","Rare","Coding","Screen","Quick"),
 "XOR Operation in an Array":               T("DSA","Easy","Rare","Coding","Screen","Quick"),
})
