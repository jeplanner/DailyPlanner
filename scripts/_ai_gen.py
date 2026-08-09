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
    dict(cat="dsa", title="Spiral Matrix",
         answer="Return all elements of an m x n matrix in spiral (clockwise) order. Maintain four boundaries (top, bottom, left, right); walk right, down, left, up, shrinking a boundary after each pass, until they cross.",
         tags=["spiral-matrix","matrix","boundaries","simulation","dsa"],
         code='''# Traverse a matrix in clockwise spiral order.
def spiral_order(matrix):
    if not matrix:
        return []
    top, bottom = 0, len(matrix) - 1
    left, right = 0, len(matrix[0]) - 1
    result = []
    while top <= bottom and left <= right:
        for c in range(left, right + 1):
            result.append(matrix[top][c])      # top row, left to right
        top += 1
        for r in range(top, bottom + 1):
            result.append(matrix[r][right])    # right column, top to bottom
        right -= 1
        if top <= bottom:
            for c in range(right, left - 1, -1):
                result.append(matrix[bottom][c])   # bottom row, right to left
            bottom -= 1
        if left <= right:
            for r in range(bottom, top - 1, -1):
                result.append(matrix[r][left])     # left column, bottom to top
            left += 1
    return result''',
         complexity="Time O(m * n), space O(1) (output aside).",
         pitfalls="Re-walking a row/column when boundaries meet (the two inner ifs guard this); wrong shrink order.",
         example="spiral_order([[1,2,3],[4,5,6],[7,8,9]]) -> [1,2,3,6,9,8,7,4,5]."),
    dict(cat="dsa", title="Rotate Image (90 degrees)",
         answer="Rotate an n x n matrix 90 degrees clockwise IN PLACE. Transpose (swap across the diagonal), then reverse each row.",
         tags=["rotate-image","matrix","transpose","in-place","dsa"],
         code='''# Rotate an n x n matrix 90 degrees clockwise, in place.
def rotate(matrix):
    n = len(matrix)
    for i in range(n):
        for j in range(i + 1, n):
            matrix[i][j], matrix[j][i] = matrix[j][i], matrix[i][j]  # transpose
    for row in matrix:
        row.reverse()                          # reverse each row
    return matrix''',
         complexity="Time O(n^2), space O(1).",
         pitfalls="Transposing the full matrix (double-swaps back to start) -- only iterate j>i; forgetting the row reverse.",
         example="rotate([[1,2,3],[4,5,6],[7,8,9]]) -> [[7,4,1],[8,5,2],[9,6,3]]."),
    dict(cat="dsa", title="Search a 2D Matrix",
         answer="Rows are sorted and each row's first value exceeds the previous row's last -- so the matrix is a sorted 1-D array folded into m x n. Binary search over [0, m*n) mapping mid to (mid//n, mid%n).",
         tags=["search-2d-matrix","binary-search","matrix","dsa"],
         code='''# Binary search a row-wise sorted matrix treated as one sorted array.
def search_matrix(matrix, target):
    if not matrix or not matrix[0]:
        return False
    m, n = len(matrix), len(matrix[0])
    lo, hi = 0, m * n - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        val = matrix[mid // n][mid % n]        # map flat index to 2-D
        if val == target:
            return True
        if val < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return False''',
         complexity="Time O(log(m*n)), space O(1).",
         pitfalls="Wrong flat-to-2D index math; using m instead of n as the divisor.",
         example="search_matrix([[1,3,5,7],[10,11,16,20],[23,30,34,60]], 3) -> True; target 13 -> False."),
    dict(cat="dsa", title="Flipping an Image",
         answer="For each row, reverse it then invert each bit (0<->1). Reverse-then-invert equals: for a row, new[i] = 1 - row[n-1-i]; a two-pointer pass does both at once.",
         tags=["flipping-image","matrix","two-pointers","bit","dsa"],
         code='''# Horizontally flip each row then invert bits.
def flip_and_invert_image(image):
    for row in image:
        i, j = 0, len(row) - 1
        while i <= j:
            # reverse-then-invert: swap ends and flip both bits
            row[i], row[j] = 1 - row[j], 1 - row[i]
            i += 1
            j -= 1
    return image''',
         complexity="Time O(m * n), space O(1).",
         pitfalls="Inverting without reversing (or vice versa); missing the middle element when i == j.",
         example="flip_and_invert_image([[1,1,0],[1,0,1],[0,0,0]]) -> [[1,0,0],[0,1,0],[1,1,1]]."),
    dict(cat="dsa", title="Count Negative Numbers in a Sorted Matrix",
         answer="A matrix is sorted non-increasing along rows and columns; count negatives efficiently. Start at the bottom-left; if the value is negative, all cells to its right in that row are negative (add them and go up), else move right.",
         tags=["count-negatives","sorted-matrix","staircase","matrix","dsa"],
         code='''# Count negatives in a row/col non-increasing matrix (staircase walk).
def count_negatives(grid):
    m, n = len(grid), len(grid[0])
    row, col = m - 1, 0                          # start bottom-left
    count = 0
    while row >= 0 and col < n:
        if grid[row][col] < 0:
            count += n - col                    # rest of this row is negative
            row -= 1                            # move up
        else:
            col += 1                            # move right
    return count''',
         complexity="Time O(m + n), space O(1).",
         pitfalls="Scanning every cell (O(m*n)); starting from a corner that doesn't give the monotonic decision.",
         example="count_negatives([[4,3,2,-1],[3,2,1,-1],[1,1,-1,-2],[-1,-1,-2,-3]]) -> 8."),
    dict(cat="dsa", title="Toeplitz Matrix",
         answer="A matrix is Toeplitz if every top-left-to-bottom-right diagonal has the same value. Check each cell equals the one diagonally up-left (matrix[i-1][j-1]).",
         tags=["toeplitz-matrix","matrix","diagonal","dsa"],
         code='''# True if every descending diagonal is constant.
def is_toeplitz(matrix):
    for i in range(1, len(matrix)):
        for j in range(1, len(matrix[0])):
            if matrix[i][j] != matrix[i - 1][j - 1]:   # compare up-left neighbor
                return False
    return True''',
         complexity="Time O(m * n), space O(1).",
         pitfalls="Comparing along the wrong diagonal; indexing out of bounds at row/col 0 (start loops at 1).",
         example="is_toeplitz([[1,2,3,4],[5,1,2,3],[9,5,1,2]]) -> True."),
    dict(cat="dsa", title="Robot Return to Origin",
         answer="Given a string of moves U/D/L/R, decide if the robot ends at the origin. Track x,y deltas; it returns iff net horizontal and vertical displacement are both zero.",
         tags=["robot-origin","simulation","string","dsa"],
         code='''# True if the move sequence returns the robot to (0,0).
def judge_circle(moves):
    x = y = 0
    for m in moves:
        if m == 'U':
            y += 1
        elif m == 'D':
            y -= 1
        elif m == 'L':
            x -= 1
        elif m == 'R':
            x += 1
    return x == 0 and y == 0''',
         complexity="Time O(n), space O(1).",
         pitfalls="Only checking counts of one axis; miscounting opposite directions.",
         example="judge_circle('UD') -> True; judge_circle('LL') -> False."),
    dict(cat="dsa", title="Count Odd Numbers in an Interval Range",
         answer="Count odd integers in [low, high] inclusive without looping. Count odds in [0, x] is (x+1)//2; answer is f(high) - f(low-1).",
         tags=["count-odds-interval","math","counting","dsa"],
         code='''# Count odd numbers in [low, high] inclusive, in O(1).
def count_odds(low, high):
    def odds_up_to(x):
        return (x + 1) // 2                      # count of odds in [0, x]
    return odds_up_to(high) - odds_up_to(low - 1)''',
         complexity="Time O(1), space O(1).",
         pitfalls="Off-by-one at the endpoints; looping the whole range (too slow for large bounds).",
         example="count_odds(3, 7) -> 3  (3,5,7); count_odds(8, 10) -> 1."),
    dict(cat="dsa", title="Invert Binary Tree",
         answer="Mirror a binary tree by swapping every node's left and right children. Recurse (or BFS/DFS) swapping children at each node. Example uses a tiny local Node class so it runs standalone.",
         tags=["invert-binary-tree","tree","recursion","dfs","dsa"],
         code='''# Mirror a binary tree by swapping children everywhere.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def invert_tree(root):
    if root is None:
        return None
    root.left, root.right = invert_tree(root.right), invert_tree(root.left)  # swap
    return root

def inorder(root):
    # helper to read the tree out for checking
    if root is None:
        return []
    return inorder(root.left) + [root.val] + inorder(root.right)''',
         complexity="Time O(n), space O(h) recursion.",
         pitfalls="Swapping values instead of subtrees; forgetting the null base case.",
         example="invert of tree [4,(2,1,3),(7,6,9)] has inorder [9,7,6,4,3,2,1]."),
    dict(cat="dsa", title="Maximum Depth of Binary Tree",
         answer="Return the number of nodes along the longest root-to-leaf path. Recurse: depth = 1 + max(depth(left), depth(right)); null is depth 0.",
         tags=["max-depth-tree","tree","recursion","dfs","dsa"],
         code='''# Height (max depth) of a binary tree.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def max_depth(root):
    if root is None:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))''',
         complexity="Time O(n), space O(h).",
         pitfalls="Returning edges vs nodes inconsistently; missing the null base case.",
         example="max_depth(Node(3, Node(9), Node(20, Node(15), Node(7)))) -> 3."),
    dict(cat="dsa", title="Same Tree",
         answer="Check two binary trees are structurally identical with equal values. Recurse: both null -> equal; one null or values differ -> not; else compare left and right subtrees.",
         tags=["same-tree","tree","recursion","dfs","dsa"],
         code='''# True if two binary trees are identical in structure and values.
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def is_same_tree(p, q):
    if p is None and q is None:
        return True
    if p is None or q is None or p.val != q.val:
        return False
    return is_same_tree(p.left, q.left) and is_same_tree(p.right, q.right)''',
         complexity="Time O(n), space O(h).",
         pitfalls="Comparing only values not structure; not handling one-null-one-not.",
         example="is_same_tree(Node(1,Node(2)), Node(1,Node(2))) -> True; vs Node(1,None,Node(2)) -> False."),
    dict(cat="dsa", title="Balanced Binary Tree",
         answer="A tree is height-balanced if every node's two subtrees differ in height by at most 1. Bottom-up: return each subtree's height, propagating -1 as a sentinel once any imbalance is found (short-circuits to O(n)).",
         tags=["balanced-tree","tree","recursion","height","dsa"],
         code='''# True if the binary tree is height-balanced (bottom-up, O(n)).
class Node:
    def __init__(self, val, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

def is_balanced(root):
    def height(node):
        if node is None:
            return 0
        lh = height(node.left)
        if lh == -1:
            return -1                           # left subtree already unbalanced
        rh = height(node.right)
        if rh == -1:
            return -1
        if abs(lh - rh) > 1:
            return -1                           # this node is unbalanced
        return 1 + max(lh, rh)
    return height(root) != -1''',
         complexity="Time O(n), space O(h).",
         pitfalls="Recomputing height top-down (O(n^2)); forgetting to propagate the -1 sentinel.",
         example="is_balanced(Node(1, Node(2, Node(3)), None)) depends on shape; a full tree of depth 2 -> True."),
    dict(cat="glossary", title="Forward proxy vs reverse proxy",
         answer="A FORWARD PROXY sits in front of CLIENTS and forwards their outbound requests to the internet -- it represents the client (used for egress control, caching, anonymity, corporate filtering). A REVERSE PROXY sits in front of SERVERS and receives inbound requests on their behalf -- it represents the server (used for load balancing, TLS termination, caching, request routing, hiding backend topology). Same 'intermediary' idea, opposite side: forward proxies protect/serve clients, reverse proxies protect/serve servers.",
         tags=["forward-proxy","reverse-proxy","load-balancer","networking","architecture"],
         example="A company forward proxy filters and logs employees' outbound web traffic; nginx as a reverse proxy terminates TLS and load-balances inbound requests across app servers -- clients only ever see the reverse proxy, not the backends."),
    dict(cat="glossary", title="API gateway vs load balancer",
         answer="A LOAD BALANCER distributes traffic across identical backend instances at L4/L7, focused on availability and throughput (health checks, connection distribution) -- it doesn't understand your API. An API GATEWAY is an application-aware entry point for (micro)services that adds cross-cutting API concerns: authentication/authorization, rate limiting, request routing by path/version, request/response transformation, aggregation, and API-key/quota management. They compose: a load balancer often sits in front of gateway instances, and the gateway routes to services (each possibly behind its own load balancer). Gateway = API smarts; LB = traffic spreading.",
         tags=["api-gateway","load-balancer","routing","microservices","architecture"],
         example="Requests hit an LB that spreads them across API-gateway nodes; the gateway authenticates the JWT, rate-limits the caller, and routes /orders to the order service and /users to the user service -- routing/auth the LB alone couldn't do."),
    dict(cat="glossary", title="North-south vs east-west traffic",
         answer="Data-center traffic directions. NORTH-SOUTH is traffic between clients OUTSIDE the data center and services inside (ingress/egress) -- what API gateways, WAFs, and edge load balancers handle. EAST-WEST is traffic BETWEEN services WITHIN the data center/cluster (service-to-service) -- which has exploded with microservices and is what service meshes secure (mTLS) and observe. The distinction matters for security (east-west needs zero-trust too, not just a hardened perimeter) and for capacity planning (east-west often dwarfs north-south).",
         tags=["north-south","east-west","traffic","service-mesh","networking"],
         example="A user's request to the API is north-south; the fan-out where that request calls the auth, catalog, pricing, and inventory services internally is east-west -- a mesh applies mTLS to the east-west hops that never leave the cluster."),
    dict(cat="glossary", title="Anycast",
         answer="A network addressing method where the SAME IP address is advertised from MULTIPLE locations, and BGP routing delivers each client to the TOPOLOGICALLY NEAREST one. Used by CDNs, DNS (e.g. 8.8.8.8), and DDoS scrubbing to cut latency (nearest PoP), balance load geographically, and absorb attacks (traffic is spread across many sites). Contrast unicast (one address, one host). Failover is automatic: if a site withdraws its route, clients reroute to the next nearest.",
         tags=["anycast","bgp","cdn","dns","networking"],
         example="Google DNS at 8.8.8.8 is anycast: a user in Tokyo and one in Paris both query 8.8.8.8 but reach different nearby data centers, so each gets a low-latency answer and an outage at one site reroutes to another automatically."),
    dict(cat="ml_coding", title="Huber loss (numpy)",
         answer="Huber loss is quadratic for small errors and linear for large ones, making it ROBUST to outliers (unlike MSE) while staying smooth near zero (unlike MAE). For |error| <= delta it's 0.5*error^2; beyond delta it's delta*(|error| - 0.5*delta).",
         tags=["huber-loss","robust-regression","outliers","loss-function","ml-coding"],
         code='''# Huber loss: quadratic near zero, linear in the tails. ast.parse-only.
import numpy as np

def huber_loss(y_true, y_pred, delta=1.0):
    error = y_true - y_pred
    abs_error = np.abs(error)
    quadratic = np.minimum(abs_error, delta)      # the quadratic-region part
    linear = abs_error - quadratic                # the linear-region overflow
    return np.mean(0.5 * quadratic ** 2 + delta * linear)''',
         complexity="Time O(n), space O(n).",
         pitfalls="A hard if/else instead of the min-split (breaks vectorization/gradients); wrong delta scaling in the linear part.",
         example="huber_loss(np.array([1.,10.]), np.array([1.,1.]), 1.0) -> small robust value (the 9-unit outlier is penalized linearly, not squared)."),
    dict(cat="ml_coding", title="Softmax + cross-entropy combined gradient (numpy)",
         answer="When softmax feeds cross-entropy, the gradient of the loss w.r.t. the LOGITS simplifies beautifully to (softmax_probs - one_hot_labels)/N -- no need to backprop through softmax and log separately. This numerically stable combined form is why frameworks fuse them.",
         tags=["softmax-cross-entropy","gradient","logits","backpropagation","ml-coding"],
         code='''# Combined softmax+cross-entropy gradient w.r.t. logits. ast.parse-only.
import numpy as np

def softmax_ce_grad(logits, y_onehot):
    shifted = logits - np.max(logits, axis=1, keepdims=True)   # stability
    exp = np.exp(shifted)
    probs = exp / np.sum(exp, axis=1, keepdims=True)           # softmax
    n = logits.shape[0]
    return (probs - y_onehot) / n                             # elegant gradient''',
         complexity="Time O(n * classes), space O(n * classes).",
         pitfalls="Backpropagating softmax and log separately (loses the cancellation and stability); forgetting to average by N.",
         example="softmax_ce_grad(logits, y_onehot) returns probs-minus-labels over N; if a class prob is 0.7 and it's the true label, that logit's grad is (0.7-1)/N < 0 (push it up)."),
    dict(cat="ml_coding", title="Adam optimizer update (numpy)",
         answer="Adam combines momentum (1st moment m) and RMSProp (2nd moment v) with bias correction. Per step: m = b1*m + (1-b1)*g; v = b2*v + (1-b2)*g^2; bias-correct both; w -= lr * m_hat / (sqrt(v_hat) + eps). Adaptive per-parameter learning rates.",
         tags=["adam","optimizer","momentum","rmsprop","ml-coding"],
         code='''# One Adam update step. ast.parse-only.
import numpy as np

def adam_step(w, g, m, v, t, lr=1e-3, b1=0.9, b2=0.999, eps=1e-8):
    m = b1 * m + (1 - b1) * g                     # 1st moment (mean of grads)
    v = b2 * v + (1 - b2) * (g * g)               # 2nd moment (uncentered var)
    m_hat = m / (1 - b1 ** t)                     # bias correction
    v_hat = v / (1 - b2 ** t)
    w = w - lr * m_hat / (np.sqrt(v_hat) + eps)   # adaptive step
    return w, m, v''',
         complexity="Time O(size of w), space O(size of w).",
         pitfalls="Omitting bias correction (slow early steps); using t=0 (division by zero in 1-b1^t); eps inside vs outside the sqrt.",
         example="adam_step(w, g, m0, v0, t=1) takes a bias-corrected adaptive step; early steps rely on correction since m,v start at 0."),
    dict(cat="conceptual", title="Why does the softmax+cross-entropy gradient simplify to (probs - labels), and why fuse them?",
         answer="Take the softmax p_i = exp(z_i)/sum_j exp(z_j) over logits z, and cross-entropy loss L = -sum_i y_i log(p_i) for one-hot labels y. You'd expect the gradient dL/dz to be messy because it chains through the log and through softmax's normalization (every logit affects every probability via the shared denominator). But when you actually compute dL/dz_k, two things happen. First, the log and the exp partly cancel. Second -- the key -- the derivative of softmax has a specific structure: dp_i/dz_k = p_i*(1[i=k] - p_k). Plugging that in and using that the labels sum to 1 (one-hot), the whole sum collapses to the strikingly simple dL/dz_k = p_k - y_k. So the gradient of the loss with respect to the logits is just 'predicted probability minus true label' -- for the correct class it's p_true - 1 (negative, pushing that logit up), and for wrong classes it's p_wrong - 0 (positive, pushing them down), scaled by how confident the mistake was. Intuitively the network is nudged exactly in proportion to its error on each class. WHY FUSE THEM in code (a single softmax_cross_entropy op rather than a softmax layer then a separate cross-entropy layer): (1) NUMERICAL STABILITY -- computing log(softmax) naively means exponentiating possibly-large logits then taking a log, which overflows/underflows; the fused log-sum-exp form (log p_i = z_i - max - log sum exp(z_j - max)) stays stable, and you never materialize a probability that rounds to 0 and then take log(0) = -inf. (2) EFFICIENCY AND ACCURACY of the BACKWARD pass -- you emit the closed-form (p - y) directly instead of backpropagating through a division and a log, which both saves compute and avoids the catastrophic cancellation those steps can introduce (e.g. dividing by a tiny p). (3) SIMPLICITY -- one clean gradient. This is why every framework provides a combined cross_entropy_with_logits that takes RAW logits, and why you should NOT put a softmax on your output layer and then apply a separate cross-entropy: you'd lose the stability and risk NaNs. The lesson generalizes: when a loss composes with a final activation, the pair often has a simpler, more stable joint form than either piece alone.",
         tags=["softmax","cross-entropy","gradient","numerical-stability","why"],
         example="With logits giving p=[0.7,0.2,0.1] and true class 0, the fused gradient is [0.7-1, 0.2, 0.1]=[-0.3,0.2,0.1] -- directly usable, whereas a split softmax-then-CE would backprop through log and a division and risk log(0) if a prob underflowed."),
    dict(cat="conceptual", title="Why does Adam need bias correction, and what goes wrong without it?",
         answer="Adam maintains two running exponential moving averages: m (the first moment, an estimate of the mean of the gradients) and v (the second moment, an estimate of the uncentered variance / mean of squared gradients). Both are INITIALIZED TO ZERO. The update is m = b1*m + (1-b1)*g and v = b2*v + (1-b2)*g^2, with b1 around 0.9 and b2 around 0.999. The problem is that because they start at zero, these estimates are BIASED TOWARD ZERO during the early steps, and severely so for v because b2 is very close to 1. Concretely, after the first step m = (1-b1)*g1 = 0.1*g1 -- only a tenth of the actual gradient, even though the best estimate of the mean gradient so far is just g1. For v it's worse: v = (1-b2)*g1^2 = 0.001*g1^2, a thousandth of the true magnitude. If you used these raw, the effective step size lr * m/(sqrt(v)) would be wildly off early in training: the tiny v makes sqrt(v) tiny, so the step could BLOW UP, or the mismatch between under-estimated m and v distorts the direction. Bias correction fixes this exactly: dividing by (1 - b1^t) and (1 - b2^t) rescales the estimates to be UNBIASED. You can derive that the expected value of the raw m_t equals (1 - b1^t) times the true first moment (assuming stationary gradients), so dividing by (1 - b1^t) cancels the bias precisely. Early on, when t is small, (1 - b1^t) is small (e.g. at t=1, 1 - 0.9 = 0.1), so the division multiplies m by 10, undoing the 0.1 attenuation and recovering the right magnitude. As t grows, b1^t -> 0, the correction factor -> 1, and it smoothly becomes a no-op -- it only matters for the first tens/hundreds of steps. WITHOUT correction the symptoms are: overly small and erratic effective learning rates at the start (because v is under-estimated inconsistently with m), slow or unstable early convergence, and sensitivity to the initialization transient. The correction is essentially free (two scalar powers per step) and makes Adam's early steps well-scaled, which is a big part of why Adam works robustly out of the box. A related practical note: some implementations instead warm up the learning rate to achieve a similar effect, and 'AdamW' changes how weight decay interacts, but the bias-correction terms specifically address the zero-initialization transient of the moment estimates.",
         tags=["adam","bias-correction","optimizer","moment-estimates","why"],
         example="At t=1 with b2=0.999 and g=2, raw v=0.001*4=0.004 so sqrt(v)=0.063 -- a huge, wrong step; bias-corrected v_hat=v/(1-0.999)=4 gives sqrt=2, the correct scale -- so without correction the first step would be ~30x too large."),
    dict(cat="behavioral", title="STAR: Thinking big and influencing beyond your team (Think Big)",
         answer="Amazon LP: THINK BIG -- leaders create and communicate a bold direction that inspires results, think differently, and look around corners for ways to serve customers. Show you proposed and drove something bigger than your immediate mandate, aligning others, with a measurable outcome.",
         tags=["behavioral","star","think-big","amazon-lp","influence"],
         example="SITUATION: My team owned one service's logging, but I noticed every team was reinventing observability differently -- inconsistent formats, no shared tracing -- so debugging cross-service incidents took hours of manual correlation. TASK: Nobody owned the org-wide problem; I chose to define a bolder vision than my team's remit: unified structured logging and distributed tracing across all services. ACTION: I wrote a one-page vision doc framing the customer/business cost (slow incident resolution, poor reliability) and a phased path, then socialized it with peer leads and my manager to build a coalition rather than mandating anything. I built a small reference library and instrumented two services end-to-end as a lighthouse example so the value was concrete, not theoretical, and I presented the cross-service trace of a real past incident to show minutes-not-hours debugging. I recruited volunteers from three teams and set a lightweight standard everyone could adopt incrementally. RESULT: Over two quarters the standard spread to most services; mean time to diagnose cross-service incidents dropped substantially because engineers could follow a single trace ID across the system, and the tracing library became an org-supported platform with a real owner. The win came from looking beyond my team's box, articulating a vision compelling enough that others opted in, and de-risking it with a working example before asking for buy-in."),
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
