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
    dict(cat="dsa", title="Isomorphic Strings",
         answer="Two strings are isomorphic if there's a consistent ONE-TO-ONE mapping between their characters preserving order. Track two maps (s->t and t->s); a mismatch in either — a char already mapped to something else — means not isomorphic. Both directions are needed so two chars can't map to the same target.",
         tags=["isomorphic-strings","hash-map","string","dsa"],
         code='''# Are s and t isomorphic (a consistent one-to-one char mapping)?
def is_isomorphic(s, t):
    if len(s) != len(t):
        return False
    map_st, map_ts = {}, {}
    for a, b in zip(s, t):
        if a in map_st and map_st[a] != b:
            return False        # a already maps to a different char
        if b in map_ts and map_ts[b] != a:
            return False        # b already mapped from a different char
        map_st[a] = b
        map_ts[b] = a
    return True''',
         complexity="Time O(n), space O(1) (bounded alphabet).",
         pitfalls="Checking only one direction (lets two chars map to the same target); ignoring unequal lengths.",
         example="is_isomorphic('egg','add') -> True; is_isomorphic('foo','bar') -> False."),
    dict(cat="dsa", title="Word Pattern",
         answer="Check whether a string of words follows a pattern with a BIJECTION between pattern letters and words. Split into words, verify equal length, then maintain char->word and word->char maps — a conflict in either direction breaks the pattern (same idea as isomorphic strings but with words).",
         tags=["word-pattern","hash-map","string","bijection","dsa"],
         code='''# Does s follow the given pattern (bijection pattern-char <-> word)?
def word_pattern(pattern, s):
    words = s.split()
    if len(pattern) != len(words):
        return False
    char_to_word, word_to_char = {}, {}
    for c, w in zip(pattern, words):
        if c in char_to_word and char_to_word[c] != w:
            return False
        if w in word_to_char and word_to_char[w] != c:
            return False
        char_to_word[c] = w
        word_to_char[w] = c
    return True''',
         complexity="Time O(n), space O(unique words).",
         pitfalls="Not checking both directions (two letters -> same word); mismatched counts of letters vs words.",
         example="word_pattern('abba', 'dog cat cat dog') -> True; word_pattern('abba', 'dog cat cat fish') -> False."),
    dict(cat="dsa", title="Ransom Note",
         answer="Determine if a ransom note can be built from the letters of a magazine, each magazine letter usable once. Count the magazine's letters, then consume one per note character; if a needed letter runs out, it's impossible.",
         tags=["ransom-note","hash-map","counting","string","dsa"],
         code='''# Can ransom_note be built from the letters in magazine (each used once)?
from collections import Counter
def can_construct(ransom_note, magazine):
    available = Counter(magazine)
    for ch in ransom_note:
        if available[ch] <= 0:
            return False        # not enough of this letter
        available[ch] -= 1
    return True''',
         complexity="Time O(n + m), space O(alphabet).",
         pitfalls="Reusing a magazine letter more than once; comparing sets instead of counts.",
         example="can_construct('aa','aab') -> True; can_construct('aa','ab') -> False."),
    dict(cat="dsa", title="First Unique Character in a String",
         answer="Return the index of the first non-repeating character, or -1 if none. Two passes: count every character's frequency, then scan left to right for the first character whose count is 1.",
         tags=["first-unique-char","hash-map","counting","string","dsa"],
         code='''# Index of the first non-repeating character, or -1 if none.
from collections import Counter
def first_uniq_char(s):
    counts = Counter(s)
    for i, ch in enumerate(s):
        if counts[ch] == 1:
            return i            # first char that appears exactly once
    return -1''',
         complexity="Time O(n), space O(alphabet).",
         pitfalls="Returning the character instead of its index; a single pass can't know future repeats.",
         example="first_uniq_char('leetcode') -> 0; first_uniq_char('aabb') -> -1."),
    dict(cat="dsa", title="Intersection of Two Arrays II",
         answer="Return the intersection of two arrays INCLUDING duplicates — each element appears min(count in A, count in B) times. Count one array, then walk the other consuming matches from the counts.",
         tags=["intersection-arrays","hash-map","counting","array","dsa"],
         code='''# Intersection of two arrays including duplicates (min of the counts).
from collections import Counter
def intersect(nums1, nums2):
    counts = Counter(nums1)
    result = []
    for n in nums2:
        if counts[n] > 0:
            result.append(n)
            counts[n] -= 1      # consume one occurrence
    return result''',
         complexity="Time O(n + m), space O(min(n, m)).",
         pitfalls="Deduping (this variant keeps duplicates); not decrementing the count after a match.",
         example="intersect([1,2,2,1],[2,2]) -> [2,2]."),
    dict(cat="dsa", title="Is Subsequence",
         answer="Check whether s is a subsequence of t — s's characters appear in t in the same order (not necessarily contiguous). Two pointers: sweep t and advance the s-pointer on each match; s is a subsequence iff the pointer reaches the end of s.",
         tags=["is-subsequence","two-pointers","string","dsa"],
         code='''# Is s a subsequence of t? (chars of s appear in order within t)
def is_subsequence(s, t):
    i = 0
    for ch in t:
        if i < len(s) and s[i] == ch:
            i += 1              # matched the next char of s
    return i == len(s)          # matched all of s''',
         complexity="Time O(len(t)), space O(1).",
         pitfalls="Requiring contiguity (that's substring); advancing the s-pointer without a match.",
         example="is_subsequence('abc','ahbgdc') -> True; is_subsequence('axc','ahbgdc') -> False."),
    dict(cat="dsa", title="Valid Palindrome II (delete at most one)",
         answer="Determine if a string can become a palindrome by deleting AT MOST ONE character. Use two pointers inward; on the first mismatch, try skipping EITHER the left or the right character and check if the remainder is a palindrome. If no mismatch ever occurs, it already is one.",
         tags=["valid-palindrome","two-pointers","greedy","string","dsa"],
         code='''# Can s become a palindrome by deleting at most ONE character?
def valid_palindrome(s):
    def is_pal(lo, hi):
        while lo < hi:
            if s[lo] != s[hi]:
                return False
            lo += 1; hi -= 1
        return True
    left, right = 0, len(s) - 1
    while left < right:
        if s[left] != s[right]:
            # try skipping either the left or the right mismatched char
            return is_pal(left + 1, right) or is_pal(left, right - 1)
        left += 1; right -= 1
    return True''',
         complexity="Time O(n), space O(1).",
         pitfalls="Trying only one side of the mismatch; attempting more than one deletion.",
         example="valid_palindrome('abca') -> True (delete 'c' or 'b'); valid_palindrome('abc') -> False."),
    dict(cat="dsa", title="String Compression (in place)",
         answer="Compress runs of repeated characters IN PLACE: a run of a character followed by its count when >1 (e.g. 'aaabb' -> 'a3b2'), returning the new length. Use a read pointer to count each run and a write pointer to emit the char and, for runs longer than 1, each digit of the count.",
         tags=["string-compression","two-pointers","in-place","string","dsa"],
         code='''# Compress runs of repeated chars in place: 'aaabb' -> 'a3b2'; return length.
def compress(chars):
    write = 0
    read = 0
    n = len(chars)
    while read < n:
        ch = chars[read]
        count = 0
        while read < n and chars[read] == ch:
            read += 1; count += 1     # count the current run
        chars[write] = ch; write += 1
        if count > 1:
            for digit in str(count):  # write each digit of the run length
                chars[write] = digit; write += 1
    return write''',
         complexity="Time O(n), space O(1).",
         pitfalls="Writing '1' for single characters (only counts >1); multi-digit counts need each digit.",
         example="chars=['a','a','b','b','c','c','c'] -> compress -> 6, with chars starting ['a','2','b','2','c','3']."),
    dict(cat="glossary", title="Vector clocks",
         answer="A mechanism to track CAUSALITY across distributed nodes without synchronized clocks. Each node keeps a vector of counters (one per node), increments its own on each event, and merges (element-wise max) on message receipt. Comparing two vectors tells you whether one event happened-before another or whether they're CONCURRENT (conflicting). Used to detect conflicting replica writes (Dynamo).",
         tags=["vector-clocks","causality","distributed-systems","conflict-detection"],
         example="Two replicas update the same key concurrently; their vector clocks are incomparable (neither dominates), so the system flags a conflict and keeps both versions for the client to resolve."),
    dict(cat="glossary", title="Snapshot isolation",
         answer="A transaction isolation level where each transaction reads from a consistent SNAPSHOT of the database as of its start, and writes are conflict-checked at commit. It prevents dirty and non-repeatable reads and gives high concurrency (readers don't block writers, via MVCC), but permits the WRITE SKEW anomaly — so it's weaker than serializable.",
         tags=["snapshot-isolation","mvcc","transactions","isolation-levels","database"],
         example="Two on-call doctors each see '2 on call' in their snapshot and each removes themselves — snapshot isolation allows this write skew, leaving zero on call; serializable would forbid it."),
    dict(cat="glossary", title="Backpressure",
         answer="A flow-control mechanism where a slow CONSUMER signals upstream producers to slow down, preventing unbounded queue growth and memory blowup when demand exceeds capacity. Rather than buffering forever (and crashing), the system pushes back — blocking, dropping, or rate-limiting the producer. It's core to reactive streams and stable pipelines.",
         tags=["backpressure","flow-control","streaming","reliability"],
         example="A stream processor can't keep up with Kafka; backpressure pauses its fetch (letting lag grow) instead of buffering unbounded records in memory and running out of memory."),
    dict(cat="glossary", title="Dead-letter queue (DLQ)",
         answer="A separate queue where messages that repeatedly FAIL processing (after max retries) or can't be delivered are set aside — instead of blocking the main queue or being silently lost. Engineers inspect, fix, and replay them. It isolates 'poison' messages so one bad message doesn't stall the whole pipeline.",
         tags=["dead-letter-queue","dlq","messaging","reliability","retries"],
         example="A malformed order event that throws on every attempt is moved to the DLQ after 5 retries, so the worker keeps processing good messages while the team investigates the poison one."),
    dict(cat="glossary", title="SLI / SLO / SLA (+ error budget)",
         answer="The reliability vocabulary. An SLI (indicator) is a measured metric like success rate or p99 latency. An SLO (objective) is your internal target for it (e.g. 99.9% success). An SLA (agreement) is a contractual promise to customers with penalties, usually looser than the SLO. The ERROR BUDGET = 1 - SLO — the unreliability you're allowed to 'spend' on risk/releases before you must freeze changes.",
         tags=["slo","sla","sli","error-budget","reliability","sre"],
         example="A 99.9% availability SLO gives a ~43-minute monthly error budget; if a botched deploy burns it, the team halts feature launches and focuses on reliability until it recovers."),
    dict(cat="conceptual", title="Why report p99/tail latency instead of average latency?",
         answer="Averages HIDE the bad experiences. A 50ms mean can coexist with 1% of requests taking 2 seconds — and those slow requests hit real users, often the most active ones (more requests = higher chance of hitting the tail). Latency distributions are right-skewed, so the mean doesn't reflect the worst-case user. PERCENTILES (p99, p99.9) directly answer 'how bad is it for the unluckiest 1%?' — the SLO-relevant question. Tail latency also COMPOUNDS: a page making 100 backend calls almost certainly hits at least one p99-slow call, so the tail becomes the common case at the page level. That's why SLOs target p99, not the average.",
         tags=["tail-latency","p99","percentiles","latency","why"],
         example="Two services both average 50ms, but one has p99=60ms and the other p99=2s; the average calls them equal while users of the second see frequent multi-second stalls — only the percentile exposes it."),
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
