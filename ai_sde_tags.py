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

SUBTOPIC is a seventh, additive column with its own per-topic vocabulary - see
SUBTOPICS below.  It exists because "DSA" alone is useless for revision when
375 entries carry it.

FLAG is optional and holds a one-line reason whenever a tag is a best guess
rather than a clean fit.  Ambiguous entries are flagged, never silently
force-fitted.

GLOSSARY ENTRIES ARE TAGGED INDIVIDUALLY, not by a category-wide default.  An
earlier draft defaulted the whole `glossary` category to Conceptual/Either/
Quick behind one structural flag; that was a cop-out, because the category
mixes things a real interviewer genuinely asks ("What is overfitting?",
"Explain a deadlock") with pure reference trivia nobody asks out loud
("QUIC", "ETag").  Those two kinds deserve opposite PRIORITY and different
TIME, so every glossary row is judged on its own.

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

# ── SUBTOPIC: a SEVENTH, additive column ───────────────────────────────────
# The six dimensions above keep their fixed vocabulary exactly as specified -
# nothing was invented inside them.  But "DSA" alone is far too coarse to
# revise from when 375 of 1,120 entries carry it, so SUBTOPIC is added as an
# extra column with its own controlled list, scoped PER TOPIC: a subtopic is
# only legal for the topic it belongs to, and that pairing is enforced by
# validate().  The DSA list deliberately mirrors the way the material is
# actually studied (the NeetCode-style grouping) so a filter on the study page
# maps onto a revision session.
SUBTOPICS = {
    "DSA": ("Arrays-Hashing", "Two-Pointers", "Sliding-Window", "Stack",
            "Binary-Search", "Linked-List", "Trees", "Tries", "Heap",
            "Backtracking", "Graphs", "DP", "Greedy", "Intervals",
            "Math-Bits", "Matrix", "Sorting", "Design"),
    "Core-CS": ("OS", "DBMS", "Networking", "OOP", "Systems"),
    "Python": ("Language", "Stdlib", "Performance"),
    "Math-Stats": ("Probability", "Statistics", "Linear-Algebra", "Calculus",
                   "Information-Theory"),
    "Classical-ML": ("Supervised", "Unsupervised", "Evaluation",
                     "Feature-Engineering", "Trees-Ensembles", "Theory"),
    "Deep-Learning": ("Architectures", "Training", "CNN", "Sequence-Models",
                      "Optimization", "Regularization"),
    "NLP-LLM": ("Transformers", "RAG", "Prompting", "Fine-Tuning", "Agents",
                "Evaluation", "Inference", "Embeddings"),
    "System-Design": ("Fundamentals", "Scalability", "Storage",
                      "ML-System-Design"),
    "MLOps": ("Deployment", "Monitoring", "Pipelines", "Infra"),
    "Behavioral": ("Amazon-LP", "Googleyness", "Story-Bank", "Process"),
}


def T(topic, level, priority, fmt, stage, time, flag=""):
    """One tag row.  Positional order matches the six columns."""
    return {"topic": topic, "level": level, "priority": priority,
            "format": fmt, "stage": stage, "time": time, "flag": flag}


# ═══════════════════════════════════════════════════════════════════════════
# TAGS: exact entry title -> T(...)
# ═══════════════════════════════════════════════════════════════════════════

TAGS = {}

#: title -> subtopic.  Kept separate from TAGS so the seventh column could be
#: added without rewriting rows that were already judged on the first six.
SUB = {}


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
        e["tag_subtopic"] = SUB.get(e["title"], "")
        e["tag_flag"] = row["flag"]
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
        # SUBTOPIC is scoped per topic: a DSA subtopic on an NLP-LLM row is a
        # mis-tag, not a free-text note, so the pairing is checked too.
        sub = SUB.get(title)
        if sub is not None:
            legal = SUBTOPICS.get(row.get("topic"), ())
            if sub not in legal:
                problems.append("%r: subtopic=%r is not legal for topic=%r"
                                % (title, sub, row.get("topic")))
    for title in SUB:
        if title not in TAGS:
            problems.append("%r: has a subtopic but no tag row" % title)
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


# ═══════════════════════════════════════════════════════════════════════════
# SUBTOPIC assignments, grouped by subtopic so the taxonomy is reviewable at
# a glance.  Where a problem legitimately sits in two buckets it is filed
# under the one you would REVISE it from, not the one that technically also
# applies - Number of Islands is Graphs, not Matrix; Two Sum-style counting
# is Arrays-Hashing, not Two-Pointers.
# ═══════════════════════════════════════════════════════════════════════════

def _sub(name, titles):
    for _t in titles:
        SUB[_t] = name


_sub("Arrays-Hashing", [
 "Group Anagrams", "Longest Consecutive Sequence",
 "Product of Array Except Self", "Subarray Sum Equals K", "Top K Frequent Elements",
 "Hashing — the 'have I seen this?' pattern", "First Unique Character in a String",
 "Intersection of Two Arrays II", "Isomorphic Strings", "Ransom Note", "Word Pattern",
 "Find Pivot Index", "Running Sum of 1d Array", "Find the Highest Altitude",
 "Left and Right Sum Difference", "Degree of an Array", "Find Lucky Integer in an Array",
 "Kth Distinct String in an Array", "Sum of Unique Elements", "Unique Number of Occurrences",
 "Find Words That Can Be Formed by Characters", "Count the Number of Consistent Strings",
 "Count Good Pairs", "Count Number of Pairs With Absolute Difference K",
 "Count Pairs Whose Sum is Less than Target", "Find All Numbers Disappeared in an Array",
 "Set Mismatch", "Third Maximum Number", "Minimum Common Value", "Jewels and Stones",
 "Find the Difference of Two Arrays", "Shuffle String", "Richest Customer Wealth",
 "Count Items Matching a Rule", "Number of Employees Who Met the Target",
 "Number of Senior Citizens", "Maximum Population Year", "Corporate Flight Bookings",
 "Points That Intersect With Cars", "Sum of All Odd Length Subarrays",
 "Apply Operations to an Array", "Decode XORed Array", "Decompress Run-Length Encoded List",
 "Separate the Digits in an Array", "Find Words Containing Character",
 "Find First Palindromic String in the Array", "Truncate Sentence", "Sorting the Sentence",
 "Defanging an IP Address", "Detect Capital", "Longest Common Prefix",
 "Repeated Substring Pattern", "Greatest Common Divisor of Strings", "Unique Morse Code Words",
 "Maximum Score After Splitting a String", "Minimize String Length (keep distinct characters)",
 "Largest Odd Number in String", "Remove Trailing Zeros From a String",
 "Check if Two Strings Are Almost Equivalent", "Implement strStr() (indexOf)",
 "Count Elements With Strictly Smaller and Greater Elements", "Robot Return to Origin",
 "Average Salary Excluding the Minimum and Maximum", "Replace Elements with Greatest Element on Right Side",
 "Monotonic Array", "Check if Array Is Sorted and Rotated", "Maximum Ascending Subarray Sum",
 "Minimum Right Shifts to Sort the Array", "Rotate Array by k (reversal trick)",
 "Reverse Words in a String", "Reverse String (in place)", "String Compression (in place)",
 "Count and Say", "Number of Arithmetic Triplets", "Can Make Arithmetic Progression",
 "Check If It Is a Straight Line", "Minimum Time Visiting All Points", "Water Bottles",
 "Split a String in Balanced Strings", "Count Symmetric Integers",
])

_sub("Two-Pointers", [
 "Two Pointers — recognize & apply",
 "3Sum", "Container With Most Water", "Move Zeroes", "Squares of a Sorted Array",
 "Valid Palindrome II (delete at most one)", "Is Subsequence", "Backspace String Compare",
 "Sort Colors (Dutch National Flag)", "Boats to Save People", "Sort Array By Parity",
 "Valid Mountain Array", "Two Sum IV - Input is a BST", "Trapping Rain Water",
])

_sub("Sliding-Window", [
 "Longest Substring Without Repeating Characters", "Longest Repeating Character Replacement",
 "Minimum Window Substring (sliding window)", "Sliding Window — recognize & apply",
 "Permutation in String", "Subarray Product Less Than K", "Sliding Window Maximum (deque)",
 "Minimum Recolors to Get K Consecutive Black Blocks",
])

_sub("Stack", [
 "Valid Parentheses", "Design a Min Stack", "Evaluate Reverse Polish Notation",
 "Daily Temperatures (monotonic stack)", "Decode String (stack)", "Asteroid Collision (stack)",
 "Next Greater Element (monotonic stack)", "Next Greater Element II (circular)",
 "Largest Rectangle in Histogram (monotonic stack)", "Basic Calculator (with parentheses)",
 "Implement a Queue using two Stacks", "Implement Stack using Queues",
 "Minimum Add to Make Parentheses Valid", "Generate Parentheses (backtracking)",
 "Remove Duplicate Letters",
])

_sub("Binary-Search", [
 "Binary Search — including 'search on the answer'", "Binary Search Lower Bound (bisect_left)",
 "Search in Rotated Sorted Array", "Find Minimum in Rotated Sorted Array",
 "Find First and Last Position (sorted array)", "Find Peak Element (binary search)",
 "Search a 2D Matrix", "Search Insert Position", "Koko Eating Bananas (binary search on the answer)",
 "Capacity to Ship Packages Within D Days", "Sqrt(x) — integer square root (binary search)",
 "Valid Perfect Square", "Arranging Coins", "Kth Missing Positive Number",
 "Search in a Binary Search Tree", "Closest Binary Search Tree Value",
 "Count Negatives in a Sorted Matrix", "Find Target Indices After Sorting Array",
])

_sub("Linked-List", [
 "Reverse Linked List", "Merge Two Sorted Lists", "Linked List Cycle",
 "Middle of the Linked List", "Palindrome Linked List", "Remove Nth Node From End of List",
 "Linked Lists — reversal & fast/slow pointers", "Merge k Sorted Lists (min-heap)",
 "Odd Even Linked List", "Rotate List", "Swap Nodes in Pairs",
 "Remove Duplicates from Sorted List", "Remove Linked List Elements",
 "Find the Duplicate Number (Floyd's cycle)", "Design an LRU Cache",
])

_sub("Trees", [
 "Maximum Depth of Binary Tree", "Invert a Binary Tree", "Balanced Binary Tree",
 "Diameter of a Binary Tree", "Same Tree", "Subtree of Another Tree", "Symmetric Tree",
 "Path Sum (root-to-leaf boolean)", "Path Sum II (all root-to-leaf paths)",
 "Path Sum III (prefix sum)", "Binary Tree Level Order Traversal",
 "Binary Tree Zigzag Level-Order Traversal", "Binary Tree Right Side View",
 "Average of Levels in Binary Tree", "Minimum Depth of Binary Tree", "Binary Tree Tilt",
 "Sum of Left Leaves", "Sum Root to Leaf Numbers", "Count Good Nodes in a Binary Tree",
 "Merge Two Binary Trees", "Trees — BFS vs DFS", "Lowest Common Ancestor of a Binary Tree",
 "Binary Tree Maximum Path Sum", "Construct Binary Tree from Preorder and Inorder",
 "Flatten Binary Tree to Linked List",
])

_sub("Tries", ["Trie (Prefix Tree)"])

_sub("Heap", [
 "Kth Largest Element", "Kth Largest Element in an Array", "Kth Largest Element in a Stream",
 "K Closest Points to Origin (heap)", "Find Median from Data Stream (two heaps)",
 "Last Stone Weight (max-heap)", "Task Scheduler (cooldown)", "Reorganize String (greedy heap)",
 "Heap / Top-K — when 'K largest/most frequent' appears", "Quickselect (kth largest)",
 "Sort Characters By Frequency", "Sort Array by Increasing Frequency",
 "Minimum Deletions to Make Character Frequencies Unique",
])

_sub("Backtracking", [
 "Backtracking — subsets, permutations, combinations", "Subsets (power set)",
 "Subsets II (with duplicates)", "Permutations (backtracking)",
 "Combination Sum (reusable candidates)", "Letter Combinations of a Phone Number",
 "Word Search (backtracking)", "Palindrome Partitioning (backtracking)",
])

