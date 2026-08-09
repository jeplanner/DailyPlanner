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
    dict(cat="dsa", title="Minimum Operations to Make Array Equal to Target",
         answer="Given nums and target of equal length, each op picks a contiguous subarray and adds +1 or -1 to every element. Minimum ops to turn nums into target. Work on the DIFFERENCE array d = target - nums: adjacent elements sharing the same sign can be raised/lowered together for free, so the cost is the sum of |d[0]| plus each step-up in magnitude between same-sign neighbors — equivalently sum of positive jumps for rises and falls handled by sign changes.",
         tags=["min-operations-target","difference-array","greedy","array","dsa"],
         code='''# Min contiguous +1/-1 range ops to turn nums into target (difference array).
def minimum_operations(nums, target):
    d = [t - n for t, n in zip(target, nums)]   # needed delta per index
    ops = abs(d[0])                              # first element paid in full
    for i in range(1, len(d)):
        prev, cur = d[i - 1], d[i]
        if cur >= 0 and prev >= 0:               # both non-negative: only pay the rise
            ops += max(0, cur - prev)
        elif cur <= 0 and prev <= 0:             # both non-positive: pay the extra drop
            ops += max(0, prev - cur)
        else:                                    # sign flip: pay the new run from zero
            ops += abs(cur)
    return ops''',
         complexity="Time O(n), space O(n).",
         pitfalls="Treating rises and falls the same; not resetting cost at a sign change between neighbors.",
         example="minimum_operations([3,5,1,2], [4,6,2,4]) -> 2 (raise [0..3] by 1, then raise [3] by 1)."),
    dict(cat="dsa", title="Minimum Sum of Four Digit Number After Splitting Digits",
         answer="Given a four-digit number, split its digits into two new numbers (using all four digits) to minimize their sum. Sort the digits ascending; the two smallest become the tens places and the two largest the units places: new1 = 10*d0 + d2, new2 = 10*d1 + d3.",
         tags=["min-sum-four-digit","greedy","sorting","digits","dsa"],
         code='''# Split a 4-digit number's digits into two numbers with minimum sum.
def minimum_sum(num):
    digits = sorted(str(num))          # ascending digit characters
    # smallest two digits go to the tens places, largest two to the units
    new1 = int(digits[0]) * 10 + int(digits[2])
    new2 = int(digits[1]) * 10 + int(digits[3])
    return new1 + new2''',
         complexity="Time O(1) (four digits), space O(1).",
         pitfalls="Putting a large digit in a tens place; forgetting all four digits must be used.",
         example="minimum_sum(2932) -> 52  (from 29 + 23)."),
    dict(cat="dsa", title="Sum of Digits in Base 10 After Convert",
         answer="Convert each letter of s to its 1-indexed alphabet position, concatenate those numbers into one string, then repeat k times: replace the number by the sum of its digits. Return the final number.",
         tags=["sum-digits-convert","string","digits","simulation","dsa"],
         code='''# Encode letters as positions, then sum digits k times.
def get_lucky(s, k):
    # a->1, b->2, ...; concatenate the numeric positions
    num = ''.join(str(ord(c) - ord('a') + 1) for c in s)
    for _ in range(k):
        num = str(sum(int(d) for d in num))   # collapse to digit-sum
    return int(num)''',
         complexity="Time O(len(s) + k * digits), space O(len(s)).",
         pitfalls="Off-by-one in the a->1 mapping; summing letters before concatenating positions.",
         example="get_lucky('iiii', 2) -> 36 -> then 9  (positions 9999 -> 36 -> 9)."),
    dict(cat="dsa", title="Split a Number into Two Parts with Minimum Sum",
         answer="Given a positive integer, distribute its digits into two numbers num1 and num2 (each digit used once) to minimize num1 + num2. Sort digits ascending and DEAL them alternately into the two numbers — this keeps both numbers short and puts small digits in high places.",
         tags=["split-min-sum","greedy","sorting","digits","dsa"],
         code='''# Deal sorted digits alternately into two numbers to minimize their sum.
def split_num(num):
    digits = sorted(str(num))          # ascending
    a, b = '', ''
    for i, d in enumerate(digits):
        if i % 2 == 0:
            a += d                      # alternate digits between the two numbers
        else:
            b += d
    return int(a or '0') + int(b or '0')''',
         complexity="Time O(k log k) for k digits, space O(k).",
         pitfalls="Filling one number fully before the other (unbalanced lengths raise the sum); leading-zero edge with empty strings.",
         example="split_num(4325) -> 59  (sorted 2345 -> 24 + 35)."),
    dict(cat="dsa", title="Points That Intersect With Cars",
         answer="Given car intervals [start, end] on a number line, count the integer points covered by at least one car. DIFFERENCE ARRAY: +1 at start, -1 at end+1; prefix-sum and count positions with coverage > 0. (Small range, so a boolean/marking sweep also works.)",
         tags=["points-intersect-cars","difference-array","prefix-sum","intervals","dsa"],
         code='''# Count integer points covered by at least one car interval (difference array).
def number_of_points(nums):
    diff = [0] * 102                   # coordinates 1..100, +1 headroom
    for start, end in nums:
        diff[start] += 1               # coverage begins
        diff[end + 1] -= 1             # coverage ends after 'end'
    covered = 0
    running = 0
    for change in diff:
        running += change
        if running > 0:
            covered += 1
    return covered''',
         complexity="Time O(n + range), space O(range).",
         pitfalls="Decrementing at 'end' instead of end+1 (drops the last covered point); double-counting overlapping cars.",
         example="number_of_points([[3,6],[1,5],[4,7]]) -> 7  (points 1..7)."),
    dict(cat="dsa", title="Non-decreasing Array With One Modification",
         answer="Check whether an array can become non-decreasing by modifying at most ONE element. Scan for a drop nums[i] < nums[i-1]; on the first drop, greedily lower nums[i-1] to nums[i] when safe (nums[i-2] <= nums[i]), otherwise raise nums[i] to nums[i-1]. A second drop means it's impossible.",
         tags=["non-decreasing-array","greedy","array","dsa"],
         code='''# Can the array become non-decreasing by changing at most one element?
def check_possibility(nums):
    changed = False
    for i in range(1, len(nums)):
        if nums[i] < nums[i - 1]:
            if changed:                # a second violation -> impossible
                return False
            changed = True
            # prefer lowering nums[i-1]; if that breaks order, raise nums[i]
            if i < 2 or nums[i - 2] <= nums[i]:
                nums[i - 1] = nums[i]
            else:
                nums[i] = nums[i - 1]
    return True''',
         complexity="Time O(n), space O(1).",
         pitfalls="Always raising nums[i] (misses cases needing to lower the predecessor); forgetting the i<2 boundary.",
         example="check_possibility([4,2,3]) -> True; check_possibility([4,2,1]) -> False."),
    dict(cat="dsa", title="Minimum Deletions to Make Character Frequencies Unique",
         answer="Delete the fewest characters so that no two distinct letters share the same frequency. Count frequencies; process them and whenever a frequency is already taken, decrement (delete) until it hits an unused value or zero, tallying deletions.",
         tags=["min-deletions-unique-freq","greedy","hash-set","counting","dsa"],
         code='''# Fewest deletions so all character frequencies are distinct.
def min_deletions(s):
    from collections import Counter
    freqs = Counter(s)
    used = set()                       # frequencies already claimed
    deletions = 0
    for f in freqs.values():
        while f > 0 and f in used:
            f -= 1                      # delete one char to lower the frequency
            deletions += 1
        used.add(f)
    return deletions''',
         complexity="Time O(n + k^2) worst case, space O(k).",
         pitfalls="Adding 0 to 'used' repeatedly is fine, but forgetting the f>0 guard loops forever; not deleting down past collisions.",
         example="min_deletions('aaabbbcc') -> 2  (e.g. reduce to 3,2,1... one valid target)."),
    dict(cat="dsa", title="Remove Duplicate Letters",
         answer="Return the lexicographically smallest result that contains each distinct letter of s exactly once. MONOTONIC STACK: track last occurrence of each char; push chars, popping a larger top when the current char is smaller AND the popped char appears again later; skip chars already on the stack.",
         tags=["remove-duplicate-letters","monotonic-stack","greedy","string","dsa"],
         code='''# Lexicographically smallest string with each distinct letter exactly once.
def remove_duplicate_letters(s):
    last = {c: i for i, c in enumerate(s)}   # last index of each char
    stack = []
    seen = set()
    for i, c in enumerate(s):
        if c in seen:
            continue                    # already placed this letter
        # pop bigger letters that still appear later, to go smaller
        while stack and stack[-1] > c and last[stack[-1]] > i:
            seen.discard(stack.pop())
        stack.append(c)
        seen.add(c)
    return ''.join(stack)''',
         complexity="Time O(n), space O(1) (bounded alphabet).",
         pitfalls="Popping a letter that does not reappear later (loses it); not skipping letters already on the stack.",
         example="remove_duplicate_letters('cbacdcbc') -> 'acdb'."),
    dict(cat="dsa", title="Minimum Add to Make Parentheses Valid",
         answer="Return the minimum number of parentheses to insert so the string becomes valid. One pass: keep an OPEN counter; '(' increments it, ')' decrements it but if it would go negative you need an inserted '(' (tally it and clamp to 0). Answer = insertions + leftover open.",
         tags=["min-add-parentheses","stack-counter","greedy","string","dsa"],
         code='''# Minimum parentheses to add to make the string valid.
def min_add_to_make_valid(s):
    open_needed = 0                    # unmatched ')' that need a '(' inserted
    open_count = 0                     # currently unmatched '('
    for ch in s:
        if ch == '(':
            open_count += 1
        else:
            if open_count > 0:
                open_count -= 1        # matches an earlier '('
            else:
                open_needed += 1       # no '(' to match -> must insert one
    return open_needed + open_count''',
         complexity="Time O(n), space O(1).",
         pitfalls="Letting the open counter go negative instead of counting an insertion; forgetting leftover unmatched '('.",
         example="min_add_to_make_valid('()))((') -> 4."),
    dict(cat="dsa", title="Maximum Score After Splitting a String",
         answer="Split a binary string into left and right (both non-empty); score = zeros on the left + ones on the right. Maximize it. Precompute total ones; sweep split points maintaining left zeros and left ones, scoring left_zeros + (total_ones - left_ones).",
         tags=["max-score-splitting-string","prefix-sum","string","dsa"],
         code='''# Max (left zeros + right ones) over all non-empty left/right splits.
def max_score(s):
    total_ones = s.count('1')
    left_zeros = 0
    left_ones = 0
    best = 0
    for i in range(len(s) - 1):        # split after i, both sides non-empty
        if s[i] == '0':
            left_zeros += 1
        else:
            left_ones += 1
        best = max(best, left_zeros + (total_ones - left_ones))
    return best''',
         complexity="Time O(n), space O(1).",
         pitfalls="Allowing an empty right side (loop must stop at len-1); recomputing right ones each step.",
         example="max_score('011101') -> 5."),
    dict(cat="dsa", title="Minimum Bit Flips to Convert Number",
         answer="Count bit positions where start and goal differ — that many single-bit flips convert one to the other. XOR the two numbers and count set bits (Hamming distance).",
         tags=["min-bit-flips","xor","bit-manipulation","hamming-distance","dsa"],
         code='''# Number of bit flips to turn start into goal (Hamming distance).
def min_bit_flips(start, goal):
    x = start ^ goal                   # 1s mark differing bit positions
    count = 0
    while x:
        x &= x - 1                     # clear the lowest set bit
        count += 1
    return count''',
         complexity="Time O(number of set bits), space O(1).",
         pitfalls="Comparing decimal magnitude instead of bits; forgetting XOR isolates exactly the differing positions.",
         example="min_bit_flips(10, 7) -> 3  (1010 vs 0111)."),
    dict(cat="dsa", title="Number of Steps to Reduce a Number in Binary to One",
         answer="Given a binary string, count steps to reduce it to 1 where an even number is halved (drop trailing 0) and an odd number gets +1. Process from the least-significant bit tracking a carry: each bit costs a step; a set bit (with carry) triggers an add that propagates.",
         tags=["steps-binary-to-one","bit-manipulation","simulation","string","dsa"],
         code='''# Steps to reduce a binary string to 1 (even->/2, odd->+1).
def num_steps(s):
    steps = 0
    carry = 0
    # walk from least significant bit down to the second-most significant
    for i in range(len(s) - 1, 0, -1):
        bit = int(s[i]) + carry
        if bit == 1:                   # odd: +1 (a step) then divide (a step); carry set
            steps += 2
            carry = 1
        else:                          # even: just divide (a step)
            steps += 1
    return steps + carry               # final leading bit may need one +1 carry-out''',
         complexity="Time O(n), space O(1).",
         pitfalls="Converting the whole string to int for huge inputs; mishandling the carry out of the leading bit.",
         example="num_steps('1101') -> 6."),
    dict(cat="glossary", title="SAML",
         answer="Security Assertion Markup Language — an XML-based standard for exchanging authentication and authorization between an IDENTITY PROVIDER (IdP) and a SERVICE PROVIDER (SP), the classic enterprise SSO protocol. The IdP authenticates the user and issues a signed SAML ASSERTION (an XML document of identity + attributes) the SP trusts. Browser-based SSO uses redirects/POST with the assertion. Contrast with OIDC (JSON/JWT, OAuth2-based, better for mobile/APIs); SAML is heavier XML but entrenched in enterprise B2B.",
         tags=["saml","sso","identity-provider","assertion","authentication"],
         example="An employee clicks Salesforce; Salesforce (SP) redirects to Okta (IdP), which authenticates and posts back a signed SAML assertion — Salesforce trusts it and logs the user in without a separate password."),
    dict(cat="glossary", title="API key vs OAuth",
         answer="An API KEY is a single long-lived secret string identifying an APPLICATION (not a user); simple, but coarse (no per-user scope), hard to rotate, and dangerous if leaked. OAUTH 2.0 is a delegated-authorization framework issuing short-lived ACCESS TOKENS (often after a user consents) with granular SCOPES, refreshable and revocable, representing a user OR an app (client-credentials). Use API keys for simple server-to-server or public data; use OAuth when you need user consent, scoped/least-privilege access, token expiry, and revocation.",
         tags=["api-key","oauth","access-token","scopes","authorization"],
         example="A weather widget uses a plain API key to fetch public forecasts; a 'Sign in with Google' app uses OAuth so the user consents to specific scopes (email, calendar) and issues short-lived, revocable tokens instead of a static key."),
    dict(cat="glossary", title="Refresh token rotation",
         answer="A security practice where each use of a REFRESH TOKEN issues a NEW refresh token and invalidates the old one, so a refresh token is single-use. If a stolen refresh token is replayed after the legitimate client already rotated it, the auth server detects the reuse of a retired token and REVOKES the whole token family — containing theft. Pairs with short-lived access tokens; essential for public clients (SPAs, mobile) that can't keep a client secret.",
         tags=["refresh-token-rotation","oauth","token-reuse-detection","security","authentication"],
         example="A mobile app refreshes: server returns a new refresh token and retires the old. An attacker who copied the old one tries it, the server sees a retired token reused, and revokes every token in that family — logging the attacker (and user) out."),
    dict(cat="glossary", title="Dead letter queue",
         answer="A DEAD LETTER QUEUE (DLQ) / dead letter exchange is a separate queue where messages land after they can't be processed — repeated consumer failures exceeding a retry limit, expiry (TTL), or a message that would overflow a queue. It quarantines POISON MESSAGES so one bad message doesn't block or infinitely retry the main queue, and gives operators a place to inspect, fix, and replay failures. Core to resilient async messaging (SQS, RabbitMQ, Kafka via a DLT topic).",
         tags=["dead-letter-queue","dlq","poison-message","messaging","reliability"],
         example="An order-processing consumer fails 5 times on a malformed message; the broker moves it to the DLQ instead of redelivering forever, so healthy orders keep flowing and an engineer can inspect and replay the bad one later."),
    dict(cat="glossary", title="Competing consumers",
         answer="A messaging pattern where MULTIPLE consumer instances read from the SAME queue, and each message is delivered to exactly ONE of them — the broker load-balances work across the pool. It scales throughput horizontally (add consumers) and adds fault tolerance (a dead consumer's unacked messages redeliver to others). Trade-off: it breaks strict global ordering (parallel consumers finish out of order) unless you partition by key so related messages go to one consumer.",
         tags=["competing-consumers","message-queue","load-balancing","scalability","messaging"],
         example="Ten worker instances all pull from an 'image-resize' queue; each job goes to whichever worker is free, so throughput scales with workers — but two resize jobs may finish out of submission order."),
    dict(cat="glossary", title="Message ordering guarantees",
         answer="What order consumers see messages in. GLOBAL ordering (all messages strictly in order) usually forces a single partition/consumer and kills parallelism. Most systems offer PARTITION/KEY ordering: messages sharing a key (e.g. user_id) are ordered within their partition while different keys process in parallel (Kafka partitions, SQS FIFO message groups). NONE/best-effort trades ordering for throughput. Idempotent consumers and sequence numbers help when ordering can't be guaranteed end-to-end.",
         tags=["message-ordering","partition-key","kafka","fifo","messaging"],
         example="Kafka keyed by account_id: all events for account A land in one partition and stay ordered, while accounts A, B, C process concurrently across partitions — per-account order without serializing the whole stream."),
    dict(cat="ml_coding", title="Layer Normalization (numpy)",
         answer="Layer norm normalizes each SAMPLE across its FEATURES (unlike batch norm, which normalizes each feature across the batch) — making it batch-size-independent and the norm of choice for Transformers/RNNs. For each row: subtract the row mean, divide by the row std (with epsilon), then scale (gamma) and shift (beta).",
         tags=["layer-normalization","layernorm","transformers","normalization","ml-coding"],
         code='''# Layer normalization over the feature axis (per-sample). ast.parse-only.
import numpy as np

def layer_norm(x, gamma, beta, eps=1e-5):
    # x: (batch, features); normalize each row across its features
    mean = x.mean(axis=1, keepdims=True)          # per-sample mean
    var = x.var(axis=1, keepdims=True)            # per-sample variance
    x_hat = (x - mean) / np.sqrt(var + eps)       # standardize each row
    return gamma * x_hat + beta                   # learnable scale and shift''',
         complexity="Time O(batch * features), space O(batch * features).",
         pitfalls="Normalizing over the batch axis (that's batch norm); dropping keepdims so broadcasting misaligns; omitting eps (divide-by-zero on constant rows).",
         example="layer_norm(np.array([[1.,2.,3.]]), 1.0, 0.0) -> approx [[-1.22, 0, 1.22]] (row standardized)."),
    dict(cat="ml_coding", title="Batch Normalization forward (numpy)",
         answer="Batch norm normalizes each FEATURE across the BATCH, reducing internal covariate shift and enabling higher learning rates. Training: use the batch mean/var and update running estimates. Inference: use the running mean/var. Then scale (gamma) and shift (beta).",
         tags=["batch-normalization","batchnorm","normalization","training","ml-coding"],
         code='''# Batch normalization forward (per-feature across the batch). ast.parse-only.
import numpy as np

def batch_norm_forward(x, gamma, beta, running_mean, running_var,
                       training=True, momentum=0.9, eps=1e-5):
    if training:
        mean = x.mean(axis=0)                     # per-feature batch mean
        var = x.var(axis=0)                       # per-feature batch variance
        # update running stats for inference use later
        running_mean = momentum * running_mean + (1 - momentum) * mean
        running_var = momentum * running_var + (1 - momentum) * var
    else:
        mean, var = running_mean, running_var     # frozen stats at inference
    x_hat = (x - mean) / np.sqrt(var + eps)       # standardize each feature
    out = gamma * x_hat + beta                    # scale and shift
    return out, running_mean, running_var''',
         complexity="Time O(batch * features), space O(batch * features).",
         pitfalls="Using batch stats at inference (non-deterministic outputs); forgetting to update running stats; wrong axis (0 = across batch).",
         example="At inference, batch_norm_forward(x, gamma, beta, rm, rv, training=False) uses frozen running_mean/var so each input maps deterministically."),
    dict(cat="ml_coding", title="ReLU and its gradient (numpy)",
         answer="ReLU(x) = max(0, x): cheap, non-saturating for positive inputs, and the default hidden activation. Its gradient is 1 where x>0 and 0 where x<=0, so in backprop you pass the upstream gradient through only the positions that were active in the forward pass.",
         tags=["relu","activation","gradient","backpropagation","ml-coding"],
         code='''# ReLU forward and backward. ast.parse-only.
import numpy as np

def relu(x):
    return np.maximum(0, x)                       # zero out negatives

def relu_backward(grad_output, x):
    # gradient flows only where the input was positive
    grad = grad_output.copy()
    grad[x <= 0] = 0                              # dead where x<=0
    return grad''',
         complexity="Time O(n), space O(n).",
         pitfalls="Passing gradient where x<=0 (dying-ReLU handled wrong); using > vs >= inconsistently at exactly 0; mutating grad_output in place unintentionally.",
         example="relu(np.array([-2.,0.,3.])) -> [0,0,3]; relu_backward(np.array([1.,1.,1.]), np.array([-2.,0.,3.])) -> [0,0,1]."),
    dict(cat="ml_coding", title="One-hot encoding (numpy)",
         answer="Turn integer class labels into one-hot vectors: a matrix where row i has a 1 in column labels[i] and 0 elsewhere. Standard for categorical targets fed to cross-entropy. Build a zeros matrix of shape (n, num_classes) and set the indexed positions to 1.",
         tags=["one-hot-encoding","categorical","preprocessing","numpy","ml-coding"],
         code='''# One-hot encode integer labels into a (n, num_classes) matrix. ast.parse-only.
import numpy as np

def one_hot(labels, num_classes):
    n = len(labels)
    encoded = np.zeros((n, num_classes))          # all zeros
    encoded[np.arange(n), labels] = 1             # set one 1 per row
    return encoded''',
         complexity="Time O(n), space O(n * num_classes).",
         pitfalls="num_classes too small for the max label (index error); using a Python loop instead of fancy indexing; labels not zero-indexed.",
         example="one_hot(np.array([0,2,1]), 3) -> [[1,0,0],[0,0,1],[0,1,0]]."),
    dict(cat="ml_coding", title="Standardize features / z-score (numpy)",
         answer="Standardization rescales each FEATURE to zero mean and unit variance: (x - mean) / std, computed per column on the TRAINING set and reused on test data. Essential for distance- and gradient-based models (KNN, SVM, logistic regression) so no feature dominates by scale.",
         tags=["standardization","z-score","feature-scaling","preprocessing","ml-coding"],
         code='''# Standardize columns to zero mean / unit variance. ast.parse-only.
import numpy as np

def standardize(x_train, x_test=None, eps=1e-8):
    mean = x_train.mean(axis=0)                   # per-feature mean (train only)
    std = x_train.std(axis=0)                     # per-feature std (train only)
    train_scaled = (x_train - mean) / (std + eps) # z-score the train set
    if x_test is None:
        return train_scaled
    test_scaled = (x_test - mean) / (std + eps)   # reuse train stats on test
    return train_scaled, test_scaled''',
         complexity="Time O(n * features), space O(n * features).",
         pitfalls="Fitting mean/std on the full dataset (test leakage); per-row instead of per-column; dividing by zero on constant features (add eps).",
         example="standardize(np.array([[1.],[2.],[3.]])) -> [[-1.22],[0.],[1.22]] (column standardized)."),
    dict(cat="conceptual", title="Why does layer normalization work better than batch normalization for Transformers and RNNs?",
         answer="Batch norm normalizes each feature using statistics computed ACROSS THE BATCH, which creates two problems for sequence models. First, DEPENDENCE ON BATCH SIZE and composition: with small batches (common for long sequences that eat memory) the batch mean/var are noisy estimates, and the model's output for one example depends on the other examples in its batch — undesirable and non-deterministic without careful running stats. Second, VARIABLE SEQUENCE LENGTHS: in RNNs/Transformers different timesteps and padded lengths make 'the same feature across the batch' ill-defined — which timesteps do you pool over? Batch norm has no clean answer, and it couples statistics across time. LAYER NORM sidesteps both by normalizing across the FEATURE dimension of each individual token/sample independently: every example's normalization uses only its own activations, so it's completely independent of batch size, batch composition, and sequence length, and behaves identically in training and inference (no running stats to maintain). This per-token stability is exactly what deep residual Transformer stacks need — each sublayer's input is well-conditioned regardless of what else is in the batch. The trade-off: layer norm can't exploit cross-batch feature statistics the way batch norm does for CNNs (where batch norm still usually wins on images), so the choice is architecture-dependent: batch norm for CNNs/vision with decent batch sizes, layer norm for sequence models and small/variable batches.",
         tags=["layer-norm","batch-norm","transformers","normalization","why"],
         example="A Transformer trained with batch size 8 on variable-length sentences: layer norm normalizes each token by its own 512 features (identical in train and inference), while batch norm would compute noisy per-feature stats over just 8 examples of differing lengths and behave differently at inference — so layer norm gives stable, batch-independent training."),
    dict(cat="behavioral", title="STAR: Diving deep to find a root cause others missed (Dive Deep)",
         answer="Amazon LP: DIVE DEEP — leaders operate at all levels, stay connected to the details, audit frequently, and are skeptical when metrics and anecdotes differ; no task is beneath them. Structure the answer as Situation, Task, Action, Result, showing you went past the surface symptom to the true root cause with data.",
         tags=["behavioral","star","dive-deep","amazon-lp","root-cause"],
         example="SITUATION: Our checkout service's error rate spiked to 3% intermittently and the team blamed a flaky downstream payment API, planning to just add retries. TASK: As the on-call owner I wasn't convinced retries treated the cause, so I took on finding why the errors clustered. ACTION: I pulled traces for the failed requests and noticed the failures all shared one database read replica; correlating with replica lag metrics, I found the errors spiked exactly when replica lag crossed ~2s, causing a stale read that failed a validation check — not the payment API at all. I reproduced it by artificially lagging a replica, confirmed the causal link, and fixed it by routing that consistency-sensitive read to the primary and adding a lag-based health check to pull lagging replicas from rotation. RESULT: The error rate dropped from 3% to under 0.05% and stayed there; the retry band-aid the team had planned would have masked the stale-read bug and left customers with silent failures. I wrote up the replica-lag failure mode so other services could add the same health check.")
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
