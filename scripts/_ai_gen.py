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
    dict(cat="dsa", title="Palindrome Linked List",
         answer="Check a singly linked list reads the same forwards and backwards in O(1) space. Find the middle with fast/slow, reverse the second half, then compare the two halves node by node.",
         tags=["palindrome-linked-list","linked-list","fast-slow-pointers","reverse","dsa"],
         code='''# True if a linked list is a palindrome, using O(1) extra space.
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def is_palindrome(head):
    # find the middle (slow ends at the start of the 2nd half)
    slow = fast = head
    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
    # reverse the second half
    prev = None
    while slow:
        nxt = slow.next
        slow.next = prev
        prev = slow
        slow = nxt
    # compare halves
    left, right = head, prev
    while right:
        if left.val != right.val:
            return False
        left = left.next
        right = right.next
    return True

def build(vals):
    head = None
    for v in reversed(vals):
        head = ListNode(v, head)
    return head''',
         complexity="Time O(n), space O(1).",
         pitfalls="Comparing the whole reversed list instead of stopping at the shorter half; mutating without restoring (fine if not required).",
         example="is_palindrome(build([1,2,2,1])) -> True; is_palindrome(build([1,2,3])) -> False."),
    dict(cat="dsa", title="Remove Linked List Elements",
         answer="Delete all nodes equal to a target value. Use a dummy head so removing the first node is uniform; walk with a prev pointer, skipping matching nodes.",
         tags=["remove-linked-list-elements","linked-list","dummy-head","dsa"],
         code='''# Remove all nodes with a given value from a linked list.
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def remove_elements(head, val):
    dummy = ListNode(0, head)
    prev = dummy
    curr = head
    while curr:
        if curr.val == val:
            prev.next = curr.next    # unlink the matching node
        else:
            prev = curr              # keep it; advance prev
        curr = curr.next
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
         complexity="Time O(n), space O(1).",
         pitfalls="Not using a dummy head (special-casing head removal); advancing prev when you removed a node.",
         example="to_list(remove_elements(build([1,2,6,3,6]), 6)) -> [1,2,3]."),
    dict(cat="dsa", title="Remove Nth Node From End of List",
         answer="Delete the n-th node from the end in one pass. Two pointers: advance a lead pointer n steps first, then move lead and a trailing pointer together until lead hits the end; the trailing pointer sits just before the target.",
         tags=["remove-nth-from-end","linked-list","two-pointers","dsa"],
         code='''# Remove the nth node from the end in a single pass.
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def remove_nth_from_end(head, n):
    dummy = ListNode(0, head)
    lead = trail = dummy
    for _ in range(n):
        lead = lead.next             # give lead an n-node head start
    while lead.next:
        lead = lead.next
        trail = trail.next           # move together until lead is last
    trail.next = trail.next.next     # unlink the target
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
         complexity="Time O(n), space O(1).",
         pitfalls="Off-by-one in the head start (use a dummy); not handling removal of the head node.",
         example="to_list(remove_nth_from_end(build([1,2,3,4,5]), 2)) -> [1,2,3,5]."),
    dict(cat="dsa", title="Odd Even Linked List",
         answer="Group nodes at ODD positions before nodes at EVEN positions, preserving relative order, in O(1) space. Thread two chains (odd and even) with pointers, then attach the even chain after the odd tail.",
         tags=["odd-even-linked-list","linked-list","pointers","dsa"],
         code='''# Reorder so odd-indexed nodes precede even-indexed ones (1-based).
class ListNode:
    def __init__(self, val, next=None):
        self.val = val
        self.next = next

def odd_even_list(head):
    if not head or not head.next:
        return head
    odd = head
    even = head.next
    even_head = even                 # remember the start of the even chain
    while even and even.next:
        odd.next = even.next         # splice the next odd node
        odd = odd.next
        even.next = odd.next         # splice the next even node
        even = even.next
    odd.next = even_head             # attach evens after odds
    return head

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
         pitfalls="Losing the even-chain head; not terminating the odd chain before attaching evens.",
         example="to_list(odd_even_list(build([1,2,3,4,5]))) -> [1,3,5,2,4]."),
    dict(cat="dsa", title="Binary Tree Level Order Traversal",
         answer="Return node values grouped by level (BFS). Use a queue; for each level, pop the current level's size number of nodes and enqueue their children.",
         tags=["level-order-traversal","tree","bfs","queue","dsa"],
         code='''# BFS level-order traversal grouped by level.
from collections import deque

class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def level_order(root):
    if root is None:
        return []
    result = []
    queue = deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):   # fix this level's node count
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level)
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Not snapshotting the level size before the loop (mixes levels); forgetting the empty-tree case.",
         example="level_order(Node(3, Node(9), Node(20, Node(15), Node(7)))) -> [[3],[9,20],[15,7]]."),
    dict(cat="dsa", title="Binary Tree Zigzag Level Order Traversal",
         answer="Level-order traversal but alternate direction each level (left-to-right, then right-to-left). Standard BFS, reversing every other level's collected values.",
         tags=["zigzag-traversal","tree","bfs","queue","dsa"],
         code='''# BFS level order, alternating direction per level.
from collections import deque

class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def zigzag_level_order(root):
    if root is None:
        return []
    result = []
    queue = deque([root])
    left_to_right = True
    while queue:
        level = []
        for _ in range(len(queue)):
            node = queue.popleft()
            level.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        result.append(level if left_to_right else level[::-1])
        left_to_right = not left_to_right   # flip direction
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Reversing the queue instead of the output list; forgetting to toggle the direction flag.",
         example="zigzag_level_order(Node(3, Node(9), Node(20, Node(15), Node(7)))) -> [[3],[20,9],[15,7]]."),
    dict(cat="dsa", title="Binary Tree Right Side View",
         answer="Return the values visible from the right side (the last node of each level). BFS and take the last element of each level (or DFS visiting right first, recording the first node seen at each depth).",
         tags=["right-side-view","tree","bfs","dsa"],
         code='''# Values seen from the right: last node of each level.
from collections import deque

class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def right_side_view(root):
    if root is None:
        return []
    result = []
    queue = deque([root])
    while queue:
        n = len(queue)
        for i in range(n):
            node = queue.popleft()
            if i == n - 1:            # last node of this level is visible
                result.append(node.val)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Taking the rightmost CHILD rather than the last node at each level (a left-only deeper node can be visible); off-by-one on the last index.",
         example="right_side_view(Node(1, Node(2, None, Node(5)), Node(3, None, Node(4)))) -> [1,3,4]."),
    dict(cat="dsa", title="Symmetric Tree",
         answer="Check a binary tree is a mirror of itself. Recurse on pairs (left subtree, right subtree): mirrored iff values equal AND left.left mirrors right.right AND left.right mirrors right.left.",
         tags=["symmetric-tree","tree","recursion","mirror","dsa"],
         code='''# True if a binary tree is symmetric about its center.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def is_symmetric(root):
    def mirror(a, b):
        if a is None and b is None:
            return True
        if a is None or b is None or a.val != b.val:
            return False
        # outer pair and inner pair must both mirror
        return mirror(a.left, b.right) and mirror(a.right, b.left)
    return root is None or mirror(root.left, root.right)''',
         complexity="Time O(n), space O(h).",
         pitfalls="Comparing subtrees in the same orientation (must cross: left.left vs right.right); missing one-null case.",
         example="is_symmetric(Node(1, Node(2, Node(3), Node(4)), Node(2, Node(4), Node(3)))) -> True."),
    dict(cat="dsa", title="Convert Sorted Array to BST",
         answer="Build a HEIGHT-BALANCED BST from a sorted array. Recursively pick the middle element as the subtree root (so halves are balanced), building left from the left half and right from the right half.",
         tags=["sorted-array-to-bst","bst","divide-and-conquer","recursion","dsa"],
         code='''# Build a height-balanced BST from a sorted array.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def sorted_array_to_bst(nums):
    def build(lo, hi):
        if lo > hi:
            return None
        mid = (lo + hi) // 2          # middle keeps subtrees balanced
        node = Node(nums[mid])
        node.left = build(lo, mid - 1)
        node.right = build(mid + 1, hi)
        return node
    return build(0, len(nums) - 1)

def inorder(node):
    if node is None:
        return []
    return inorder(node.left) + [node.val] + inorder(node.right)''',
         complexity="Time O(n), space O(log n) recursion.",
         pitfalls="Picking a non-middle root (unbalanced tree); off-by-one in the half ranges.",
         example="inorder(sorted_array_to_bst([-10,-3,0,5,9])) -> [-10,-3,0,5,9] (and balanced)."),
    dict(cat="dsa", title="Validate Binary Search Tree",
         answer="Check a tree is a valid BST: every node greater than all in its left subtree and less than all in its right. Recurse carrying an allowed (low, high) range, tightening it as you descend.",
         tags=["validate-bst","bst","recursion","bounds","dsa"],
         code='''# True if the tree satisfies the BST ordering globally.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def is_valid_bst(root):
    def valid(node, low, high):
        if node is None:
            return True
        if not (low < node.val < high):   # must lie strictly in range
            return False
        return valid(node.left, low, node.val) and valid(node.right, node.val, high)
    return valid(root, float('-inf'), float('inf'))''',
         complexity="Time O(n), space O(h).",
         pitfalls="Only comparing a node to its direct children (misses distant violations); using <= where strict < is required.",
         example="is_valid_bst(Node(5, Node(1), Node(4, Node(3), Node(6)))) -> False (4 < 5 but in right subtree)."),
    dict(cat="dsa", title="Kth Smallest Element in a BST",
         answer="Find the k-th smallest value. An in-order traversal of a BST visits values in ascending order; stop at the k-th visited node (iterative in-order with a stack is O(h) space).",
         tags=["kth-smallest-bst","bst","inorder","stack","dsa"],
         code='''# Kth smallest value in a BST via iterative in-order traversal.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def kth_smallest(root, k):
    stack = []
    curr = root
    while stack or curr:
        while curr:
            stack.append(curr)       # go as left as possible
            curr = curr.left
        curr = stack.pop()           # visit in ascending order
        k -= 1
        if k == 0:
            return curr.val
        curr = curr.right
    return None''',
         complexity="Time O(h + k), space O(h).",
         pitfalls="Doing a full traversal when you can stop at k; decrementing k in the wrong place.",
         example="kth_smallest(Node(3, Node(1, None, Node(2)), Node(4)), 1) -> 1."),
    dict(cat="glossary", title="Lease",
         answer="A LEASE is a lock with a TIME BOUND: a node is granted exclusive rights (to be leader, hold a lock, own a shard) for a limited duration and must RENEW before expiry to keep it. If the holder crashes or is partitioned, the lease simply EXPIRES and another node can take over -- avoiding the deadlock a permanent lock would cause. The catch: leases rely on bounded clock drift and don't stop a paused-then-resumed holder from acting on an expired lease, which is why they're paired with FENCING TOKENS. Core to leader election and distributed locks (Chubby, etcd, ZooKeeper).",
         tags=["lease","distributed-lock","leader-election","expiry","distributed-systems"],
         example="An etcd leader holds a 10s lease it renews every few seconds; if it crashes, the lease expires in 10s and a follower is elected -- no manual intervention, and no permanent lock stuck on a dead node."),
    dict(cat="glossary", title="Hinted handoff",
         answer="A technique in Dynamo-style systems to keep WRITES available during a temporary node outage. If a replica that should store a write is down, a healthy node accepts the write and stores a HINT (metadata noting the intended recipient); when the down node recovers, the hint is HANDED OFF (replayed) to it. This preserves write availability and durability during transient failures without waiting for the node, at the cost of temporary inconsistency (resolved later by read-repair/anti-entropy).",
         tags=["hinted-handoff","availability","dynamo","eventual-consistency","distributed-systems"],
         example="A write's target replica is rebooting; a neighbor stores it with a hint 'meant for node C'. When C comes back, the neighbor replays the buffered writes to it -- so the outage didn't reject the client's write."),
    dict(cat="glossary", title="Quorum (W + R > N)",
         answer="In a replicated store with N replicas, a QUORUM protocol requires W replicas to acknowledge a write and R replicas to answer a read. If W + R > N, the read and write replica sets are GUARANTEED to OVERLAP by at least one node, so every read sees the latest acknowledged write -- giving strong consistency while tolerating failures. Tuning shifts the trade-off: W=N,R=1 (fast reads, slow/fragile writes), W=1,R=N (fast writes), W=R=(N+1)/2 (balanced). SLOPPY quorums relax this for availability at the cost of the overlap guarantee.",
         tags=["quorum","w-plus-r","replication","consistency","distributed-systems"],
         example="With N=3, W=2, R=2: a write waits for 2 of 3 acks and a read queries 2 of 3; since 2+2>3 the read set always includes a node that saw the write -- so clients never read stale after a successful write."),
    dict(cat="ml_coding", title="SGD with momentum update (numpy)",
         answer="Momentum accelerates SGD by accumulating a velocity that is an exponential moving average of past gradients, damping oscillation in ravines and speeding progress along consistent directions. v = beta*v + g; w -= lr * v (or the equivalent with (1-beta) weighting).",
         tags=["momentum","sgd","optimizer","velocity","ml-coding"],
         code='''# SGD-with-momentum parameter update. ast.parse-only.
import numpy as np

def momentum_step(w, g, v, lr=1e-2, beta=0.9):
    v = beta * v + g                              # accumulate velocity
    w = w - lr * v                                # step along the velocity
    return w, v''',
         complexity="Time O(size of w), space O(size of w).",
         pitfalls="Forgetting to persist v across steps (loses the accumulation); confusing this with Nesterov (which looks ahead before the gradient).",
         example="Over steps with a consistent gradient direction, v grows and the effective step size increases, converging faster than plain SGD in a narrow valley."),
    dict(cat="ml_coding", title="Label smoothing (numpy)",
         answer="Label smoothing softens one-hot targets to discourage over-confidence and improve generalization/calibration. Replace the hard 1 with 1 - epsilon and distribute epsilon over the other classes: y_smooth = (1 - eps) * onehot + eps / num_classes.",
         tags=["label-smoothing","regularization","calibration","classification","ml-coding"],
         code='''# Apply label smoothing to one-hot targets. ast.parse-only.
import numpy as np

def label_smoothing(one_hot, eps=0.1):
    num_classes = one_hot.shape[1]
    # pull the target off 1.0 and spread eps mass across all classes
    return one_hot * (1 - eps) + eps / num_classes''',
         complexity="Time O(n * classes), space O(n * classes).",
         pitfalls="Spreading eps over only the wrong classes (spread over ALL, including the true one is the standard form); using too large an eps (underfits).",
         example="label_smoothing(np.array([[1.,0.,0.]]), 0.1) -> [[0.9333, 0.0333, 0.0333]] (true class 0.9+eps/3)."),
    dict(cat="conceptual", title="Why does validating a BST require passing down min/max bounds instead of just comparing to children?",
         answer="A naive BST validator checks, at each node, that node.left.val < node.val < node.right.val -- comparing a node only to its DIRECT children. This is WRONG because the BST property is GLOBAL, not local: it requires that EVERY value in a node's entire left subtree is less than the node, and every value in its entire right subtree is greater -- not merely the immediate children. A tree can satisfy every parent-child comparison and still violate the BST invariant because of a DISTANT descendant. Classic counterexample: root 5, left child 1, right child 4, where 4 has children 3 and 6. Every local check passes (1<5, 4>5? no -- take a cleaner one): root 10 with right child 15, and 15 has a left child 6. Locally 15>10 (fine) and 6<15 (fine), but 6 is in the RIGHT subtree of 10, so it must be >10 -- and it isn't. The local check never compares 6 against its grandparent 10, so it misses the violation. The fix is to thread down an ALLOWED RANGE (low, high) that every node must fall strictly within, tightening the range as you descend: when you go LEFT from a node with value v, the whole left subtree must be less than v, so you set the new upper bound to v (range becomes (low, v)); when you go RIGHT, everything must exceed v, so the new lower bound is v (range becomes (v, high)). A node is valid iff low < node.val < high AND both children are valid under their tightened ranges. This way, node 6 above would be validated against the range (10, 15) -- inherited from having gone right at 10 then left at 15 -- and correctly rejected because 6 is not > 10. The bounds carry the ancestor constraints that pure child comparisons lose. Two implementation notes: use strict inequalities (a BST typically forbids duplicates, or you must decide a consistent side for them), and use +/- infinity as the initial bounds for the root. An elegant alternative that also captures the global property: do an IN-ORDER traversal and verify the visited values are strictly increasing -- because an in-order walk of a valid BST yields sorted output, any out-of-order adjacent pair reveals a violation, distant or not. Both approaches work precisely because they encode the global ordering constraint rather than a purely local one.",
         tags=["validate-bst","bst","bounds","in-order","why"],
         example="Tree 10 -> right 15 -> left 6: local checks pass (15>10, 6<15) but it's an invalid BST because 6 sits in 10's right subtree; the range method validates 6 against (10, inf) inherited from ancestors and rejects it, and an in-order walk yields [10,6,15] which isn't sorted."),
    dict(cat="conceptual", title="Why does momentum speed up gradient descent, and what problem with plain SGD does it fix?",
         answer="Plain gradient descent updates weights by w -= lr * g, taking a step directly proportional to the current gradient. This struggles badly in a very common loss-surface shape: a long, narrow RAVINE -- a region that is steeply curved in some directions and gently sloped in others (mathematically, the Hessian has very different eigenvalues, i.e. a high condition number). In such a ravine, the gradient points mostly ACROSS the valley (down the steep walls) rather than ALONG it (toward the minimum). So plain SGD oscillates back and forth between the steep walls, making big zig-zag moves that largely cancel out, while creeping only slowly along the shallow direction toward the actual minimum. To avoid divergence on the steep axis you're forced to use a small learning rate, which makes the slow progress along the valley floor even slower -- a frustrating trade-off. MOMENTUM fixes this by giving the optimizer INERTIA. Instead of stepping by the raw gradient, it maintains a VELOCITY vector that is an exponentially-weighted running average of past gradients: v = beta*v + g, then w -= lr*v (beta ~ 0.9). The key effect is directional filtering. Along the OSCILLATING steep axis, successive gradients point in OPPOSITE directions on alternate steps, so they largely CANCEL in the running average -- the velocity in that direction stays small and the zig-zag is damped. Along the CONSISTENT shallow axis, successive gradients all point the SAME way, so they ACCUMULATE in the running average -- the velocity builds up and the optimizer accelerates toward the minimum, like a ball rolling downhill gathering speed. So momentum simultaneously suppresses the wasteful oscillation and amplifies progress in the productive direction, which is exactly the pathology plain SGD has in ill-conditioned ravines. Consequences and nuances: momentum lets you use a larger effective learning rate without diverging, it helps roll through small local bumps and flat regions (plateaus) where the raw gradient is tiny because the accumulated velocity carries it, and beta controls how much history is averaged (higher = smoother/more inertia but slower to change direction). NESTEROV momentum refines it by evaluating the gradient at the look-ahead position (where the velocity is about to take you), which gives a more responsive correction and often slightly better convergence. Modern optimizers like Adam combine this first-moment momentum with per-parameter adaptive scaling. The core intuition to remember: momentum turns a memoryless, oscillation-prone step into an inertial one that averages out noise/oscillation and accelerates along persistent gradient directions.",
         tags=["momentum","sgd","optimization","ill-conditioning","why"],
         example="On a loss shaped like a taco (steep sides, gentle length), plain SGD bounces between the steep walls and inches along the length; momentum cancels the alternating side-to-side gradients and accumulates the consistent lengthwise gradient, so it shoots down the valley far faster at the same learning rate."),
    dict(cat="behavioral", title="STAR: Customer obsession -- starting from the customer and working backward",
         answer="Amazon LP: CUSTOMER OBSESSION -- leaders start with the customer and work backwards; they work vigorously to earn and keep customer trust, and while they pay attention to competitors, they obsess over customers. Show you dug into a real customer pain, worked backward to the right solution (not the convenient one), and improved the customer outcome measurably.",
         tags=["behavioral","star","customer-obsession","amazon-lp","working-backwards"],
         example="SITUATION: Support tickets for our onboarding flow were rising, but the aggregate completion metric looked 'fine', so there was pressure to dismiss it as noise and ship the next planned feature. TASK: I suspected the average was hiding real pain, so I took ownership of understanding the actual customer experience before we built anything. ACTION: I worked backward from the customer: I read 60 recent tickets, watched session replays, and found a specific segment -- users on slow connections and older devices -- who hit a silent timeout on a heavy verification step and simply gave up (they never filed tickets, so they were invisible in our support counts but visible in drop-off). Rather than the convenient fix (a bigger spinner), I wrote a short 'working backwards' note describing that customer's experience and pushed for the real fix: make the verification asynchronous with a save-and-resume, so a slow step never blocked or lost their progress. I prototyped it and tested specifically on throttled connections and a low-end device to reproduce the actual customer's conditions. RESULT: Completion for that segment rose substantially and onboarding-related tickets dropped, while the aggregate metric that had looked 'fine' also ticked up because the hidden failures were real volume. The lesson I carry: averages hide the customers who are struggling -- starting from their concrete experience and working backward surfaced a fix we'd otherwise have ignored, and it earned trust with users who'd been silently churning."),
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