_sub("Graphs", [
 "Graphs — BFS, DFS, and when to use each", "Number of Islands (DFS flood-fill)",
 "Clone Graph (DFS)", "Number of Connected Components", "Number of Provinces",
 "Course Schedule (topological sort)", "Topological Sort (Kahn's algorithm)",
 "Pacific Atlantic Water Flow", "Rotting Oranges (multi-source BFS)", "Flood Fill",
 "01 Matrix (distance to nearest zero)", "Surrounded Regions", "Word Ladder (shortest transformation, BFS)",
 "Shortest Path in Binary Matrix (8-directional BFS)", "Bipartite Graph Check (BFS 2-coloring)",
 "Dijkstra's Shortest Path (min-heap)", "Network Delay Time (Dijkstra application)",
 "Bellman-Ford (shortest path with negative edges)", "Cheapest Flights Within K Stops (Bellman-Ford)",
 "Prim's Minimum Spanning Tree", "Kruskal's Minimum Spanning Tree",
 "Union-Find / Disjoint Set Union (DSU)", "Union-Find (Disjoint Set Union)",
 "Redundant Connection (Union-Find)", "Find Center of Star Graph",
])

_sub("DP", [
 "Dynamic Programming — the 4-question method", "Climbing Stairs", "Min Cost Climbing Stairs (DP)",
 "House Robber", "House Robber II (circular street)", "Coin Change (fewest coins)",
 "Coin Change II (count ways)", "Word Break (DP)", "Decode Ways (DP)",
 "Longest Increasing Subsequence (patience + binary search)", "Longest Common Subsequence",
 "Longest Palindromic Subsequence", "Longest Arithmetic Subsequence",
 "Longest Palindromic Substring (expand around center)", "Edit Distance (Levenshtein)",
 "Maximum Subarray (Kadane's algorithm)", "Maximum Product Subarray",
 "Partition Equal Subset Sum", "Unique Paths (grid DP)", "Unique Paths II (grid with obstacles)",
 "Minimum Path Sum", "Triangle (Minimum Path Sum)", "Maximal Square (DP)",
 "Perfect Squares (DP)", "Integer Break (DP)", "N-th Tribonacci Number",
 "Best Time to Buy and Sell Stock with Cooldown", "Minimum Number of Coins for Fruits",
])

_sub("Greedy", [
 "Jump Game", "Jump Game II (fewest jumps)", "Gas Station (greedy circuit)",
 "Partition Labels (greedy)", "Best Time to Buy and Sell Stock II (greedy)",
 "Two City Scheduling (greedy)", "Maximum Units on a Truck (greedy)", "Assign Cookies",
 "Can Place Flowers (greedy)", "Lemonade Change (greedy)", "Wiggle Subsequence (greedy)",
 "Queue Reconstruction by Height", "Array Partition I", "Largest Perimeter Triangle",
 "Maximum Product Difference Between Two Pairs", "Maximum Product of Three Numbers",
 "Maximum Number of Coins You Can Get", "Minimum Moves to Equal Array Elements II",
 "Minimum Cost to Move Chips", "Minimum Number of Moves to Seat Everyone",
 "Minimum Sum of Four Digit Number After Splitting Digits",
 "Split a Number into Two Parts with Minimum Sum", "Distribute Candies",
 "Distribute Money to Maximum Children", "Kids With the Greatest Number of Candies",
 "Maximum Product of Two Elements in an Array", "Minimum Operations to Make the Array Increasing",
 "Minimum Cost to Make Array Non-decreasing (increasing via increments)",
 "Non-decreasing Array With One Modification", "Minimum Operations to Make Array Equal to Target",
 "Divide Players Into Teams of Equal Skill", "Pairs of Songs Divisible by 60",
 "Minimum Absolute Difference", "DI String Match", "Merge Similar Items", "Car Pooling",
 "Number of Steps to Reduce a Number in Binary to One",
])

_sub("Intervals", [
 "Intervals — merge, insert, overlap", "Merge Intervals", "Insert Interval",
 "Non-overlapping Intervals (min removals)", "Meeting Rooms (can attend all)",
 "Meeting Rooms II (minimum rooms)", "Minimum Number of Arrows to Burst Balloons",
 "Maximum Length of Pair Chain", "Find Right Interval", "Summary Ranges",
])

_sub("Math-Bits", [
 "Single Number (XOR)", "Single Number II (appears once among triples)",
 "Single Number III (two uniques)", "Missing Number", "Number of 1 Bits (popcount)",
 "Reverse Bits", "Hamming Distance", "Number Complement", "Minimum Bit Flips to Convert Number",
 "Sum of Values at Indices With K Set Bits", "Sort Integers by Number of 1 Bits",
 "Range Bitwise AND", "XOR Operation in an Array", "Find the Difference (XOR)",
 "Pow(x, n) — fast exponentiation", "Count Primes (Sieve of Eratosthenes)",
 "Happy Number", "Palindrome Number", "Reverse Integer", "Plus One", "Add Binary",
 "Add Strings", "Add to Array-Form of Integer", "Add Digits (digital root)",
 "Power of Two", "Power of Three", "Ugly Number", "Perfect Number", "Three Divisors",
 "Smallest Even Multiple", "Base 7 Conversion", "Sum of Digits in Base 10 After Convert",
 "Subtract the Product and Sum of Digits", "Alternating Digit Sum", "Self Dividing Numbers",
 "Three Consecutive Odds", "Count Odd Numbers in an Interval Range", "Fizz Buzz",
 "Roman to Integer", "Excel Sheet Column Number", "Number to Excel Column Title",
 "Day of the Year", "Number of Steps to Reduce a Number to Zero",
 "Sum of Squares of Special Elements", "String to Integer (atoi)", "First Missing Positive",
])

_sub("Matrix", [
 "Rotate Image (90 degrees, in place)", "Spiral Matrix", "Spiral Matrix II (generate)",
 "Set Matrix Zeroes (O(1) space)", "Valid Sudoku", "Transpose Matrix", "Toeplitz Matrix",
 "Matrix Diagonal Sum", "Matrix Reshape", "Lucky Numbers in a Matrix", "Flipping an Image",
])

_sub("Sorting", [
 "Merge Sort", "Quick Sort", "Counting Sort", "Largest Number (custom sort)",
 "Sort the People", "Relative Sort Array", "Height Checker", "Maximum Gap (bucket sort)",
 "Majority Element (Boyer-Moore voting)", "Majority Element II (> n/3)",
 "How Many Numbers Are Smaller Than the Current", "Rank Transform of an Array",
 "Convert Sorted Array to BST", "Count Tested Devices After Test Operations",
])

_sub("Design", [
 "Design HashMap", "Kth Smallest Element in a BST", "Range Sum of BST",
 "Lowest Common Ancestor of a BST", "Validate Binary Search Tree",
 "Convert BST to Greater Tree", "Minimum Absolute Difference in BST",
])


def R(title, topic, level, priority, fmt, stage, time, sub, flag=""):
    """One fully-tagged row, all seven columns in one call."""
    TAGS[title] = T(topic, level, priority, fmt, stage, time, flag)
    SUB[title] = sub


# ═══════════════════════════════════════════════════════════════════════════
# GLOSSARY - judged individually.  The category mixes two very different
# things and the PRIORITY column is where that shows: terms a new grad will
# genuinely be asked to explain (Big-O, hash table, gradient descent,
# overfitting, attention) against senior distributed-systems and SRE
# vocabulary that no new-grad loop reaches for (BGP, hinted handoff, fencing
# tokens, bulkheads).  A great many of the latter are Rare, on purpose.
# ═══════════════════════════════════════════════════════════════════════════

R("API gateway vs load balancer","System-Design","Medium","Common","Conceptual","Onsite","Quick","Fundamentals")
R("API key vs OAuth","Core-CS","Easy","Rare","Conceptual","Onsite","Quick","Systems")
R("Activation function","Deep-Learning","Easy","Must-Know","Conceptual","Either","Quick","Architectures")
R("Adam optimizer","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Optimization")
R("Adjacency list","DSA","Easy","Must-Know","Conceptual","Either","Quick","Graphs")
R("Adversarial example","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Training")
R("Amortized analysis","DSA","Medium","Common","Conceptual","Either","Medium","Arrays-Hashing")
R("Anycast","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Networking")
R("Approximate Nearest Neighbor (ANN / HNSW)","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Embeddings")
R("Array","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Arrays-Hashing")
R("At-least-once vs at-most-once vs exactly-once","System-Design","Medium","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Attention","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Autoencoder","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Architectures")
R("BERT","NLP-LLM","Medium","Common","Conceptual","Either","Quick","Transformers")
R("BFS vs DFS","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Graphs")
R("BGP (Border Gateway Protocol)","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","Networking")
R("BLEU","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Evaluation")
R("Backpressure","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Backpropagation","Deep-Learning","Medium","Must-Know","Math","Either","Medium","Training")
R("Bag-of-words & TF-IDF","NLP-LLM","Easy","Common","Conceptual","Either","Quick","Embeddings")
R("Batch (mini-batch)","Deep-Learning","Easy","Must-Know","Conceptual","Either","Quick","Training")
R("Batch normalization","Deep-Learning","Medium","Common","Conceptual","Either","Medium","Regularization")
R("Batch vs online learning","Classical-ML","Easy","Common","Conceptual","Either","Quick","Theory")
R("Bayes' theorem","Math-Stats","Medium","Must-Know","Math","Either","Medium","Probability")
R("Beam search","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Inference")
R("Bias (bias-variance)","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Theory")
R("Big-O notation","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Arrays-Hashing")
R("Binary Search Tree (BST)","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Trees")
R("Bitmap index","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Bloom filter","System-Design","Medium","Common","Conceptual","Onsite","Medium","Storage")
R("Blue-green vs canary deployment","MLOps","Medium","Common","Conceptual","Onsite","Quick","Deployment")
R("Blue-green vs rolling deployment","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Deployment")
R("Bootstrap (sampling)","Math-Stats","Medium","Common","Conceptual","Either","Quick","Statistics")
R("Bootstrap sampling","Math-Stats","Medium","Common","Conceptual","Either","Quick","Statistics",
  "near-duplicate of 'Bootstrap (sampling)'; kept as-is under the no-drop rule")
R("Buffered vs direct I/O","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","OS")
R("Bulkhead isolation","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Bulkhead pattern","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability",
  "near-duplicate of 'Bulkhead isolation'; kept as-is under the no-drop rule")
