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
