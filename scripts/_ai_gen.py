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
    dict(cat="dsa", title="Minimum Depth of Binary Tree",
         answer="The minimum depth is the number of nodes on the SHORTEST root-to-LEAF path. BFS level-by-level and return the depth of the first LEAF you encounter — BFS reaches the shallowest leaf first, so it's optimal (and avoids the DFS pitfall of a node with one missing child).",
         tags=["minimum-depth","bfs","binary-tree","dsa"],
         code='''# Minimum depth: shortest root-to-LEAF path length (number of nodes).
from collections import deque
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def min_depth(root):
    if root is None:
        return 0
    queue = deque([(root, 1)])
    while queue:
        node, depth = queue.popleft()
        if node.left is None and node.right is None:
            return depth              # first leaf reached (BFS) = min depth
        if node.left: queue.append((node.left, depth + 1))
        if node.right: queue.append((node.right, depth + 1))
    return 0''',
         complexity="Time O(n), space O(n).",
         pitfalls="Using naive DFS min(left,right)+1 (a node with one child isn't a leaf); off-by-one on depth.",
         example="For tree 3 -> (9, 20 -> (15, 7)), min_depth -> 2."),
    dict(cat="dsa", title="Average of Levels in Binary Tree",
         answer="Return the average value of the nodes on each level. Standard BFS by levels: process all nodes currently in the queue (one level), sum their values, divide by the level's node count, and enqueue their children for the next level.",
         tags=["average-of-levels","bfs","binary-tree","level-order","dsa"],
         code='''# Average value of the nodes on each level of a binary tree.
from collections import deque
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def average_of_levels(root):
    result = []
    queue = deque([root])
    while queue:
        n = len(queue)
        level_sum = 0
        for _ in range(n):
            node = queue.popleft()
            level_sum += node.val
            if node.left: queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level_sum / n)     # mean of this level
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Fixing the level count after mutating the queue; integer instead of float division.",
         example="For [3,9,20,null,null,15,7], average_of_levels -> [3.0, 14.5, 11.0]."),
    dict(cat="dsa", title="Sum of Left Leaves",
         answer="Sum the values of all LEFT leaves — leaves that are the LEFT child of their parent. Recurse: whenever a node's left child exists and is itself a leaf, add its value; then recurse into both subtrees.",
         tags=["sum-left-leaves","binary-tree","recursion","dfs","dsa"],
         code='''# Sum of all LEFT leaves (leaves that are a left child).
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def sum_of_left_leaves(root):
    if root is None:
        return 0
    total = 0
    if root.left and root.left.left is None and root.left.right is None:
        total += root.left.val          # a left child that is a leaf
    total += sum_of_left_leaves(root.left)
    total += sum_of_left_leaves(root.right)
    return total''',
         complexity="Time O(n), space O(h).",
         pitfalls="Counting any leaf (must be a LEFT child); missing the leaf check on the left child.",
         example="For 3 -> (9, 20 -> (15, 7)), sum_of_left_leaves -> 24 (9 + 15)."),
    dict(cat="dsa", title="Path Sum III (prefix sum)",
         answer="Count the downward paths (any node to any descendant) whose values sum to a target. Use a running prefix sum with a hash map of prefix-sum counts: at each node the number of valid paths ending here is how many earlier prefix sums equal (running - target). Backtrack the map on the way up.",
         tags=["path-sum","prefix-sum","binary-tree","hash-map","dfs","dsa"],
         code='''# Count root-to-any downward paths summing to target (prefix-sum hashmap).
from collections import defaultdict
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def path_sum_iii(root, target):
    prefix = defaultdict(int)
    prefix[0] = 1                        # the empty prefix
    def dfs(node, running):
        if node is None:
            return 0
        running += node.val
        count = prefix[running - target] # paths ending here summing to target
        prefix[running] += 1
        count += dfs(node.left, running) + dfs(node.right, running)
        prefix[running] -= 1             # backtrack: leave this path
        return count
    return dfs(root, 0)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Not backtracking the prefix map (over-counts across branches); forgetting prefix[0]=1.",
         example="For [10,5,-3,3,2,null,11,3,-2,null,1], path_sum_iii(root, 8) -> 3."),
    dict(cat="dsa", title="Two Sum IV - Input is a BST",
         answer="Determine if a BST contains two distinct elements summing to k. Traverse and keep a SET of seen values; at each node, if k minus the node's value is already in the set, return True. (You could also do a two-pointer walk over the in-order sorted values.)",
         tags=["two-sum-bst","bst","hash-set","dfs","dsa"],
         code='''# Does the BST contain two elements summing to k? (seen-set traversal)
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def find_target(root, k):
    seen = set()
    def dfs(node):
        if node is None:
            return False
        if k - node.val in seen:
            return True                  # complement already seen
        seen.add(node.val)
        return dfs(node.left) or dfs(node.right)
    return dfs(root)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Using the same node twice (the set holds only previously visited nodes); ignoring the BST order that enables a two-pointer variant.",
         example="For a BST holding {2,3,4,5,6,7}, find_target(root, 9) -> True (2+7 or 3+6)."),
    dict(cat="dsa", title="Minimum Absolute Difference in BST",
         answer="Find the minimum absolute difference between any two node values in a BST. An IN-ORDER traversal visits values in sorted order, so the answer is the smallest gap between ADJACENT in-order values — track the previous value and update the best difference.",
         tags=["min-abs-diff-bst","bst","in-order","dsa"],
         code='''# Minimum absolute difference between any two node values in a BST.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val; self.left = left; self.right = right

def min_diff_in_bst(root):
    prev = None
    best = float('inf')
    def inorder(node):
        nonlocal prev, best
        if node is None:
            return
        inorder(node.left)
        if prev is not None:
            best = min(best, node.val - prev)   # sorted -> adjacent gap
        prev = node.val
        inorder(node.right)
    inorder(root)
    return best''',
         complexity="Time O(n), space O(h).",
         pitfalls="Comparing all pairs (O(n^2)); not using in-order sorted order.",
         example="For BST 4 -> (2 -> (1,3), 6), min_diff_in_bst -> 1."),
    dict(cat="dsa", title="Middle of the Linked List",
         answer="Return the middle node (the SECOND middle if the length is even). Fast/slow pointers: advance slow by one and fast by two; when fast reaches the end, slow is at the middle — a single pass with no length precomputation.",
         tags=["middle-linked-list","fast-slow-pointers","linked-list","dsa"],
         code='''# The middle node of a linked list (second middle if even length).
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def middle_node(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next            # one step
        fast = fast.next.next       # two steps
    return slow                     # slow lands on the middle''',
         complexity="Time O(n), space O(1).",
         pitfalls="Off-by-one on even length (this returns the second middle); wrong loop condition.",
         example="1->2->3->4->5 returns node 3; 1->2->3->4->5->6 returns node 4."),
    dict(cat="dsa", title="Remove Nth Node From End of List",
         answer="Remove the nth node from the end in ONE pass. Use a dummy head and two pointers: advance fast n steps ahead, then move both until fast hits the end — slow now sits just BEFORE the target, so relink to skip it. The dummy handles removing the head.",
         tags=["remove-nth-from-end","two-pointers","linked-list","dummy-node","dsa"],
         code='''# Remove the nth node from the END of a list in one pass (two pointers).
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val; self.next = next

def remove_nth_from_end(head, n):
    dummy = ListNode(0, head)
    fast = slow = dummy
    for _ in range(n):
        fast = fast.next            # advance fast n steps ahead
    while fast.next:
        fast = fast.next
        slow = slow.next            # slow stops just before the target
    slow.next = slow.next.next      # unlink the nth-from-end node
    return dummy.next''',
         complexity="Time O(n), space O(1).",
         pitfalls="Not using a dummy (removing the head breaks); off-by-one in the n-step advance.",
         example="1->2->3->4->5 with n=2 -> 1->2->3->5."),
    dict(cat="glossary", title="Chaos engineering",
         answer="The practice of deliberately INJECTING failures into a production (or prod-like) system — killing servers, adding latency, dropping network — to proactively find weaknesses BEFORE they cause real outages. Pioneered by Netflix's Chaos Monkey: form a hypothesis ('the system stays up if a node dies'), run a controlled experiment, and fix what breaks. It builds real confidence in resilience.",
         tags=["chaos-engineering","resilience","reliability","testing","sre"],
         example="Chaos Monkey randomly terminates production instances during business hours; if a service can't survive losing one, the team finds and fixes the single point of failure before a real crash does."),
    dict(cat="glossary", title="LSM internals (memtable, SSTable, compaction)",
         answer="How a log-structured merge tree stores data. Writes go to an in-memory sorted MEMTABLE plus a WAL; when it fills, it's flushed to an immutable, sorted on-disk SSTABLE. Reads probe SSTables newest-first (with Bloom filters). Background COMPACTION merges SSTables, discarding overwritten/deleted entries — reclaiming space and keeping reads fast. Writes are sequential (fast) at the cost of read/space amplification.",
         tags=["lsm","memtable","sstable","compaction","storage-engine"],
         example="In RocksDB/Cassandra, a burst of writes fills the memtable, flushes to an SSTable, and later compaction merges many SSTables into fewer sorted files so reads needn't check dozens of them."),
    dict(cat="glossary", title="Tombstone (deletes)",
         answer="A marker that records a DELETE in append-only/LSM and distributed stores, instead of physically removing the data (impossible in immutable files, and it would resurrect on replica sync). Reads treat a tombstoned key as absent; compaction/GC purges the data and tombstone after a grace period longer than max replica downtime. Too many tombstones slow reads.",
         tags=["tombstone","deletes","lsm","replication","compaction"],
         example="Deleting a row in Cassandra writes a tombstone; a replica that missed the delete learns of it via the tombstone during repair, so the row can't resurrect — then compaction purges both after the grace period."),
    dict(cat="glossary", title="Write / read / space amplification",
         answer="Overhead ratios of a storage engine. WRITE amplification = bytes written to disk vs bytes of user data (LSM compaction rewrites data repeatedly -> high). READ amplification = disk reads per query (an LSM read may probe several SSTables -> higher than a B-tree). SPACE amplification = disk used vs live data (stale versions before compaction). Engines and compaction strategies trade these off.",
         tags=["write-amplification","read-amplification","space-amplification","lsm","storage-engine"],
         example="An LSM tree ingests fast but has high write amplification because compaction rewrites the same data across levels; a B-tree has lower read amplification but higher write amplification from in-place page updates."),
    dict(cat="glossary", title="Hot partition",
         answer="When one shard/partition receives a DISPROPORTIONATE share of traffic (a celebrity user, a popular key, a monotonically increasing timestamp key), overloading a single node while others idle — a scalability killer despite 'horizontal scaling'. Fix by choosing a high-cardinality, evenly-distributed partition key, salting hot keys with a hash/random suffix, or splitting the hot partition.",
         tags=["hot-partition","sharding","skew","scalability","partition-key"],
         example="Partitioning events by day makes today's partition a hot spot (all writes land there); partitioning by hash(user_id) or salting the key spreads writes evenly across nodes."),
    dict(cat="conceptual", title="Why do LSM/append-only stores delete with tombstones instead of removing the data?",
         answer="Because their on-disk files are IMMUTABLE (append-only) — you can't edit an SSTable in place to erase a key. And in a distributed, replicated store, physically deleting on one replica isn't enough: a replica that was down during the delete would, via anti-entropy/read-repair, see the key still present elsewhere and RESURRECT it. A tombstone is an explicit 'deleted as of time T' record that is itself an append (fits the immutable model), propagates to replicas so all agree it's gone, and shadows older values on reads. Compaction later physically drops the data AND the tombstone — but only after a grace period longer than max replica downtime, so a lagging replica still learns of the delete first. The cost: many tombstones slow reads until compaction cleans them.",
         tags=["tombstone","lsm","deletes","replication","why"],
         example="Delete a key in Cassandra: a tombstone is written and replicated; a replica that missed it learns of the delete via the tombstone during repair (so the row doesn't come back), then compaction purges both after gc_grace_seconds."),
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