R("Byte-Pair Encoding (BPE)","NLP-LLM","Medium","Common","Conceptual","Either","Medium","Transformers")
R("CORS (Cross-Origin Resource Sharing)","Core-CS","Easy","Rare","Conceptual","Onsite","Quick","Networking")
R("CQRS","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("CSRF (Cross-Site Request Forgery)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("CUPED (variance reduction)","Math-Stats","Hard","Rare","Math","Onsite","Medium","Statistics")
R("Cache stampede","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Calibration (Platt / isotonic)","Classical-ML","Medium","Rare","Conceptual","Onsite","Medium","Evaluation")
R("Canary analysis (automated)","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Deployment")
R("Cardinality (of a feature)","Classical-ML","Easy","Common","Conceptual","Either","Quick","Feature-Engineering")
R("Catastrophic forgetting","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Fine-Tuning")
R("Certificate pinning","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Chain-of-thought prompting","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","Prompting")
R("Change data capture (CDC)","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Storage")
R("Chaos engineering","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Infra")
R("Circuit breaker","System-Design","Medium","Common","Conceptual","Onsite","Quick","Scalability")
R("Circuit breaker states","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Class weights & imbalance handling","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Evaluation")
R("Classification vs Regression","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Supervised")
R("Clustered vs non-clustered index","Core-CS","Medium","Common","Conceptual","Either","Quick","DBMS")
R("Columnar encoding (RLE / dictionary)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Competing consumers","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Confidence interval","Math-Stats","Medium","Common","Math","Either","Medium","Statistics")
R("Confounding variable","Math-Stats","Medium","Common","Conceptual","Either","Quick","Statistics")
R("Confusion matrix","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Evaluation")
R("Connection draining","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Connection pooling","Core-CS","Medium","Common","Conceptual","Onsite","Quick","DBMS")
R("Consistent hashing","System-Design","Medium","Common","Conceptual","Onsite","Medium","Scalability")
R("Consistent hashing with virtual nodes","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Scalability")
R("Content Security Policy (CSP)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Contrastive learning","Deep-Learning","Medium","Rare","Conceptual","Onsite","Medium","Training")
R("Convolution (CNN)","Deep-Learning","Medium","Common","Conceptual","Either","Medium","CNN")
R("Cookie security flags (Secure / HttpOnly / SameSite)","Core-CS","Easy","Rare","Conceptual","Onsite","Quick","Systems")
R("Cookies vs tokens (JWT)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Cosine annealing (LR schedule)","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Optimization")
R("Cosine similarity","Math-Stats","Easy","Must-Know","Math","Either","Quick","Linear-Algebra")
R("Cost-based optimizer (query plan)","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","DBMS")
R("Count-min sketch","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("Covariance vs Correlation","Math-Stats","Easy","Common","Math","Either","Quick","Statistics")
R("Covariate shift vs label shift","Classical-ML","Medium","Rare","Conceptual","Onsite","Medium","Theory")
R("Cross-attention","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Transformers")
R("Cross-entropy (log loss)","Classical-ML","Medium","Must-Know","Math","Either","Medium","Evaluation")
R("Curriculum learning","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Training")
R("DBSCAN","Classical-ML","Medium","Rare","Conceptual","Onsite","Medium","Unsupervised")
R("DDoS mitigation","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("DNS recursion / resolution","Core-CS","Easy","Common","Conceptual","Either","Quick","Networking")
R("DNSSEC","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","Networking")
R("Data augmentation","Deep-Learning","Easy","Common","Conceptual","Either","Quick","Regularization")
R("Data drift","MLOps","Medium","Common","Conceptual","Either","Quick","Monitoring")
R("Data drift vs concept drift","MLOps","Medium","Common","Conceptual","Either","Medium","Monitoring")
R("Data lake vs warehouse vs lakehouse","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Pipelines")
R("Data skew","System-Design","Medium","Common","Conceptual","Onsite","Quick","Scalability")
R("Data structure","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Arrays-Hashing")
R("Dead letter queue","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Decision tree","Classical-ML","Easy","Must-Know","Conceptual","Either","Medium","Trees-Ensembles")
R("Diffusion model","Deep-Learning","Hard","Rare","Conceptual","Onsite","Medium","Architectures")
R("Dijkstra's algorithm","DSA","Medium","Must-Know","Conceptual","Either","Medium","Graphs")
R("Divide and conquer","DSA","Easy","Common","Conceptual","Either","Quick","Sorting")
R("Domain adaptation","Classical-ML","Medium","Rare","Conceptual","Onsite","Quick","Theory")
R("Dropout","Deep-Learning","Easy","Must-Know","Conceptual","Either","Quick","Regularization")
R("Dynamic programming","DSA","Medium","Must-Know","Conceptual","Either","Medium","DP")
R("ETag / conditional requests","Core-CS","Easy","Rare","Conceptual","Onsite","Quick","Networking")
R("Early stopping","Deep-Learning","Easy","Must-Know","Conceptual","Either","Quick","Regularization")
R("Elbow method","Classical-ML","Easy","Common","Conceptual","Either","Quick","Unsupervised")
R("Embedding","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","Embeddings")
R("Encoder-decoder (seq2seq)","NLP-LLM","Medium","Common","Conceptual","Either","Medium","Transformers")
R("Entropy","Math-Stats","Easy","Common","Math","Either","Quick","Information-Theory",
  "sits across Math-Stats and Classical-ML; reached via decision-tree splits and cross-entropy loss")
R("Epoch","Deep-Learning","Easy","Must-Know","Conceptual","Screen","Quick","Training")
R("Epsilon-greedy","Classical-ML","Medium","Rare","Conceptual","Onsite","Quick","Theory")
R("Event sourcing","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Storage")
R("Event time vs processing time","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Storage")
R("Exactly-once semantics","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Expand-contract migration","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Storage")
R("Exploding gradient","Deep-Learning","Medium","Common","Conceptual","Either","Quick","Training")
R("Exploration vs exploitation","Classical-ML","Easy","Common","Conceptual","Either","Quick","Theory")
R("Exponential backoff with jitter","System-Design","Easy","Common","Conceptual","Either","Quick","Fundamentals")
R("Exponential moving average (EMA)","Math-Stats","Easy","Rare","Math","Onsite","Quick","Statistics")
R("F-beta score","Classical-ML","Medium","Common","Math","Either","Quick","Evaluation")
R("F1 score","Classical-ML","Easy","Must-Know","Math","Screen","Quick","Evaluation")
R("Feature hashing (the hashing trick)","Classical-ML","Medium","Rare","Conceptual","Onsite","Quick","Feature-Engineering")
R("Feature store","MLOps","Medium","Common","Conceptual","Onsite","Quick","Pipelines")
R("Feature toggle types","MLOps","Easy","Rare","Conceptual","Onsite","Quick","Deployment")
R("Feature vs Label","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Supervised")
R("Fencing token","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Few-shot vs zero-shot learning","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","Prompting")
R("Fine-tuning","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Fine-Tuning")
R("Flash attention","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Inference")
R("Focal loss","Deep-Learning","Medium","Rare","Math","Onsite","Quick","Training")
R("Forward proxy vs reverse proxy","Core-CS","Easy","Common","Conceptual","Either","Quick","Networking")
R("Full-text index","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("GAN (Generative Adversarial Network)","Deep-Learning","Medium","Common","Conceptual","Either","Medium","Architectures")
R("GPT","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","Transformers")
R("Generalization","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("Geospatial index","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Gini impurity","Classical-ML","Medium","Common","Math","Either","Quick","Trees-Ensembles")
R("GitOps","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Infra")
R("Gossip protocol","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Graceful degradation","System-Design","Easy","Common","Conceptual","Onsite","Quick","Scalability")
R("Gradient","Math-Stats","Easy","Must-Know","Math","Either","Quick","Calculus")
R("Gradient Descent","Math-Stats","Easy","Must-Know","Math","Either","Medium","Calculus")
R("Gradient accumulation","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Training")
R("Gradient boosting","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Trees-Ensembles")
R("Gradient clipping","Deep-Learning","Medium","Common","Conceptual","Either","Quick","Training")
R("Graph","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Graphs")
R("Greedy algorithm","DSA","Easy","Must-Know","Conceptual","Either","Quick","Greedy")
R("Greedy decoding","NLP-LLM","Easy","Common","Conceptual","Either","Quick","Inference")
R("Group vs Layer normalization","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Regularization")
R("Guardrail metric","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Monitoring")
R("HSTS (HTTP Strict Transport Security)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("HTTP keep-alive (persistent connections)","Core-CS","Easy","Rare","Conceptual","Onsite","Quick","Networking")
R("HTTP status code families","Core-CS","Easy","Common","Conceptual","Either","Quick","Networking")
R("HTTP/2 multiplexing","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Networking")
R("Hallucination (LLMs)","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Evaluation")
R("Hash set","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Arrays-Hashing")
R("Hash table (hash map)","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Arrays-Hashing")
R("Head-of-line blocking","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Networking")
R("Health check (liveness vs readiness)","MLOps","Easy","Common","Conceptual","Onsite","Quick","Deployment")
R("Heap (priority queue)","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Heap")
R("Hedged requests","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Hinge loss","Classical-ML","Medium","Rare","Math","Onsite","Quick","Supervised")
R("Hinted handoff","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage")
R("Hot partition","System-Design","Medium","Common","Conceptual","Onsite","Quick","Scalability")
R("Huber loss","Classical-ML","Medium","Rare","Math","Onsite","Quick","Supervised")
R("HyperLogLog","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("Hyperparameter vs Parameter","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("ISR (in-sync replicas)","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage")
R("Idempotency key","System-Design","Medium","Common","Conceptual","Onsite","Quick","Fundamentals")
R("Idempotent HTTP methods","Core-CS","Easy","Common","Conceptual","Either","Quick","Networking")
R("Idempotent producer","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Immutable infrastructure","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Infra")
R("Imputation","Classical-ML","Easy","Common","Conceptual","Either","Quick","Feature-Engineering")
R("Imputation strategies","Classical-ML","Medium","Common","Conceptual","Either","Medium","Feature-Engineering",
  "near-duplicate of 'Imputation'; kept as-is under the no-drop rule")
R("In-place algorithm","DSA","Easy","Common","Conceptual","Either","Quick","Arrays-Hashing")
R("Index selectivity","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Inference (vs training)","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("Infrastructure as Code (IaC)","MLOps","Easy","Rare","Conceptual","Onsite","Quick","Infra")
R("Interleaving (online evaluation)","MLOps","Hard","Rare","Conceptual","Onsite","Medium","Monitoring")
R("Inverse propensity weighting (IPW)","Math-Stats","Hard","Rare","Math","Onsite","Medium","Statistics")
R("Isolation forest","Classical-ML","Medium","Rare","Conceptual","Onsite","Quick","Unsupervised")
R("JWT structure & claims","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Join algorithms (nested-loop / hash / sort-merge)","Core-CS","Medium","Common","Conceptual","Onsite","Medium","DBMS")
R("K-fold cross-validation","Classical-ML","Easy","Must-Know","Conceptual","Either","Medium","Evaluation")
R("KL divergence","Math-Stats","Medium","Common","Math","Onsite","Medium","Information-Theory")
R("KV cache","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Inference")

# ── GLOSSARY, second half ──────────────────────────────────────────────────
R("Knowledge distillation","Deep-Learning","Medium","Common","Conceptual","Onsite","Medium","Training")
R("LSM internals (memtable, SSTable, compaction)","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("LSM tree vs B-tree","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("Label smoothing","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Regularization")
R("Layer normalization","Deep-Learning","Medium","Common","Conceptual","Either","Quick","Regularization")
R("Learning rate","Deep-Learning","Easy","Must-Know","Conceptual","Screen","Quick","Optimization")
R("Learning-rate schedule","Deep-Learning","Medium","Common","Conceptual","Either","Quick","Optimization")
R("Learning-rate warmup","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Optimization")
R("Lease","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Linear regression","Classical-ML","Easy","Must-Know","Math","Either","Medium","Supervised")
R("Linked list","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Linked-List")
R("Liveness vs readiness probes","MLOps","Easy","Rare","Conceptual","Onsite","Quick","Deployment",
  "near-duplicate of 'Health check (liveness vs readiness)'; kept as-is under the no-drop rule")
R("LoRA (Low-Rank Adaptation)","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Fine-Tuning")
R("LoRA / PEFT","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Fine-Tuning",
  "near-duplicate of 'LoRA (Low-Rank Adaptation)'; kept as-is under the no-drop rule")
R("Load balancer: L4 vs L7","System-Design","Medium","Common","Conceptual","Onsite","Quick","Fundamentals")
R("Load shedding","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Log compaction (Kafka)","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage")
R("Logistic regression","Classical-ML","Easy","Must-Know","Math","Either","Medium","Supervised")
R("Loss (cost) function","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("MAE (Mean Absolute Error)","Classical-ML","Easy","Must-Know","Math","Screen","Quick","Evaluation")
R("MAP (Maximum A Posteriori)","Math-Stats","Medium","Rare","Math","Onsite","Medium","Probability")
R("MSE (Mean Squared Error)","Classical-ML","Easy","Must-Know","Math","Screen","Quick","Evaluation")
R("MVCC (Multi-Version Concurrency Control)","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","DBMS")
R("Masked language modeling (MLM)","NLP-LLM","Medium","Common","Conceptual","Either","Quick","Transformers")
R("Materialized view","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Maximum Likelihood Estimation (MLE)","Math-Stats","Medium","Common","Math","Onsite","Medium","Probability")
R("Mean Reciprocal Rank (MRR)","Classical-ML","Medium","Rare","Math","Onsite","Quick","Evaluation")
R("Memoization","DSA","Easy","Must-Know","Conceptual","Either","Quick","DP")
R("Message ordering guarantees","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Metric cardinality","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Monitoring")
R("Mixed-precision training","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Training")
R("Mixture of Experts (MoE)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Transformers")
R("Mixup","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Regularization")
R("Momentum","Deep-Learning","Medium","Common","Math","Either","Quick","Optimization")
R("Multicollinearity / VIF","Math-Stats","Medium","Common","Conceptual","Either","Medium","Statistics")
R("Mutual information","Math-Stats","Medium","Rare","Math","Onsite","Medium","Information-Theory")
R("N+1 query problem","Core-CS","Medium","Common","Conceptual","Onsite","Quick","DBMS")
R("Nagle's algorithm","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","Networking")
R("Naive Bayes","Classical-ML","Easy","Common","Math","Either","Medium","Supervised")
R("Named-entity recognition (NER)","NLP-LLM","Easy","Rare","Conceptual","Onsite","Quick","Evaluation")
R("Negative caching","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Negative sampling","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Embeddings")
R("Neural network","Deep-Learning","Easy","Must-Know","Conceptual","Screen","Medium","Architectures")
R("Normalization vs Standardization","Classical-ML","Easy","Must-Know","Conceptual","Either","Quick","Feature-Engineering")
R("North-south vs east-west traffic","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("OAuth2 authorization flow","Core-CS","Medium","Rare","Conceptual","Onsite","Medium","Systems")
R("OLAP vs OLTP","Core-CS","Easy","Common","Conceptual","Either","Quick","DBMS")
R("Observability: the three pillars","MLOps","Easy","Common","Conceptual","Onsite","Quick","Monitoring")
R("One-hot encoding","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Feature-Engineering")
R("OpenID Connect (OIDC)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Out-of-distribution (OOD)","Classical-ML","Medium","Common","Conceptual","Either","Quick","Theory")
R("Overfitting","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("PACELC theorem","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("PCA (Principal Component Analysis)","Math-Stats","Medium","Must-Know","Math","Either","Medium","Linear-Algebra")
R("PKCE","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","Systems")
R("PR-AUC (Precision-Recall AUC)","Classical-ML","Medium","Common","Math","Either","Medium","Evaluation")
R("Perplexity","NLP-LLM","Medium","Common","Math","Either","Medium","Evaluation")
R("Pointwise vs pairwise vs listwise ranking","Classical-ML","Hard","Rare","Conceptual","Onsite","Medium","Supervised")
R("Position bias","Classical-ML","Medium","Rare","Conceptual","Onsite","Quick","Evaluation")
R("Positional encoding","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Precision","Classical-ML","Easy","Must-Know","Math","Screen","Quick","Evaluation")
R("Predicate pushdown","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Prepared statement","Core-CS","Easy","Common","Conceptual","Either","Quick","DBMS")
R("Prior vs Posterior (Bayesian)","Math-Stats","Medium","Common","Math","Either","Medium","Probability")
R("Prompt engineering","NLP-LLM","Easy","Common","Conceptual","Either","Quick","Prompting")
R("QUIC","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Networking")
R("Quantization (model)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Inference")
R("Quorum (W + R > N)","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("R-squared (coefficient of determination)","Math-Stats","Medium","Common","Math","Either","Medium","Statistics")
R("RED vs USE metrics","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Monitoring")
R("RLHF (Reinforcement Learning from Human Feedback)","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Fine-Tuning")
R("ROUGE","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Evaluation")
R("Raft consensus","System-Design","Hard","Rare","Conceptual","Onsite","Deep","Fundamentals")
R("Random forest","Classical-ML","Easy","Must-Know","Conceptual","Either","Medium","Trees-Ensembles")
R("ReLU (Rectified Linear Unit)","Deep-Learning","Easy","Must-Know","Conceptual","Screen","Quick","Architectures")
R("Read repair and anti-entropy","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage")
R("Read-repair","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage",
  "near-duplicate of 'Read repair and anti-entropy'; kept as-is under the no-drop rule")
R("Read-through vs write-through cache","System-Design","Medium","Common","Conceptual","Onsite","Medium","Scalability")
R("Recall (sensitivity)","Classical-ML","Easy","Must-Know","Math","Screen","Quick","Evaluation")
R("Recall@k","Classical-ML","Medium","Common","Math","Onsite","Quick","Evaluation")
R("Recursion","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Backtracking")
R("Refresh token rotation","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Regret (online learning)","Math-Stats","Hard","Rare","Math","Onsite","Medium","Statistics")
R("Regularization","Classical-ML","Easy","Must-Know","Conceptual","Either","Medium","Theory")
R("Reinforcement learning (agent, reward, policy)","Classical-ML","Medium","Common","Conceptual","Either","Medium","Theory")
R("Request coalescing","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Scalability")
R("Residual connection (skip connection)","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Architectures")
R("Retrieval-Augmented Generation (RAG)","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","RAG")
R("SAML","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","Systems")
R("SHAP / feature importance","Classical-ML","Medium","Common","Conceptual","Onsite","Medium","Evaluation")
R("SLI / SLO / SLA (+ error budget)","MLOps","Medium","Common","Conceptual","Onsite","Quick","Monitoring")
R("SMOTE","Classical-ML","Medium","Common","Conceptual","Either","Quick","Evaluation")
R("SQL injection","Core-CS","Easy","Common","Conceptual","Either","Quick","Systems")
R("SVM (Support Vector Machine)","Classical-ML","Medium","Common","Math","Either","Medium","Supervised")
R("Saga: choreography vs orchestration","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Sample ratio mismatch (SRM)","Math-Stats","Hard","Rare","Conceptual","Onsite","Quick","Statistics")
R("Sampling in observability","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Monitoring")
R("Selection bias","Math-Stats","Easy","Common","Conceptual","Either","Quick","Statistics")
R("Self-supervised learning","Deep-Learning","Medium","Common","Conceptual","Either","Medium","Training")
R("Semi-supervised & active learning","Classical-ML","Medium","Rare","Conceptual","Onsite","Medium","Theory")
R("Service discovery (client-side vs server-side)","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Service mesh","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Sidecar pattern","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Sigmoid","Deep-Learning","Easy","Must-Know","Math","Screen","Quick","Architectures")
R("Silhouette score","Classical-ML","Medium","Common","Math","Either","Quick","Unsupervised")
R("Simpson's paradox","Math-Stats","Medium","Common","Conceptual","Either","Medium","Statistics")
R("Sliding window vs fixed window rate limiter","System-Design","Medium","Common","Conceptual","Onsite","Medium","Scalability")
R("Snapshot isolation","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","DBMS")
R("Softmax","Deep-Learning","Easy","Must-Know","Math","Screen","Quick","Architectures")
R("Softmax temperature","NLP-LLM","Medium","Common","Math","Either","Quick","Inference")
R("Split-brain","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Stable sort","DSA","Easy","Common","Conceptual","Either","Quick","Sorting")
R("Stack vs Queue","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Stack")
R("Star vs snowflake schema","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Statistical power","Math-Stats","Medium","Rare","Math","Onsite","Medium","Statistics")
R("Stemming vs Lemmatization","NLP-LLM","Easy","Common","Conceptual","Either","Quick","Embeddings")
R("Sticky sessions (session affinity)","System-Design","Medium","Rare","Conceptual","Onsite","Quick","Fundamentals")
R("Stratified sampling","Math-Stats","Easy","Common","Conceptual","Either","Quick","Statistics")
R("Streaming windows (tumbling / sliding / session)","System-Design","Medium","Rare","Conceptual","Onsite","Medium","Storage")
R("Structured logging & log levels","MLOps","Easy","Common","Conceptual","Onsite","Quick","Monitoring")
R("Subresource Integrity (SRI)","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","Systems")
R("Supervised vs Unsupervised vs Reinforcement","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("TCP slow start","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Networking")
R("TCP vs UDP","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","Networking")
R("TLS 1.3 handshake","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","Networking")
R("TTL index","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","DBMS")
R("Tabulation","DSA","Easy","Must-Know","Conceptual","Either","Quick","DP")
R("Target encoding","Classical-ML","Medium","Common","Conceptual","Onsite","Medium","Feature-Engineering")
R("Target leakage","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Feature-Engineering")
R("Teacher forcing","Deep-Learning","Medium","Rare","Conceptual","Onsite","Quick","Sequence-Models")
R("Temperature (sampling)","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","Inference")
R("Tensor","Deep-Learning","Easy","Must-Know","Conceptual","Screen","Quick","Architectures")
R("Thompson sampling","Math-Stats","Hard","Rare","Math","Onsite","Medium","Probability")
R("Thundering herd problem","System-Design","Medium","Common","Conceptual","Onsite","Quick","Scalability")
R("Time vs Space complexity","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Arrays-Hashing")
R("Token","NLP-LLM","Easy","Must-Know","Conceptual","Screen","Quick","Transformers")
R("Token bucket vs leaky bucket","System-Design","Medium","Common","Conceptual","Onsite","Medium","Scalability")
R("Tokenization / BPE","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Tombstone (deletes)","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage")
R("Top-p (nucleus) sampling","NLP-LLM","Medium","Must-Know","Conceptual","Either","Quick","Inference")
R("Topological sort","DSA","Medium","Must-Know","Conceptual","Either","Medium","Graphs")
R("Transactional outbox","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("Transfer learning","Deep-Learning","Easy","Must-Know","Conceptual","Either","Quick","Training")
R("Transformer","NLP-LLM","Medium","Must-Know","Conceptual","Either","Deep","Transformers")
R("Tree","DSA","Easy","Must-Know","Conceptual","Screen","Quick","Trees")
R("Triplet loss","Deep-Learning","Medium","Rare","Math","Onsite","Medium","Training")
R("Type I vs Type II error","Math-Stats","Easy","Must-Know","Conceptual","Either","Quick","Statistics")
R("UCB (Upper Confidence Bound)","Math-Stats","Hard","Rare","Math","Onsite","Medium","Probability")
R("Underfitting","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Theory")
R("Vanishing gradient","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Training")
R("Variance (bias-variance)","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Theory")
R("Vector clocks","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Vector database","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","RAG")
R("Vector database / ANN","NLP-LLM","Medium","Common","Conceptual","Either","Medium","RAG",
  "near-duplicate of 'Vector database'; kept as-is under the no-drop rule")
R("WAF (Web Application Firewall)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("Weak supervision","Classical-ML","Medium","Rare","Conceptual","Onsite","Quick","Theory")
R("Weight decay (L2 regularization)","Deep-Learning","Medium","Common","Math","Either","Medium","Regularization")
R("Weight initialization","Deep-Learning","Medium","Common","Conceptual","Either","Quick","Training")
R("Word2vec","NLP-LLM","Medium","Common","Conceptual","Either","Medium","Embeddings")
R("Write / read / space amplification","System-Design","Hard","Rare","Conceptual","Onsite","Quick","Storage")
R("Write-ahead log (WAL)","Core-CS","Medium","Common","Conceptual","Onsite","Medium","DBMS")
R("XSS (Cross-Site Scripting)","Core-CS","Easy","Common","Conceptual","Either","Quick","Systems")
R("Zero-copy","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","OS")
R("Zero-shot / few-shot / in-context learning","NLP-LLM","Easy","Must-Know","Conceptual","Either","Quick","Prompting",
  "near-duplicate of 'Few-shot vs zero-shot learning'; kept as-is under the no-drop rule")
R("fsync (durability)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","OS")
R("gRPC vs REST","Core-CS","Medium","Common","Conceptual","Onsite","Medium","Networking")
R("gzip vs brotli","Core-CS","Easy","Rare","Conceptual","Onsite","Quick","Networking")
R("k-means","Classical-ML","Easy","Must-Know","Conceptual","Either","Medium","Unsupervised")
R("mTLS (mutual TLS)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","Systems")
R("mmap (memory-mapped files)","Core-CS","Hard","Rare","Conceptual","Onsite","Quick","OS")
R("n-gram","NLP-LLM","Easy","Common","Conceptual","Either","Quick","Embeddings")
R("p-value","Math-Stats","Medium","Must-Know","Math","Either","Medium","Statistics")
R("t-SNE / UMAP","Math-Stats","Medium","Common","Conceptual","Either","Medium","Linear-Algebra")

# ═══════════════════════════════════════════════════════════════════════════
# CONCEPTUAL - "why" questions.  FORMAT is Conceptual almost by definition;
# the discriminating columns here are TOPIC (they range across the whole
# syllabus) and PRIORITY (a good third are systems-depth questions a new grad
# will not be asked).
# ═══════════════════════════════════════════════════════════════════════════
R("If deep learning is so powerful, why do gradient-boosted trees still win on tabular data?","Classical-ML","Medium","Common","Conceptual","Either","Medium","Trees-Ensembles")
R("Why (and when) choose L7 load balancing over L4?","System-Design","Medium","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Why add jitter to exponential backoff instead of just backing off exponentially?","System-Design","Medium","Common","Conceptual","Onsite","Quick","Scalability")
R("Why aggregate streams by event time instead of processing time?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("Why can R-squared be negative, and what does that tell you about a model?","Math-Stats","Medium","Rare","Conceptual","Either","Quick","Statistics")
R("Why can a model score great offline but fail once deployed online?","MLOps","Medium","Must-Know","Conceptual","Either","Medium","Monitoring")
R("Why can a model with 99% accuracy be useless?","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Evaluation")
R("Why can two O(n log n) sorts (merge sort vs quicksort) perform so differently?","DSA","Medium","Common","Conceptual","Either","Medium","Sorting")
R("Why denormalize a database if normalization is the 'correct' design?","Core-CS","Medium","Common","Conceptual","Either","Medium","DBMS")
R("Why did QUIC/HTTP/3 build a new protocol over UDP instead of just improving TCP?","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","Networking")
R("Why do LSM/append-only stores delete with tombstones instead of removing the data?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Storage")
R("Why do Transformers need positional encoding when RNNs don't?","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Why do Transformers need positional encodings but RNNs don't?","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers",
  "near-duplicate of the entry above (singular/plural); kept as-is under the no-drop rule")
R("Why do databases use B-trees / LSM-trees instead of a hash index for most workloads?","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","DBMS")
R("Why do ensembles (bagging, boosting) usually beat a single model?","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Trees-Ensembles")
R("Why do hedged requests reduce tail latency, and why not just send duplicate requests always?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Scalability")
R("Why do recommendation and ad systems use a two-stage retrieval-then-ranking architecture instead of one big model?","System-Design","Hard","Common","Conceptual","Onsite","Deep","ML-System-Design")
R("Why do we distinguish latency from throughput?","System-Design","Easy","Common","Conceptual","Either","Quick","Fundamentals")
R("Why do we need a learning rate — why not jump straight to the minimum?","Deep-Learning","Easy","Must-Know","Conceptual","Either","Medium","Optimization")
R("Why do we need a separate validation set AND a test set?","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Evaluation")
R("Why do we need consensus algorithms (Raft/Paxos) instead of a naive majority vote?","System-Design","Hard","Rare","Conceptual","Onsite","Deep","Fundamentals")
R("Why do we need idempotent consumers with at-least-once delivery, and how do you make one?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Why do we scale/normalize features before training many models?","Classical-ML","Easy","Must-Know","Conceptual","Either","Quick","Feature-Engineering")
R("Why do you need both liveness and readiness probes, and what breaks if you conflate them?","MLOps","Medium","Rare","Conceptual","Onsite","Medium","Deployment")
R("Why does Adam need bias correction, and what goes wrong without it?","Deep-Learning","Hard","Rare","Math","Onsite","Medium","Optimization")
R("Why does HTTP/2 multiplexing not fully eliminate head-of-line blocking, and how does HTTP/3 fix it?","Core-CS","Hard","Rare","Conceptual","Onsite","Medium","Networking")
R("Why does L2 regularization reduce overfitting, and how does it differ from L1?","Classical-ML","Medium","Must-Know","Math","Either","Medium","Theory")
R("Why does TCP start slow (slow start) instead of sending at full speed immediately?","Core-CS","Medium","Rare","Conceptual","Onsite","Medium","Networking")
R("Why does XOR let you find a unique number in O(1) space?","DSA","Medium","Common","Conceptual","Either","Quick","Math-Bits")
R("Why does a database index speed up reads but slow down writes?","Core-CS","Easy","Must-Know","Conceptual","Either","Quick","DBMS")
R("Why does a hash table give O(1) lookup — and when does it fail?","DSA","Medium","Must-Know","Conceptual","Either","Medium","Arrays-Hashing")
R("Why does batching make inference cheaper but can raise latency?","MLOps","Medium","Common","Conceptual","Onsite","Medium","Deployment")
R("Why does dropout act as a regularizer?","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Regularization")
R("Why does focal loss help with class imbalance where weighted cross-entropy alone falls short?","Deep-Learning","Hard","Rare","Math","Onsite","Medium","Training")
R("Why does labeling by uncertainty (active learning) beat random labeling, and when can it backfire?","Classical-ML","Hard","Rare","Conceptual","Onsite","Medium","Theory")
R("Why does layer normalization work better than batch normalization for Transformers and RNNs?","Deep-Learning","Hard","Common","Conceptual","Onsite","Medium","Regularization")
R("Why does min-max scaling suffer from outliers while standardization is more robust?","Classical-ML","Easy","Common","Conceptual","Either","Quick","Feature-Engineering")
R("Why does minimum depth of a binary tree need special handling for single-child nodes?","DSA","Easy","Common","Conceptual","Either","Quick","Trees")
R("Why does momentum speed up gradient descent, and what problem with plain SGD does it fix?","Deep-Learning","Medium","Common","Math","Either","Medium","Optimization")
R("Why does more data usually beat a cleverer algorithm?","Classical-ML","Easy","Common","Conceptual","Either","Quick","Theory")
R("Why does more/better data often beat a fancier algorithm?","Classical-ML","Easy","Common","Conceptual","Either","Quick","Theory",
  "near-duplicate of the entry above; kept as-is under the no-drop rule")
R("Why does pretraining + fine-tuning beat training from scratch?","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Training")
R("Why does the browser enforce the same-origin policy, and why do we then need CORS?","Core-CS","Medium","Rare","Conceptual","Onsite","Medium","Systems")
R("Why does the median minimize total absolute distance while the mean minimizes squared distance?","Math-Stats","Medium","Common","Math","Either","Medium","Statistics")
R("Why does the softmax+cross-entropy gradient simplify to (probs - labels), and why fuse them?","Deep-Learning","Hard","Common","Math","Onsite","Medium","Training")
R("Why does the tails array in the O(n log n) LIS algorithm give the correct length but not a valid subsequence?","DSA","Hard","Rare","Conceptual","Onsite","Medium","DP")
R("Why does validating a BST require passing down min/max bounds instead of just comparing to children?","DSA","Medium","Must-Know","Conceptual","Either","Medium","Trees")
R("Why is Bayes' theorem so counterintuitive with rare events?","Math-Stats","Medium","Must-Know","Math","Either","Medium","Probability")
R("Why is O(n log n) the limit for comparison sorting — can we beat it?","DSA","Medium","Common","Conceptual","Either","Medium","Sorting")
R("Why is UDP used for video, gaming, VoIP, and DNS despite being unreliable?","Core-CS","Easy","Common","Conceptual","Either","Quick","Networking")
R("Why is a columnar storage format faster for analytics than a row format?","Core-CS","Medium","Common","Conceptual","Onsite","Medium","DBMS")
R("Why is a stack the natural tool for matching and undo?","DSA","Easy","Common","Conceptual","Either","Quick","Stack")
R("Why is accuracy a poor metric for imbalanced classification?","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Evaluation")
R("Why is exactly-once delivery essentially impossible, and how do systems fake it?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Why is recursion elegant but sometimes dangerous?","DSA","Easy","Common","Conceptual","Either","Quick","Backtracking")
R("Why might adding more features hurt performance?","Classical-ML","Medium","Common","Conceptual","Either","Medium","Feature-Engineering")
R("Why must you use time-based splits (not random shuffling) when evaluating models on temporal data like fraud or forecasting?","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Evaluation")
R("Why prefer immutable infrastructure over patching servers in place?","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Infra")
R("Why report p99/tail latency instead of average latency?","System-Design","Easy","Common","Conceptual","Either","Quick","Fundamentals")
R("Why sample traces/logs instead of collecting everything?","MLOps","Medium","Rare","Conceptual","Onsite","Quick","Monitoring")
R("Why scale by 1/(1-p) in dropout, and why is inference a no-op?","Deep-Learning","Hard","Rare","Math","Onsite","Medium","Regularization")
R("Why should PUT/DELETE be idempotent but POST not — and why does it matter for retries?","Core-CS","Medium","Common","Conceptual","Either","Medium","Networking")
R("Why split data into train / validation / test — why not just train and test?","Classical-ML","Easy","Must-Know","Conceptual","Screen","Quick","Evaluation",
  "near-duplicate of 'Why do we need a separate validation set AND a test set?'; kept under the no-drop rule")
R("Why subtract the max before exponentiating in softmax, and why is the result unchanged?","Deep-Learning","Medium","Common","Math","Either","Medium","Architectures")
R("Why train classifiers with cross-entropy loss instead of accuracy?","Classical-ML","Medium","Must-Know","Math","Either","Medium","Evaluation")
R("Why use CQRS (separate read and write models), and when is it worth the complexity?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Why use a sidecar / service mesh instead of a shared library in each service?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Fundamentals")
R("Why use connection pooling instead of a database connection per request?","Core-CS","Medium","Common","Conceptual","Onsite","Quick","DBMS")
R("Why use the bulkhead pattern to isolate resources instead of a shared pool?","System-Design","Hard","Rare","Conceptual","Onsite","Medium","Scalability")

# ═══════════════════════════════════════════════════════════════════════════
# ML CONCEPTS - the classic "explain X" ML round.  Heavily Must-Know: this is
# the category a new-grad AI/SDE interview actually lives in.
# ═══════════════════════════════════════════════════════════════════════════
R("A/B testing an ML model (and the statistics you must get right)","Math-Stats","Medium","Common","Conceptual","Onsite","Deep","Statistics")
R("Activation functions - which one, and why","Deep-Learning","Easy","Must-Know","Conceptual","Either","Medium","Architectures")
R("Attention Mechanism Intuition","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Backpropagation worked by hand on a tiny network","Deep-Learning","Hard","Common","Math","Onsite","Deep","Training")
R("Bias-Variance Decomposition","Classical-ML","Hard","Common","Math","Onsite","Medium","Theory")
R("Bias-Variance trade-off (explained simply)","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Theory")
R("CNN vs RNN vs Transformer — when to use which","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Architectures")
R("Class Imbalance Strategies","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Evaluation")
R("Cross-validation — what and why","Classical-ML","Easy","Must-Know","Conceptual","Screen","Medium","Evaluation")
R("Data leakage - the bug that makes a terrible model look excellent","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Feature-Engineering")
R("Decision Trees & Random Forests","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Trees-Ensembles")
R("Diagnosing a model with learning curves (is it bias or variance?)","Classical-ML","Medium","Common","Conceptual","Onsite","Medium","Evaluation")
R("Ensembles — Bagging vs Boosting","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Trees-Ensembles")
R("Evaluation metrics: the complete map, and how to choose","Classical-ML","Medium","Must-Know","Conceptual","Either","Deep","Evaluation")
R("Feature engineering, scaling & encoding","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Feature-Engineering")
R("How a decision tree actually picks a split (Gini, entropy, information gain)","Classical-ML","Medium","Must-Know","Math","Either","Medium","Trees-Ensembles")
R("How gradient descent works (batch vs SGD vs mini-batch)","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Optimization")
R("Hyperparameter tuning: grid, random, Bayesian - and doing it honestly","Classical-ML","Medium","Common","Conceptual","Either","Medium","Evaluation")
R("L1 vs L2 regularization","Classical-ML","Medium","Must-Know","Math","Either","Medium","Theory")
R("LLMs & RAG (Retrieval-Augmented Generation)","NLP-LLM","Medium","Must-Know","Conceptual","Either","Deep","RAG")
R("Linear regression from first principles (and its assumptions)","Classical-ML","Medium","Must-Know","Math","Either","Deep","Supervised")
R("Logistic regression - why not just use linear regression for classification?","Classical-ML","Medium","Must-Know","Math","Either","Medium","Supervised")
R("Loss functions - which to use when, and why the pairing matters","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Theory")
R("Naive Bayes - why 'naive' and why it works anyway","Classical-ML","Medium","Common","Math","Either","Medium","Supervised")
R("Neural network basics: from a perceptron to a multi-layer network","Deep-Learning","Easy","Must-Know","Conceptual","Either","Deep","Architectures")
R("Overfitting — what it is and how to prevent it","Classical-ML","Easy","Must-Know","Conceptual","Screen","Medium","Theory")
R("PCA - what it does, what it does not, and when to use it","Math-Stats","Medium","Must-Know","Math","Either","Medium","Linear-Algebra")
R("Precision vs Recall (and the 95%-accuracy trap)","Classical-ML","Easy","Must-Know","Conceptual","Screen","Medium","Evaluation")
R("ROC curve, AUC & choosing a threshold","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Evaluation")
R("ROC-AUC vs Precision-Recall Curves","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Evaluation")
R("SVM and the kernel trick, explained without the maths","Classical-ML","Medium","Common","Conceptual","Either","Medium","Supervised")
R("Supervised vs unsupervised vs semi-supervised vs self-supervised vs reinforcement learning","Classical-ML","Easy","Must-Know","Conceptual","Screen","Medium","Theory")
R("The Transformer & self-attention (the big one)","NLP-LLM","Hard","Must-Know","Conceptual","Either","Deep","Transformers")
R("The applied ML question: taking a model from notebook to production","MLOps","Medium","Common","Design","Onsite","Deep","Deployment")
R("What is an embedding?","NLP-LLM","Easy","Must-Know","Conceptual","Screen","Medium","Embeddings")
R("Why Residual (Skip) Connections Enable Very Deep Networks","Deep-Learning","Medium","Must-Know","Conceptual","Either","Medium","Architectures")
R("Why gradient-boosted trees still beat deep learning on tabular data","Classical-ML","Medium","Common","Conceptual","Either","Medium","Trees-Ensembles",
  "near-duplicate of the 'If deep learning is so powerful...' conceptual entry; kept under the no-drop rule")
R("k-Nearest Neighbours - the model that does no training at all","Classical-ML","Easy","Must-Know","Conceptual","Either","Medium","Supervised")
R("k-means clustering: how it works, how to pick k, and where it fails","Classical-ML","Medium","Must-Know","Conceptual","Either","Medium","Unsupervised")

# ═══════════════════════════════════════════════════════════════════════════
# ML CODING - implement-from-scratch.  FORMAT is Coding throughout.  These
# are the AI/SDE screen's answer to LeetCode, so the well-known ones are
# Must-Know and the long tail of numpy one-liners is Rare.
# ═══════════════════════════════════════════════════════════════════════════
R("Accuracy and confusion matrix (numpy)","Classical-ML","Easy","Common","Coding","Screen","Quick","Evaluation")
R("Adam optimizer update (numpy)","Deep-Learning","Medium","Common","Coding","Either","Medium","Optimization")
R("Batch Normalization forward (numpy)","Deep-Learning","Medium","Rare","Coding","Onsite","Medium","Regularization")
R("Confusion Matrix (from scratch)","Classical-ML","Easy","Common","Coding","Screen","Quick","Evaluation")
R("Confusion matrix from scratch","Classical-ML","Easy","Common","Coding","Screen","Quick","Evaluation",
  "near-duplicate of 'Confusion Matrix (from scratch)'; kept as-is under the no-drop rule")
R("Cosine Similarity (from scratch)","Math-Stats","Easy","Must-Know","Coding","Screen","Quick","Linear-Algebra")
R("Cosine similarity matrix (numpy)","Math-Stats","Medium","Common","Coding","Either","Medium","Linear-Algebra")
R("Cross-entropy loss (numpy)","Classical-ML","Medium","Must-Know","Coding","Either","Medium","Evaluation")
R("Dropout forward (numpy)","Deep-Learning","Medium","Common","Coding","Either","Quick","Regularization")
R("Euclidean distance matrix (numpy)","Math-Stats","Medium","Common","Coding","Either","Medium","Linear-Algebra")
R("Focal loss (numpy)","Deep-Learning","Medium","Rare","Coding","Onsite","Medium","Training")
R("Gaussian Naive Bayes (from scratch)","Classical-ML","Medium","Rare","Coding","Onsite","Deep","Supervised")
R("Gini, Entropy & Information Gain (from scratch)","Classical-ML","Medium","Common","Coding","Either","Medium","Trees-Ensembles")
R("Gradient clipping (numpy)","Deep-Learning","Easy","Rare","Coding","Screen","Quick","Training")
R("Gradient descent step (numpy)","Deep-Learning","Easy","Must-Know","Coding","Screen","Quick","Optimization")
R("He / Xavier weight initialization (numpy)","Deep-Learning","Medium","Rare","Coding","Onsite","Quick","Training")
R("Huber loss (numpy)","Classical-ML","Medium","Rare","Coding","Onsite","Quick","Supervised")
R("Implement K-Means clustering","Classical-ML","Medium","Must-Know","Coding","Either","Deep","Unsupervised")
R("Implement K-Nearest-Neighbors (from scratch)","Classical-ML","Medium","Must-Know","Coding","Either","Medium","Supervised")
R("Implement Logistic Regression with gradient descent","Classical-ML","Medium","Must-Know","Coding","Either","Deep","Supervised")
R("K-means assignment step (numpy)","Classical-ML","Medium","Common","Coding","Either","Medium","Unsupervised")
R("L2 regularization (ridge) loss and gradient (numpy)","Classical-ML","Medium","Common","Coding","Either","Medium","Theory")
R("LSTM cell forward pass (numpy)","Deep-Learning","Hard","Rare","Coding","Onsite","Deep","Sequence-Models")
R("Label smoothing (numpy)","Deep-Learning","Medium","Rare","Coding","Onsite","Quick","Regularization")
R("Layer Normalization (numpy)","Deep-Learning","Medium","Common","Coding","Either","Medium","Regularization")
R("Linear Regression via Gradient Descent","Classical-ML","Medium","Must-Know","Coding","Either","Deep","Supervised")
R("Logistic Regression prediction (from scratch)","Classical-ML","Easy","Common","Coding","Screen","Quick","Supervised")
R("MSE loss and its gradient (numpy)","Classical-ML","Easy","Must-Know","Coding","Screen","Quick","Evaluation")
R("Min-Max Scaler (from scratch)","Classical-ML","Easy","Rare","Coding","Screen","Quick","Feature-Engineering",
  "the concept is commonly asked; coding it from scratch rarely is")
R("Min-max scaling (numpy)","Classical-ML","Easy","Rare","Coding","Screen","Quick","Feature-Engineering",
  "near-duplicate of 'Min-Max Scaler (from scratch)'; kept as-is under the no-drop rule")
R("One-Hot Encoding (from scratch)","Classical-ML","Easy","Common","Coding","Screen","Quick","Feature-Engineering")
R("PCA via SVD (numpy)","Math-Stats","Hard","Common","Coding","Onsite","Deep","Linear-Algebra")
R("Precision, Recall & F1 (from scratch)","Classical-ML","Easy","Must-Know","Coding","Screen","Quick","Evaluation")
R("Precision, recall, F1 from a confusion matrix (numpy)","Classical-ML","Easy","Must-Know","Coding","Screen","Quick","Evaluation",
  "near-duplicate of 'Precision, Recall & F1 (from scratch)'; kept as-is under the no-drop rule")
R("R-squared (coefficient of determination) (numpy)","Math-Stats","Easy","Common","Coding","Screen","Quick","Statistics")
R("ROC AUC (rank-based, from scratch)","Classical-ML","Hard","Common","Coding","Onsite","Deep","Evaluation")
R("ReLU and its gradient (numpy)","Deep-Learning","Easy","Must-Know","Coding","Screen","Quick","Architectures")
R("SGD with momentum update (numpy)","Deep-Learning","Medium","Common","Coding","Either","Quick","Optimization")
R("Sigmoid and its gradient (numpy)","Deep-Learning","Easy","Must-Know","Coding","Screen","Quick","Architectures")
R("Sinusoidal positional encoding (numpy)","NLP-LLM","Hard","Rare","Coding","Onsite","Medium","Transformers")
R("Softmax (numerically stable)","Deep-Learning","Medium","Must-Know","Coding","Screen","Medium","Architectures")
R("Softmax + cross-entropy combined gradient (numpy)","Deep-Learning","Hard","Common","Coding","Onsite","Deep","Training")
R("Standardize features / z-score (numpy)","Classical-ML","Easy","Common","Coding","Screen","Quick","Feature-Engineering")
R("TF-IDF (from scratch)","NLP-LLM","Medium","Common","Coding","Either","Medium","Embeddings")
R("TF-IDF from scratch (numpy)","NLP-LLM","Medium","Common","Coding","Either","Medium","Embeddings",
  "near-duplicate of 'TF-IDF (from scratch)'; kept as-is under the no-drop rule")
R("Train-test split (numpy)","Classical-ML","Easy","Common","Coding","Screen","Quick","Evaluation")

# ═══════════════════════════════════════════════════════════════════════════
# CS FUNDAMENTALS - the OS/DBMS/networks/OOP round.  In Indian campus and
# new-grad loops this is asked far more heavily than most Western guides
# suggest, so the Must-Know share here is deliberately high.
# ═══════════════════════════════════════════════════════════════════════════
R("ACID transactions","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","DBMS")
R("Abstract class vs interface - and which to reach for","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","OOP")
R("Blocking vs non-blocking I/O, and how select/epoll enables 10,000 connections","Core-CS","Hard","Common","Conceptual","Onsite","Deep","OS")
R("CAP theorem","System-Design","Medium","Must-Know","Conceptual","Either","Medium","Fundamentals")
R("CPU cache, cache lines and locality of reference","Core-CS","Medium","Common","Conceptual","Onsite","Medium","OS")
R("CPU scheduling algorithms (FCFS, SJF, SRTF, Round Robin, Priority)","Core-CS","Medium","Must-Know","Conceptual","Either","Deep","OS")
R("Caching strategies","System-Design","Medium","Must-Know","Conceptual","Either","Medium","Scalability")
R("Compiler vs interpreter (and JIT)","Core-CS","Easy","Common","Conceptual","Either","Quick","Systems")
R("Context switch","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","OS")
R("DELETE vs TRUNCATE vs DROP (and soft deletes)","Core-CS","Easy","Common","Conceptual","Either","Quick","DBMS")
R("DNS resolution","Core-CS","Easy","Common","Conceptual","Either","Medium","Networking")
R("Database index (B-tree)","Core-CS","Medium","Must-Know","Conceptual","Either","Medium","DBMS")
R("Database keys: super, candidate, primary, composite, foreign, surrogate","Core-CS","Easy","Must-Know","Conceptual","Screen","Medium","DBMS")
R("Database normalization","Core-CS","Medium","Must-Know","Conceptual","Either","Medium","DBMS")
R("Deadlock and its four necessary conditions","Core-CS","Medium","Must-Know","Conceptual","Either","Medium","OS")
R("Garbage collection vs manual memory management","Core-CS","Medium","Common","Conceptual","Either","Medium","Systems")
R("HTTP in depth: methods, status codes, idempotency and REST","Core-CS","Medium","Must-Know","Conceptual","Either","Deep","Networking")
R("Handling deadlock: prevention, avoidance, detection - and Banker's algorithm","Core-CS","Hard","Common","Conceptual","Onsite","Deep","OS")
R("How a packet actually leaves your machine: ARP, DHCP, NAT and routing","Core-CS","Hard","Common","Conceptual","Onsite","Deep","Networking")
R("IEEE 754 floating point (and why 0.1 + 0.2 != 0.3)","Core-CS","Medium","Common","Conceptual","Either","Medium","Systems")
R("Load balancing","System-Design","Easy","Must-Know","Conceptual","Either","Medium","Fundamentals")
R("Multiple inheritance, the diamond problem, and Python's MRO","Python","Medium","Common","Conceptual","Either","Medium","Language")
R("Mutex vs semaphore (and the other lock types)","Core-CS","Medium","Must-Know","Conceptual","Either","Medium","OS")
R("Normalisation worked: taking one messy table to 3NF (and when to stop)","Core-CS","Medium","Must-Know","Conceptual","Either","Deep","DBMS")
R("OSI and TCP/IP models - what each layer actually does","Core-CS","Easy","Must-Know","Conceptual","Screen","Medium","Networking")
R("Overloading vs overriding (compile-time vs runtime polymorphism)","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","OOP")
R("Page fault, TLB and thrashing","Core-CS","Medium","Common","Conceptual","Either","Medium","OS")
R("Page replacement: FIFO, LRU, Optimal - and Belady's anomaly","Core-CS","Medium","Common","Conceptual","Either","Medium","OS")
R("Paging & virtual memory","Core-CS","Medium","Must-Know","Conceptual","Either","Medium","OS")
R("Paging vs segmentation, and internal vs external fragmentation","Core-CS","Medium","Common","Conceptual","Either","Medium","OS")
R("Process vs Thread (and why it matters)","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","OS")
R("Producer-consumer with a bounded buffer (and condition variables)","Core-CS","Medium","Common","Coding","Onsite","Deep","OS")
R("Python's GIL - what it actually stops, and what it does not","Python","Medium","Must-Know","Conceptual","Either","Medium","Language")
R("Race condition","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","OS")
R("Reading a query plan and fixing a slow query","Core-CS","Hard","Common","Debug","Onsite","Deep","DBMS")
R("Real-time on the web: polling vs long polling vs SSE vs WebSockets","Core-CS","Medium","Common","Conceptual","Onsite","Medium","Networking")
R("SQL JOINs - all of them, with one worked example","Core-CS","Easy","Must-Know","Coding","Screen","Medium","DBMS")
R("SQL vs NoSQL — how to choose","System-Design","Easy","Must-Know","Conceptual","Either","Medium","Storage")
R("SQL: WHERE vs GROUP BY vs HAVING, and window functions","Core-CS","Medium","Must-Know","Coding","Either","Deep","DBMS")
R("Shallow copy vs deep copy (and the aliasing bug behind it)","Python","Easy","Must-Know","Conceptual","Screen","Quick","Language")
R("Sharding vs Replication","System-Design","Medium","Must-Know","Conceptual","Either","Medium","Scalability")
R("Stack memory vs heap memory","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","OS")
R("System call, kernel space vs user space","Core-CS","Easy","Common","Conceptual","Either","Quick","OS")
R("TCP flow control vs congestion control (and why your download speeds up gradually)","Core-CS","Medium","Common","Conceptual","Either","Medium","Networking")
R("TCP three-way handshake","Core-CS","Easy","Must-Know","Conceptual","Screen","Quick","Networking")
R("TLS / HTTPS handshake","Core-CS","Medium","Common","Conceptual","Either","Medium","Networking")
R("The SQL queries you will actually be asked to write","Core-CS","Medium","Must-Know","Coding","Either","Deep","DBMS")
R("The four pillars of OOP, with one running example","Core-CS","Easy","Must-Know","Conceptual","Screen","Medium","OOP")
R("Transaction isolation levels and the anomalies they prevent","Core-CS","Hard","Common","Conceptual","Onsite","Deep","DBMS")
R("Two's complement and integer overflow","Core-CS","Medium","Common","Conceptual","Either","Medium","Systems")
R("Unicode, UTF-8 and character encoding","Core-CS","Medium","Common","Conceptual","Either","Medium","Systems")
R("What happens when you type a URL and press Enter?","Core-CS","Medium","Must-Know","Conceptual","Either","Deep","Networking")
R("fork(), exec(), and zombie vs orphan processes","Core-CS","Medium","Common","Conceptual","Either","Medium","OS")

# ═══════════════════════════════════════════════════════════════════════════
# AI / LLM - the fastest-moving category.  The core vocabulary is now
# Must-Know for an AI-flavoured new-grad role; the serving and
# research-adjacent depth (FlashAttention, GQA, RoPE scaling, speculative
# decoding) is genuinely Rare at this level however fashionable it is.
# ═══════════════════════════════════════════════════════════════════════════
R("Active learning (label the most useful examples)","Classical-ML","Medium","Rare","Conceptual","Onsite","Medium","Theory")
R("Catastrophic forgetting (and how fine-tuning can hurt)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Fine-Tuning")
R("Chain-of-Thought and reasoning models","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Prompting")
R("Contextual retrieval and better chunk context","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","RAG")
R("Cosine similarity vs dot product vs Euclidean distance","Math-Stats","Medium","Must-Know","Math","Either","Medium","Linear-Algebra")
R("DPO vs PPO (aligning LLMs to human preferences)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Deep","Fine-Tuning")
R("Data contamination in LLM benchmarks","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Evaluation")
R("Diffusion models (how AI generates images)","Deep-Learning","Hard","Rare","Conceptual","Onsite","Medium","Architectures")
R("Embedding model fine-tuning for your domain","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Embeddings")
R("Encoder vs Decoder vs Encoder-Decoder transformers","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("FlashAttention (memory-efficient attention)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Inference")
R("GPU memory math for serving LLMs","NLP-LLM","Hard","Rare","Math","Onsite","Medium","Inference")
R("GraphRAG (retrieval over a knowledge graph)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","RAG")
R("Grouped-Query Attention (GQA) and Multi-Query Attention","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Inference")
R("Guardrail frameworks (Llama Guard, NeMo Guardrails)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Evaluation")
R("HNSW (how vector databases search fast)","NLP-LLM","Hard","Common","Conceptual","Onsite","Medium","Embeddings")
R("Hallucination detection methods","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Evaluation")
R("Hard-negative mining for embedding models","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Embeddings")
R("How does self-attention work (the Transformer core)?","NLP-LLM","Hard","Must-Know","Conceptual","Either","Deep","Transformers")
R("Hybrid search (keyword + vector) and re-ranking","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","RAG")
R("KV-cache (why LLM generation speeds up after the first token)","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Inference")
R("LLM red-teaming (stress-testing for safety)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Evaluation")
R("Mixture-of-Experts (MoE) models","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Transformers")
R("Model cards and responsible model documentation","MLOps","Easy","Rare","Conceptual","Onsite","Quick","Monitoring")
R("Multimodal models and CLIP","Deep-Learning","Medium","Common","Conceptual","Either","Medium","Architectures")
R("Positional encoding (how transformers know word order)","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Pretraining vs Fine-tuning vs Prompting (how to adapt an LLM)","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Fine-Tuning")
R("Prompt caching (reuse a fixed prefix cheaply)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Quick","Inference")
R("Prompt engineering patterns that actually work","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Prompting")
R("Prompt injection and how to defend against it","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Prompting")
R("Quantization (shrinking models for cheaper inference)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Inference",
  "rising fast for inference-flavoured roles; still Rare at the new-grad bar")
R("Reranker cross-encoders (precision after retrieval)","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","RAG")
R("RoPE scaling and extending context length","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Transformers")
R("Sliding-window and sparse attention (long context cheaply)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Inference")
R("Speculative decoding (faster LLM generation)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Inference")
R("Structured output / JSON mode from LLMs","NLP-LLM","Easy","Common","Conceptual","Either","Quick","Prompting")
R("Synthetic data generation for training","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Fine-Tuning")
R("Temperature, top-k and top-p (controlling LLM output)","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Inference")
R("Tokenization and Byte-Pair Encoding (BPE)","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Transformers")
R("Vector database & semantic search","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","RAG")
R("What is MCP (Model Context Protocol)?","NLP-LLM","Medium","Common","Conceptual","Either","Medium","Agents")
R("What is RAG (Retrieval-Augmented Generation)?","NLP-LLM","Easy","Must-Know","Conceptual","Screen","Medium","RAG")
R("What is RLHF (Reinforcement Learning from Human Feedback)?","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Fine-Tuning")
R("What is a Large Language Model (LLM)?","NLP-LLM","Easy","Must-Know","Conceptual","Screen","Quick","Transformers")
R("What is fine-tuning with LoRA (parameter-efficient tuning)?","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Fine-Tuning")
R("What is the context window, and why does it matter?","NLP-LLM","Easy","Must-Know","Conceptual","Screen","Quick","Transformers")
R("Why do LLMs hallucinate, and how do you reduce it?","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","Evaluation")

# ═══════════════════════════════════════════════════════════════════════════
# AI APPLIED - mostly "design an X" prompts.  FORMAT is Design for those, and
# STAGE is Onsite: nobody asks you to design a RAG pipeline in a 30-minute
# screen.  PRIORITY is mostly Common rather than Must-Know because WHICH
# system you are asked to design is a lottery - the shape is what transfers.
# ═══════════════════════════════════════════════════════════════════════════
R("A/B testing an ML / LLM feature","Math-Stats","Medium","Common","Conceptual","Onsite","Medium","Statistics")
R("Agent memory (short-term vs long-term)","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Agents")
R("Agentic RAG (retrieval as a tool the model controls)","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Agents")
R("Cold-start problem in ML systems","System-Design","Medium","Common","Conceptual","Onsite","Medium","ML-System-Design")
R("Content moderation with LLMs","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Continuous batching (serving many LLM requests)","NLP-LLM","Hard","Rare","Conceptual","Onsite","Medium","Inference")
R("Data drift and model monitoring in production","MLOps","Medium","Must-Know","Conceptual","Onsite","Medium","Monitoring")
R("Design a RAG-powered document Q&A chatbot","System-Design","Medium","Must-Know","Design","Onsite","Deep","ML-System-Design")
R("Design a SQL data-analysis agent","System-Design","Hard","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a churn prediction system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a customer-support copilot","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a document classification system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a meeting-notes summarizer","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a natural-language-to-SQL system","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a resume screening system (and its bias risks)","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a sentiment analysis system at scale","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a time-series forecasting system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a translation / localization pipeline","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design an AI coding assistant (Copilot-style)","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design")
R("Design an AI tutor","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design an anomaly detection system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design an enterprise AI search assistant","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design an invoice / document extraction pipeline","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Embeddings for recommendation systems","System-Design","Medium","Common","Conceptual","Onsite","Medium","ML-System-Design")
R("Feature stores (online vs offline features)","MLOps","Medium","Common","Conceptual","Onsite","Medium","Pipelines")
R("Function calling / tool use in LLMs","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Agents")
R("Guardrails and safety for LLM products","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Evaluation")
R("How do you evaluate an LLM / GenAI system?","NLP-LLM","Medium","Must-Know","Conceptual","Either","Deep","Evaluation")
R("Human evaluation and inter-annotator agreement","Classical-ML","Medium","Rare","Conceptual","Onsite","Medium","Evaluation")
R("Knowledge distillation (small models from big ones)","Deep-Learning","Medium","Common","Conceptual","Onsite","Medium","Training")
R("LLM cost and latency optimization","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Inference")
R("LLM observability and tracing","MLOps","Medium","Rare","Conceptual","Onsite","Medium","Monitoring")
R("Multi-agent systems (when many LLMs collaborate)","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Agents")
R("Named-entity recognition and extraction at scale","NLP-LLM","Medium","Rare","Design","Onsite","Deep","Evaluation")
R("PII redaction for LLM pipelines","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","RAG")
R("Query rewriting and HyDE for better retrieval","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","RAG")
R("RAG chunking strategies (how to split documents)","NLP-LLM","Medium","Must-Know","Conceptual","Either","Medium","RAG")
R("RAG evaluation with golden sets and regression testing","NLP-LLM","Medium","Common","Conceptual","Onsite","Medium","Evaluation")
R("RAGAS and RAG evaluation metrics","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Evaluation")
R("Recent AI trends every candidate should know (2024-2025)","NLP-LLM","Easy","Common","Conceptual","Either","Medium","Agents")
R("Semantic caching for LLM apps","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Inference")
R("Shadow deployment and canary for ML models","MLOps","Medium","Common","Conceptual","Onsite","Medium","Deployment")
R("Tool-calling errors and retries in agents","NLP-LLM","Medium","Rare","Conceptual","Onsite","Medium","Agents")
R("What is an AI agent (tool use & the ReAct loop)?","NLP-LLM","Easy","Must-Know","Conceptual","Either","Medium","Agents")

# ═══════════════════════════════════════════════════════════════════════════
# LLD / OOP DESIGN.  TOPIC has no LLD value, so these carry Core-CS with the
# OOP subtopic - flagged once here rather than on all 31 rows.  Amazon runs an
# explicit OOD round, which is why the framework and the headline patterns are
# Must-Know while the more obscure worked prompts are Rare.
# ═══════════════════════════════════════════════════════════════════════════
_LLD = "no LLD/OOD value in the TOPIC vocabulary; Core-CS + the OOP subtopic is the closest fit"

R("Composition over inheritance - why 'is-a' keeps failing","Core-CS","Medium","Must-Know","Conceptual","Either","Medium","OOP", _LLD)
R("How to drive a low-level design (LLD) interview","Core-CS","Medium","Must-Know","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design Snake and Ladder (and what it really tests)","Core-CS","Medium","Rare","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design Splitwise (shared expense settlement)","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design Tic-Tac-Toe (and generalise it to N x N)","Core-CS","Easy","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Deck of Cards / Blackjack","Core-CS","Easy","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Library Management system","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Logging framework","Core-CS","Medium","Rare","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Movie Ticket Booking system (BookMyShow)","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Notification service (email, SMS, push)","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Parking Lot","Core-CS","Medium","Must-Know","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Rate Limiter","Core-CS","Medium","Must-Know","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design a Vending Machine (the state-machine question)","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design an ATM","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design an Elevator system","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design an e-commerce Order and Inventory model","Core-CS","Medium","Rare","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design an in-memory File System","Core-CS","Hard","Rare","Design","Onsite","Deep","OOP", _LLD)
R("LLD: Design an in-memory Key-Value store with TTL (a mini Redis)","Core-CS","Medium","Common","Design","Onsite","Deep","OOP", _LLD)
R("Pattern: Adapter - make an incompatible class fit your interface","Core-CS","Easy","Common","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: Builder - constructing an object with many optional parts","Core-CS","Easy","Common","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: Command - turn an action into an object (and get undo free)","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","OOP", _LLD)
R("Pattern: Decorator - add behaviour without touching the class","Core-CS","Medium","Common","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: Factory and Factory Method - centralise object creation","Core-CS","Easy","Must-Know","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: Observer - publish/subscribe inside one process","Core-CS","Easy","Must-Know","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: Repository / DAO - keep storage out of your business logic","Core-CS","Medium","Rare","Conceptual","Onsite","Quick","OOP", _LLD)
R("Pattern: Singleton - and why interviewers are suspicious of it","Core-CS","Easy","Must-Know","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: State - when an object's behaviour depends on its mode","Core-CS","Medium","Common","Conceptual","Either","Quick","OOP", _LLD)
R("Pattern: Strategy - swap an algorithm at runtime","Core-CS","Easy","Must-Know","Conceptual","Either","Quick","OOP", _LLD)
R("SOLID principles - all five, each with the bug it prevents","Core-CS","Medium","Must-Know","Conceptual","Either","Deep","OOP", _LLD)
R("UML relationships you actually need: association, aggregation, composition, inheritance","Core-CS","Easy","Common","Conceptual","Either","Medium","OOP", _LLD)
R("Writing thread-safe classes for an LLD round","Core-CS","Hard","Common","Coding","Onsite","Deep","OOP", _LLD)

# ═══════════════════════════════════════════════════════════════════════════
# BEHAVIORAL.  All Behavioral/Behavioral/Either.  The behavioural round is
# guaranteed, so the framework and the core stories are Must-Know; the
# narrower Amazon LPs are Common because you get four or five, not all of
# them.  TIME is Medium throughout - a STAR answer is a two-to-three minute
# spoken piece, not a quick fact and not a deep derivation.
# ═══════════════════════════════════════════════════════════════════════════
R("'Why this company / why you?'","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Story-Bank")
R("Building a story bank: six stories that cover thirty questions","Behavioral","Medium","Must-Know","Behavioral","Either","Deep","Story-Bank")
R("How do you handle a group project where someone is not pulling their weight?","Behavioral","Easy","Common","Behavioral","Either","Medium","Googleyness")
R("How do you handle competing priorities and deadlines?","Behavioral","Easy","Common","Behavioral","Either","Medium","Story-Bank")
R("STAR method + a strong student example","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Story-Bank")
R("STAR: Acting decisively with incomplete information (Bias for Action)","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Being frugal / doing more with less (Frugality)","Behavioral","Easy","Rare","Behavioral","Onsite","Medium","Amazon-LP")
R("STAR: Customer obsession -- starting from the customer and working backward","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Delivering under a hard deadline with scope trade-offs (Deliver Results / Bias for Action)","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Disagreeing with a decision then fully committing (Have Backbone; Disagree and Commit)","Behavioral","Medium","Must-Know","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Diving deep to find a root cause others missed (Dive Deep)","Behavioral","Medium","Common","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Earning trust after a mistake / owning an incident (Earn Trust / Ownership)","Behavioral","Medium","Must-Know","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Insisting on the right long-term solution over a quick hack (Are Right, A Lot / Insist on Highest Standards)","Behavioral","Medium","Common","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Learning something hard and outside your expertise fast (Learn and Be Curious)","Behavioral","Easy","Common","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Raising the bar on hiring or quality (Hire and Develop the Best / Insist on Highest Standards)","Behavioral","Medium","Rare","Behavioral","Onsite","Medium","Amazon-LP",
  "a hiring-bar story is hard for a new grad to have; asked more of experienced candidates")
R("STAR: Simplifying/inventing to remove a bottleneck (Invent and Simplify)","Behavioral","Medium","Common","Behavioral","Either","Medium","Amazon-LP")
R("STAR: Thinking big and influencing beyond your team (Think Big)","Behavioral","Medium","Rare","Behavioral","Onsite","Medium","Amazon-LP",
  "Think Big is weighted towards senior loops; a new grad is rarely pressed on it")
R("Tell me about a time you changed your mind because of evidence","Behavioral","Easy","Common","Behavioral","Either","Medium","Story-Bank")
R("Tell me about a time you dealt with ambiguity or unclear requirements","Behavioral","Medium","Must-Know","Behavioral","Either","Medium","Googleyness")
R("Tell me about a time you helped a teammate succeed","Behavioral","Easy","Common","Behavioral","Either","Medium","Googleyness")
R("Tell me about a time you led without authority","Behavioral","Medium","Common","Behavioral","Either","Medium","Googleyness")
R("Tell me about a time you made a mistake that affected other people","Behavioral","Medium","Must-Know","Behavioral","Either","Medium","Story-Bank")
R("Tell me about a time you received difficult feedback (behavioral: feedback)","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Story-Bank")
R("Tell me about a time you worked with someone difficult (collaboration)","Behavioral","Easy","Must-Know","Behavioral","Either","Medium","Googleyness")
R("Tell me about your biggest failure and what you learned (behavioral: failure)","Behavioral","Medium","Must-Know","Behavioral","Either","Medium","Story-Bank")
R("Tell me about your most challenging technical project (and how to go deep)","Behavioral","Medium","Must-Know","Behavioral","Either","Deep","Story-Bank")
R("Tell me about yourself / walk me through your resume (the two-minute answer)","Behavioral","Easy","Must-Know","Behavioral","Screen","Medium","Story-Bank")
R("What 'Googleyness' actually means, and how to show it","Behavioral","Easy","Common","Behavioral","Either","Medium","Googleyness")
R("What questions should you ask the interviewer?","Behavioral","Easy","Must-Know","Behavioral","Either","Quick","Process")
R("Why software engineering, and why AI/ML specifically?","Behavioral","Easy","Must-Know","Behavioral","Screen","Medium","Story-Bank")

# ═══════════════════════════════════════════════════════════════════════════
# ML SYSTEM DESIGN.  Onsite/Design/Deep throughout.  PRIORITY is mostly Rare
# for the specific systems: a new grad is seldom given a full ML design round,
# and WHICH system comes up is a lottery.  The FRAMEWORK is the exception and
# is the one thing here worth committing to memory.
# ═══════════════════════════════════════════════════════════════════════════
R("Design a Churn Prediction system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Content Moderation / Toxicity system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Customer Lifetime Value (LTV) prediction system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Demand Forecasting system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Dynamic Pricing system","System-Design","Hard","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Feature Store","System-Design","Hard","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Fraud / Payment-Risk Detection system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a Fraud Detection System","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design",
  "near-duplicate of 'Design a Fraud / Payment-Risk Detection system'; kept under the no-drop rule")
R("Design a Lead Scoring system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Near-Duplicate Detection system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a News Feed Ranking system","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a Query Autocomplete (typeahead) system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a Real-Time Bidding (RTB) system","System-Design","Hard","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Search Ranking system","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a Session-based Recommendation system","System-Design","Hard","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Similar-items / Related-products system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a Spam / Abuse Detection system","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a Trending / Hot-content ranking system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a Video Recommendation system (YouTube-style)","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design")
R("Design a YouTube-style Video Recommendation System","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design",
  "near-duplicate of 'Design a Video Recommendation system (YouTube-style)'; kept under the no-drop rule")
R("Design a large-scale Image Classification pipeline","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design a recommendation system (worked example)","System-Design","Medium","Must-Know","Design","Onsite","Deep","ML-System-Design")
R("Design an A/B Testing (experimentation) platform","System-Design","Hard","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design an Ad Click-Through-Rate (CTR) Prediction System","System-Design","Hard","Common","Design","Onsite","Deep","ML-System-Design")
R("Design an Anomaly Detection service","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design an ETA Prediction system","System-Design","Medium","Rare","Design","Onsite","Deep","ML-System-Design")
R("Design an LLM Chatbot with RAG","System-Design","Medium","Must-Know","Design","Onsite","Deep","ML-System-Design")
R("Design for Recommendation Cold-Start","System-Design","Medium","Common","Design","Onsite","Deep","ML-System-Design")
R("The ML system design framework (6 steps)","System-Design","Medium","Must-Know","Design","Onsite","Deep","ML-System-Design")

# ═══════════════════════════════════════════════════════════════════════════
# MINDSET / COMPANY PROCESS.  Not questions at all - study strategy and
# process briefings - so every column is a best-fit and each row is flagged.
# ═══════════════════════════════════════════════════════════════════════════
_META = "study-strategy / process briefing, not an interview question - all six columns are a best fit"

R("A realistic study plan and the '70% rule'","Behavioral","Easy","Rare","Conceptual","Either","Medium","Process", _META)
R("How should I approach a coding interview (out loud)?","Behavioral","Easy","Must-Know","Conceptual","Either","Medium","Process", _META)
R("Amazon: Leadership Principles & the Loop","Behavioral","Easy","Must-Know","Conceptual","Either","Deep","Process", _META)
R("Google: process, Googleyness & the committee","Behavioral","Easy","Common","Conceptual","Either","Medium","Process", _META)
