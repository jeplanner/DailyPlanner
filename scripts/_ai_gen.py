"""Prompt-free batch generator for ai_sde_bank.py.

Runs as a single simple command (`python3 scripts/_ai_gen.py`) so the
permission parser can allow it -- no heredocs, pipes, or && chains.
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
    dict(cat="dsa", title="Diameter of Binary Tree",
         answer="The diameter is the longest path (in edges) between any two nodes, which may not pass through the root. Bottom-up DFS returns each node's height while updating a running best = left_height + right_height (edges through that node).",
         tags=["diameter-binary-tree","tree","dfs","height","dsa"],
         code='''# Longest path (edges) between any two nodes in a binary tree.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def diameter_of_binary_tree(root):
    best = [0]
    def height(node):
        if node is None:
            return 0
        lh = height(node.left)
        rh = height(node.right)
        best[0] = max(best[0], lh + rh)      # path through this node (edges)
        return 1 + max(lh, rh)
    height(root)
    return best[0]''',
         complexity="Time O(n), space O(h).",
         pitfalls="Counting nodes instead of edges; assuming the diameter passes through the root.",
         example="diameter_of_binary_tree(Node(1, Node(2, Node(4), Node(5)), Node(3))) -> 3."),
    dict(cat="dsa", title="Sum of Left Leaves",
         answer="Sum the values of all LEFT leaves (a left child that has no children). DFS carrying a flag for whether the current node is a left child; add its value if it is a leaf.",
         tags=["sum-left-leaves","tree","dfs","recursion","dsa"],
         code='''# Sum values of all left leaves in a binary tree.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def sum_of_left_leaves(root):
    def dfs(node, is_left):
        if node is None:
            return 0
        if node.left is None and node.right is None:
            return node.val if is_left else 0    # count only left leaves
        return dfs(node.left, True) + dfs(node.right, False)
    return dfs(root, False)''',
         complexity="Time O(n), space O(h).",
         pitfalls="Counting all leaves (must be left children); treating a left internal node as a leaf.",
         example="sum_of_left_leaves(Node(3, Node(9), Node(20, Node(15), Node(7)))) -> 24  (9 + 15)."),
    dict(cat="dsa", title="Path Sum (root to leaf)",
         answer="Determine if any root-to-leaf path sums to a target. DFS subtracting each node's value; at a leaf, success iff the remaining target equals the leaf value.",
         tags=["path-sum","tree","dfs","recursion","dsa"],
         code='''# True if some root-to-leaf path sums to target.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def has_path_sum(root, target):
    if root is None:
        return False
    if root.left is None and root.right is None:
        return target == root.val            # leaf: check remaining target
    remaining = target - root.val
    return has_path_sum(root.left, remaining) or has_path_sum(root.right, remaining)''',
         complexity="Time O(n), space O(h).",
         pitfalls="Returning True at a null child (over-counts); not requiring a LEAF (path must end at a leaf).",
         example="has_path_sum(Node(5, Node(4, Node(11, Node(7), Node(2))), Node(8)), 22) -> True."),
    dict(cat="dsa", title="Minimum Depth of Binary Tree",
         answer="The minimum depth is the fewest nodes from root to the NEAREST leaf. Careful: a node with only one child is not a leaf, so take the child's depth (not min with 0). BFS finds the first leaf fastest.",
         tags=["min-depth-tree","tree","bfs","dfs","dsa"],
         code='''# Minimum root-to-leaf depth (nodes) of a binary tree.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def min_depth(root):
    if root is None:
        return 0
    if root.left is None:
        return 1 + min_depth(root.right)     # only right subtree exists
    if root.right is None:
        return 1 + min_depth(root.left)      # only left subtree exists
    return 1 + min(min_depth(root.left), min_depth(root.right))''',
         complexity="Time O(n), space O(h).",
         pitfalls="Using min(left,right) blindly counts a missing child as depth 0 (wrong); a single-child node is not a leaf.",
         example="min_depth(Node(2, None, Node(3, None, Node(4)))) -> 3."),
    dict(cat="dsa", title="Merge Two Binary Trees",
         answer="Overlay two trees: where both nodes exist, sum values; otherwise take whichever exists. Recurse on both children.",
         tags=["merge-binary-trees","tree","recursion","dfs","dsa"],
         code='''# Merge two binary trees by summing overlapping nodes.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def merge_trees(t1, t2):
    if t1 is None:
        return t2
    if t2 is None:
        return t1
    merged = Node(t1.val + t2.val)           # overlap: sum the values
    merged.left = merge_trees(t1.left, t2.left)
    merged.right = merge_trees(t1.right, t2.right)
    return merged

def preorder(node):
    if node is None:
        return []
    return [node.val] + preorder(node.left) + preorder(node.right)''',
         complexity="Time O(min(n1, n2)), space O(h).",
         pitfalls="Returning None when one side is null (should return the other); mutating inputs unintentionally.",
         example="merge of [1,3,2] and [2,1,3] has preorder [3,4,5] at the roots/children overlap."),
    dict(cat="dsa", title="Range Sum of BST",
         answer="Sum values in a BST within [low, high]. Exploit the BST order: if node.val < low, skip the left subtree; if > high, skip the right; otherwise include the node and recurse both ways.",
         tags=["range-sum-bst","bst","dfs","pruning","dsa"],
         code='''# Sum BST node values within [low, high], pruning out-of-range subtrees.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def range_sum_bst(root, low, high):
    if root is None:
        return 0
    if root.val < low:
        return range_sum_bst(root.right, low, high)   # whole left is too small
    if root.val > high:
        return range_sum_bst(root.left, low, high)    # whole right is too big
    return root.val + range_sum_bst(root.left, low, high) + range_sum_bst(root.right, low, high)''',
         complexity="Time O(n) worst, better with pruning; space O(h).",
         pitfalls="Not pruning (visits every node); wrong comparison direction for the BST invariant.",
         example="range_sum_bst(BST of [10,5,15,3,7,18], 7, 15) -> 32  (7+10+15)."),
    dict(cat="dsa", title="Search in a Binary Search Tree",
         answer="Find the subtree rooted at the node equal to a value, using the BST property: go left if the target is smaller, right if larger, until found or null.",
         tags=["search-bst","bst","binary-search","dsa"],
         code='''# Return the subtree whose root equals val, using BST ordering.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def search_bst(root, val):
    while root is not None and root.val != val:
        root = root.left if val < root.val else root.right   # BST-guided descent
    return root''',
         complexity="Time O(h), space O(1).",
         pitfalls="Scanning like a plain tree (O(n)); wrong branch direction.",
         example="search_bst(BST of [4,2,7,1,3], 2).val -> 2; searching 5 -> None."),
    dict(cat="dsa", title="Lowest Common Ancestor of a BST",
         answer="In a BST, the LCA of p and q is the first node where the paths diverge. Walk from the root: if both values are smaller go left, if both larger go right; otherwise the current node is the split point = LCA.",
         tags=["lca-bst","bst","ancestor","dsa"],
         code='''# Lowest common ancestor of two values in a BST.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def lowest_common_ancestor(root, p, q):
    while root:
        if p < root.val and q < root.val:
            root = root.left            # both in the left subtree
        elif p > root.val and q > root.val:
            root = root.right           # both in the right subtree
        else:
            return root                 # split point (or one equals root)
    return None''',
         complexity="Time O(h), space O(1).",
         pitfalls="Using a general-tree LCA (ignores the BST shortcut); mishandling when one value equals the node.",
         example="lowest_common_ancestor(BST of [6,2,8,0,4,7,9], 2, 8).val -> 6."),
    dict(cat="dsa", title="Reverse Linked List",
         answer="Reverse a singly linked list iteratively by re-pointing each node's next to its predecessor, advancing three pointers (prev, curr, next).",
         tags=["reverse-linked-list","linked-list","pointers","dsa"],
         code='''# Reverse a singly linked list in place.
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def reverse_list(head):
    prev = None
    curr = head
    while curr:
        nxt = curr.next             # remember the rest
        curr.next = prev            # flip the pointer
        prev = curr                 # advance prev
        curr = nxt                  # advance curr
    return prev

def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out

def build(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head''',
         complexity="Time O(n), space O(1).",
         pitfalls="Losing the rest of the list by overwriting next before saving it; returning head instead of prev.",
         example="to_list(reverse_list(build([1,2,3,4,5]))) -> [5,4,3,2,1]."),
    dict(cat="dsa", title="Middle of the Linked List",
         answer="Return the middle node (second middle if even length). Fast/slow pointers: fast moves two steps per one of slow; when fast reaches the end, slow is at the middle.",
         tags=["middle-linked-list","linked-list","fast-slow-pointers","dsa"],
         code='''# Middle node of a linked list via fast/slow pointers.
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def middle_node(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next            # one step
        fast = fast.next.next       # two steps
    return slow

def build(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head''',
         complexity="Time O(n), space O(1).",
         pitfalls="Wrong loop condition returns the first middle on even lengths; null-deref if you skip the fast.next check.",
         example="middle_node(build([1,2,3,4,5])).val -> 3; for [1,2,3,4,5,6] -> 4."),
    dict(cat="dsa", title="Merge Two Sorted Lists",
         answer="Merge two sorted linked lists into one sorted list. Use a dummy head; repeatedly attach the smaller of the two front nodes, then append the remaining tail.",
         tags=["merge-sorted-lists","linked-list","two-pointers","dsa"],
         code='''# Merge two sorted linked lists into one sorted list.
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def merge_two_lists(l1, l2):
    dummy = ListNode(0)
    tail = dummy
    while l1 and l2:
        if l1.val <= l2.val:
            tail.next = l1          # take from l1
            l1 = l1.next
        else:
            tail.next = l2          # take from l2
            l2 = l2.next
        tail = tail.next
    tail.next = l1 or l2            # attach whatever remains
    return dummy.next

def to_list(head):
    out = []
    while head:
        out.append(head.val)
        head = head.next
    return out

def build(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head''',
         complexity="Time O(n + m), space O(1).",
         pitfalls="Forgetting to attach the leftover tail; not using a dummy head (messy first-node logic).",
         example="to_list(merge_two_lists(build([1,2,4]), build([1,3,4]))) -> [1,1,2,3,4,4]."),
    dict(cat="dsa", title="Linked List Cycle",
         answer="Detect whether a linked list has a cycle. Floyd's tortoise and hare: a slow and a fast pointer; if they ever meet there's a cycle, if fast reaches null there isn't.",
         tags=["linked-list-cycle","floyd","fast-slow-pointers","dsa"],
         code='''# Detect a cycle in a linked list (Floyd's algorithm).
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def has_cycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow is fast:            # pointers met -> cycle
            return True
    return False''',
         complexity="Time O(n), space O(1).",
         pitfalls="Using a visited-set (O(n) space) when Floyd is O(1); missing the fast.next null check.",
         example="has_cycle on a 3-node list whose tail links back to head -> True; a plain list -> False."),
    dict(cat="glossary", title="Split-brain",
         answer="A failure in a distributed/clustered system where a NETWORK PARTITION splits nodes into groups that each believe they're the sole authority (e.g. two primaries), so both accept writes and DIVERGE -- causing conflicting data and corruption when the partition heals. Prevented by QUORUM (a majority must agree, so a minority partition can't act), fencing tokens, and witness/tiebreaker nodes. Split-brain is the concrete danger CAP's 'partition' branch forces you to design against.",
         tags=["split-brain","network-partition","quorum","consensus","distributed-systems"],
         example="A 2-node DB cluster partitions; each node promotes itself to primary and takes writes, so the same row gets different values on each side -- a quorum requirement (need majority of 3+ nodes) would have kept the minority side read-only."),
    dict(cat="glossary", title="Fencing token",
         answer="A monotonically increasing number handed out with a LOCK or leadership grant so a stale holder can't cause damage after it's been superseded. If a client acquires a lock, pauses (GC/network), and its lease expires and is granted to another (with a higher token), the resource REJECTS the paused client's later write because it carries an OLD, lower token. Fencing turns 'I think I still hold the lock' into a checkable, ordered claim -- essential because leases alone can't stop a delayed process.",
         tags=["fencing-token","distributed-lock","lease","split-brain","distributed-systems"],
         example="Client A gets lock with token 33, stalls; its lease expires and B gets token 34 and writes. A wakes and writes with token 33 -- the storage sees 33 < 34 (last accepted) and rejects it, preventing corruption from the zombie lock holder."),
    dict(cat="glossary", title="Gossip protocol",
         answer="A decentralized, epidemic-style communication method where each node periodically exchanges state with a few RANDOM peers, so information spreads exponentially through the cluster without any central coordinator. Used for membership/failure detection and metadata dissemination (Cassandra, DynamoDB, Consul, Serf). Benefits: scalable, robust to failures, no single point of failure, eventually consistent view. Costs: eventual (not instant) convergence and some redundant messages. Convergence time is logarithmic in cluster size.",
         tags=["gossip-protocol","epidemic","membership","failure-detection","distributed-systems"],
         example="In Cassandra each node gossips with a few random peers every second; when one dies, that fact propagates cluster-wide within seconds via the exponential spread -- no central registry needed."),
    dict(cat="glossary", title="Read repair and anti-entropy",
         answer="Two mechanisms Dynamo-style stores use to converge replicas after eventual-consistency divergence. READ REPAIR: on a read that queries multiple replicas, detect stale ones (by version/timestamp) and asynchronously push the newest value to them -- cheap, fixes hot data on access. ANTI-ENTROPY: a background process compares replicas wholesale using MERKLE TREES (hash trees) to find differing key ranges efficiently and sync only those -- catches cold data never read. Together they repair the inconsistency that quorum writes/hinted handoff can leave behind.",
         tags=["read-repair","anti-entropy","merkle-tree","eventual-consistency","distributed-systems"],
         example="Cassandra compares replicas' Merkle trees during repair; only the subtrees whose hashes differ are streamed, so two 1M-key replicas that differ on 100 keys exchange those ranges instead of the whole dataset."),
    dict(cat="ml_coding", title="Focal loss (numpy)",
         answer="Focal loss addresses extreme class imbalance (e.g. object detection) by DOWN-WEIGHTING easy, well-classified examples so training focuses on hard ones. It multiplies cross-entropy by (1 - p_t)^gamma, where p_t is the predicted prob of the true class: easy examples (p_t near 1) get a tiny weight; hard ones (p_t low) keep near full weight.",
         tags=["focal-loss","class-imbalance","object-detection","loss-function","ml-coding"],
         code='''# Binary focal loss. ast.parse-only.
import numpy as np

def focal_loss(y_true, p, gamma=2.0, alpha=0.25, eps=1e-9):
    p = np.clip(p, eps, 1 - eps)                  # avoid log(0)
    p_t = np.where(y_true == 1, p, 1 - p)         # prob of the true class
    alpha_t = np.where(y_true == 1, alpha, 1 - alpha)
    loss = -alpha_t * (1 - p_t) ** gamma * np.log(p_t)   # down-weight easy ones
    return np.mean(loss)''',
         complexity="Time O(n), space O(n).",
         pitfalls="Forgetting the (1-p_t)^gamma modulating factor (reduces to weighted CE); not clipping p (log(0)); wrong p_t for negatives.",
         example="focal_loss(y, p, gamma=2) makes a confident-correct example (p_t=0.99) contribute ~0.0001x its CE, so rare hard positives dominate the gradient."),
    dict(cat="ml_coding", title="He / Xavier weight initialization (numpy)",
         answer="Good initialization keeps activation variance stable across layers. XAVIER/Glorot (for tanh/sigmoid) scales by sqrt(1/fan_in) (or 2/(fan_in+fan_out)); HE (for ReLU) scales by sqrt(2/fan_in) to compensate for ReLU zeroing half the activations. Wrong scale -> vanishing or exploding activations.",
         tags=["weight-initialization","he-init","xavier-init","variance","ml-coding"],
         code='''# He and Xavier initializers. ast.parse-only (rng passed in).
import numpy as np

def he_init(fan_in, fan_out, rng):
    std = np.sqrt(2.0 / fan_in)                   # ReLU: keep variance stable
    return rng.standard_normal((fan_in, fan_out)) * std

def xavier_init(fan_in, fan_out, rng):
    std = np.sqrt(2.0 / (fan_in + fan_out))       # tanh/sigmoid
    return rng.standard_normal((fan_in, fan_out)) * std''',
         complexity="Time O(fan_in * fan_out), space O(fan_in * fan_out).",
         pitfalls="Using Xavier with ReLU (activations shrink -- He compensates for the halving); initializing all weights equal (symmetry never breaks).",
         example="he_init(256, 128, rng) gives weights with std sqrt(2/256) ~ 0.088, keeping ReLU activation variance roughly constant layer-to-layer."),
    dict(cat="conceptual", title="Why does minimum depth of a binary tree need special handling for single-child nodes?",
         answer="The maximum-depth problem has a clean recurrence: depth(node) = 1 + max(depth(left), depth(right)), with depth(null) = 0. It's tempting to write minimum depth by analogy as 1 + min(depth(left), depth(right)) -- but this is WRONG, and the reason exposes a subtle definitional point. Minimum depth is defined as the number of nodes on the shortest path from the root to a LEAF, and a leaf is a node with NO children. Now consider a node that has only ONE child -- say a left child but no right child. Its right subtree is empty, so depth(right) = 0. The naive min formula computes 1 + min(depth(left), 0) = 1 + 0 = 1, claiming this node is at minimum depth 1 as if it were a leaf. But it is NOT a leaf -- it has a left child -- so there is no root-to-leaf path that stops here. The formula has effectively invented a path that ends at a missing child, which isn't allowed. The correct rule: minimum depth must only take the min over children that ACTUALLY EXIST. So if one child is null, you must recurse into the non-null child (1 + depth(existing child)), NOT take min with the null side's 0. Only when BOTH children exist do you take 1 + min(left, right); when both are null (a true leaf) you return 1. Maximum depth doesn't suffer this because max naturally IGNORES the shorter (null) side -- max(depth(left), 0) = depth(left) whenever the left side is deeper -- so the missing child's 0 never wins and never fabricates a false path. The asymmetry is that min is 'attracted' to the zero from a missing subtree while max is repelled by it. The general lesson: when a recurrence's base case value (0 for null) can be spuriously selected by the aggregation (min picks small values), you must guard the base case so it only applies at genuine terminals -- here, genuine leaves. A BFS solution sidesteps the trap naturally: do a level-order traversal and return the depth of the FIRST node with no children, which is by construction the nearest leaf, and it's also faster because it stops as soon as it finds the shallowest leaf rather than exploring the whole tree.",
         tags=["min-depth","binary-tree","recursion","edge-cases","why"],
         example="For a right-skewed tree 1 -> 2 -> 3 (each only a right child), the true minimum depth is 3 (the only leaf is node 3); the naive 1+min(left,right) would return 1 at the root because the missing left child contributes depth 0 -- a path that doesn't end at a leaf."),
    dict(cat="conceptual", title="Why does focal loss help with class imbalance where weighted cross-entropy alone falls short?",
         answer="Extreme class imbalance -- like object detection where a single image has a handful of true objects and tens of thousands of easy background locations -- breaks naive training because the loss is dominated by the SHEER NUMBER of easy negatives. Even if each easy background example contributes a tiny individual loss (the model is already confident it's background, p near the correct value), there are so many of them that their SUM overwhelms the gradient signal from the rare, hard, informative positives; the model converges to 'predict background everywhere' and the useful examples get drowned out. The first fix people reach for is WEIGHTED (or balanced) cross-entropy: multiply the loss of the rare positive class by a large alpha and the common class by a small one, to rebalance their total contributions. This helps with the class-frequency imbalance -- it corrects for how MANY of each class there are -- but it has a blind spot: it weights every example of a class the SAME regardless of whether the model already gets it right. It does NOT distinguish EASY examples from HARD ones. So a mountain of easy, already-correct negatives still each carry the full (down-weighted) loss, and a well-classified example contributes as much per-example signal as a misclassified one of the same class. FOCAL LOSS adds the missing ingredient: a modulating factor (1 - p_t)^gamma, where p_t is the model's predicted probability of the TRUE class. When the model is confident and correct (p_t near 1), (1 - p_t)^gamma is tiny, so that example's loss is scaled down toward zero -- it's already learned, stop letting it dominate. When the model is wrong or unsure (p_t low), (1 - p_t)^gamma stays near 1, preserving the full loss -- keep focusing on it. Gamma controls the strength (gamma=0 recovers cross-entropy; gamma=2 is typical). The crucial difference from weighted CE is that focal loss re-weights by DIFFICULTY (a per-example, dynamic property that changes as the model learns), not by class membership (a static property). This automatically shifts the training focus onto the hard examples over time and stops the legion of easy negatives from swamping the gradient, even though there are vastly more of them. In practice focal loss is often combined with an alpha class-weight too (the paper's alpha-balanced focal loss), getting both effects: alpha handles the raw frequency imbalance, and the focal term handles the easy/hard imbalance -- and it was exactly this combination that let single-stage detectors like RetinaNet match two-stage ones. The broader principle: 'imbalance' can mean imbalance in COUNT (fixed by class weighting) or imbalance in DIFFICULTY/contribution (fixed by focal-style down-weighting of easy examples), and they need different tools.",
         tags=["focal-loss","class-imbalance","weighted-cross-entropy","hard-example-mining","why"],
         example="In detection with 100 hard positives and 100,000 easy backgrounds, weighted CE still lets the 100k easy examples (each already correct) sum to a dominating loss; focal loss with gamma=2 scales a p_t=0.99 background's loss by (0.01)^2=1e-4, so the hard positives finally drive the gradient."),
    dict(cat="behavioral", title="STAR: Being frugal / doing more with less (Frugality)",
         answer="Amazon LP: FRUGALITY -- accomplish more with less; constraints breed resourcefulness, self-sufficiency, and invention; no extra points for headcount, budget, or fixed expense. Show you delivered a meaningful outcome without throwing money/people at it, turning a constraint into a smarter solution.",
         tags=["behavioral","star","frugality","amazon-lp","resourcefulness"],
         example="SITUATION: Our analytics pipeline's cloud bill was climbing fast -- we were running a large always-on managed cluster to process nightly batch jobs, and the easy ask was to buy a bigger cluster to fix growing runtimes. TASK: I wanted to cut both cost and runtime WITHOUT more spend, treating the budget constraint as a design prompt. ACTION: Instead of scaling up, I profiled the jobs and found two things: the cluster sat idle ~20 hours a day, and 80% of the runtime came from a few unpartitioned full-table scans. I moved the batch jobs to ephemeral spot instances that spin up only for the nightly window and terminate after (paying for ~4 hours, not 24, at spot discounts), and I added partitioning and columnar formats so the heavy queries scanned a fraction of the data. I validated correctness against the old outputs before cutting over. RESULT: The monthly bill dropped by roughly two-thirds AND the nightly runtime got faster because of the query fixes -- a better result than the bigger-cluster proposal would have given, at lower cost. The frugality constraint forced me to actually understand the workload instead of masking inefficiency with more hardware, and the partitioning work kept paying off as data grew."),
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
