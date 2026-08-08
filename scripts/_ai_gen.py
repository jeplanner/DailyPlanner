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
    dict(cat="dsa", title="Repeated Substring Pattern",
         answer="Decide whether a string can be constructed by repeating one of its substrings. Slick trick: concatenate the string with itself and strip the first and last characters; the original string appears in that (2n-2)-length string IFF it's periodic.",
         tags=["repeated-substring","string","pattern","dsa"],
         code='''# Can the string be built by repeating one of its substrings?
def repeated_substring_pattern(s):
    doubled = (s + s)[1:-1]      # concatenate, then strip one char from each end
    return s in doubled          # s reappears iff it is periodic''',
         complexity="Time O(n) (with a good substring search), space O(n).",
         pitfalls="Not stripping both ends (would always match at position 0); brute-forcing all divisors is slower.",
         example="repeated_substring_pattern('abab') -> True; repeated_substring_pattern('aba') -> False."),
    dict(cat="dsa", title="Power of Three",
         answer="Determine if n is a power of three WITHOUT loops or logs. Since 3 is prime, any power of three divides the largest power of three that fits in a 32-bit int (3^19 = 1162261467). So n>0 is a power of three iff 1162261467 % n == 0.",
         tags=["power-of-three","math","number-theory","dsa"],
         code='''# Is n a power of three? (no loops: check divisibility of the max power)
def is_power_of_three(n):
    if n <= 0:
        return False
    # 3^19 = 1162261467 is the largest power of 3 fitting in a 32-bit int
    return 1162261467 % n == 0''',
         complexity="Time O(1), space O(1).",
         pitfalls="Only works because 3 is prime (this trick fails for composite bases); n must be > 0.",
         example="is_power_of_three(27) -> True; is_power_of_three(45) -> False."),
    dict(cat="dsa", title="Number Complement",
         answer="Flip every bit of a positive integer WITHIN its own bit-length (leading zeros aren't flipped). Build a mask of all 1s the same width as num, then XOR — XOR with 1 flips a bit, so every bit inside the width toggles.",
         tags=["number-complement","bit-manipulation","xor","dsa"],
         code='''# Flip every bit of a positive integer within its bit-length.
def find_complement(num):
    mask = 1
    while mask < num:
        mask = (mask << 1) | 1   # grow a mask of all 1s the width of num
    return num ^ mask            # XOR flips every bit inside that width''',
         complexity="Time O(bits), space O(1).",
         pitfalls="Flipping the leading zeros (mask must match num's width); off-by-one on the mask.",
         example="find_complement(5) -> 2  (101 -> 010)."),
    dict(cat="dsa", title="Jewels and Stones",
         answer="Given a string of jewel types and a string of stones, count how many stones are jewels. Put the jewel characters in a set for O(1) membership, then count stones found in it.",
         tags=["jewels-stones","hash-set","string","counting","dsa"],
         code='''# Count how many stones are also jewels (each char in jewels is a type).
def num_jewels_in_stones(jewels, stones):
    jewel_set = set(jewels)
    return sum(1 for s in stones if s in jewel_set)''',
         complexity="Time O(len(jewels) + len(stones)), space O(len(jewels)).",
         pitfalls="Using a list membership check (O(n) each) instead of a set; case sensitivity matters.",
         example="num_jewels_in_stones('aA', 'aAAbbbb') -> 3."),
    dict(cat="dsa", title="Defanging an IP Address",
         answer="'Defang' an IPv4 address by replacing every period with '[.]' so it can't be accidentally clicked. A single string replace does it.",
         tags=["defang-ip","string","replace","dsa"],
         code='''# Replace every '.' in an IP with '[.]' to 'defang' it.
def defang_ip_addr(address):
    return address.replace(".", "[.]")''',
         complexity="Time O(n), space O(n).",
         pitfalls="Manual char-by-char building when a single replace suffices.",
         example="defang_ip_addr('1.1.1.1') -> '1[.]1[.]1[.]1'."),
    dict(cat="dsa", title="Replace Elements with Greatest Element on Right Side",
         answer="Replace each element with the GREATEST element to its right; the last element becomes -1. Scan from the RIGHT, keeping a running maximum: set each position to the current max-so-far, then update the max with the old value.",
         tags=["replace-greatest-right","suffix-max","array","dsa"],
         code='''# Replace each element with the greatest element to its RIGHT (-1 for last).
def replace_elements(arr):
    greatest = -1
    for i in range(len(arr) - 1, -1, -1):
        arr[i], greatest = greatest, max(greatest, arr[i])
    return arr''',
         complexity="Time O(n), space O(1).",
         pitfalls="Scanning left-to-right (needs the suffix max); updating the max before assigning.",
         example="replace_elements([17,18,5,4,6,1]) -> [18,6,6,6,1,-1]."),
    dict(cat="dsa", title="Decode XORed Array",
         answer="An array was XOR-encoded as encoded[i] = arr[i] XOR arr[i+1]; given the encoded array and the first original element, recover the array. Since XOR is its own inverse, arr[i+1] = arr[i] XOR encoded[i] — rebuild forward from 'first'.",
         tags=["decode-xored-array","xor","bit-manipulation","array","dsa"],
         code='''# Recover the array from its XOR-encoding, given the first element.
def decode_xored(encoded, first):
    result = [first]
    for e in encoded:
        result.append(result[-1] ^ e)   # arr[i] = arr[i-1] ^ encoded[i-1]
    return result''',
         complexity="Time O(n), space O(n).",
         pitfalls="Forgetting XOR is self-inverse; off-by-one aligning encoded[i] to arr[i], arr[i+1].",
         example="decode_xored([1,2,3], 1) -> [1,0,2,1]."),
    dict(cat="dsa", title="Split a String in Balanced Strings",
         answer="Count the maximum number of BALANCED substrings (equal numbers of 'L' and 'R') you can split the string into. Greedily track a running balance (+1 for R, -1 for L); every time it returns to 0 a balanced segment closes, so increment the count.",
         tags=["balanced-split","greedy","string","dsa"],
         code='''# Max number of balanced substrings (equal count of 'L' and 'R').
def balanced_string_split(s):
    count = 0        # running balance: +1 for R, -1 for L
    result = 0
    for ch in s:
        count += 1 if ch == 'R' else -1
        if count == 0:
            result += 1   # a balanced segment closes here
    return result''',
         complexity="Time O(n), space O(1).",
         pitfalls="Overcomplicating — greedy closing at balance 0 is optimal; miscounting the direction signs.",
         example="balanced_string_split('RLRRLLRLRL') -> 4."),
    dict(cat="glossary", title="TCP vs UDP",
         answer="Two transport protocols. TCP is CONNECTION-oriented and RELIABLE: a 3-way handshake, then guaranteed in-order, error-checked, retransmitted delivery with flow/congestion control — at the cost of overhead and latency (handshakes, ordering, head-of-line blocking). UDP is CONNECTIONLESS and best-effort: fire datagrams with no delivery/order guarantee and no handshake — minimal overhead/latency. Use TCP when correctness matters (web, files); UDP when timeliness beats perfection (video, VoIP, gaming, DNS).",
         tags=["tcp","udp","transport","networking"],
         example="A file download uses TCP (every byte must arrive correctly); a live video call uses UDP (a dropped frame beats stalling the stream to retransmit)."),
    dict(cat="glossary", title="TLS 1.3 handshake",
         answer="Establishes an encrypted, authenticated channel, streamlined in TLS 1.3 to ONE round trip (1-RTT), with 0-RTT resumption for repeat visits. The client sends its key share up front; the server replies with its share + certificate, and both derive a shared session key via EPHEMERAL Diffie-Hellman — giving FORWARD SECRECY. It dropped legacy ciphers and starts encryption earlier — faster and safer than TLS 1.2's 2-RTT.",
         tags=["tls","tls1.3","handshake","forward-secrecy","encryption"],
         example="On TLS 1.3 the browser and server exchange key shares in one round trip, verify the server's certificate, and derive a forward-secret session key — so a future key compromise can't decrypt today's traffic."),
    dict(cat="glossary", title="JWT structure & claims",
         answer="A JSON Web Token has three base64url parts separated by dots: HEADER (algorithm/type), PAYLOAD (the CLAIMS — sub=user id, exp=expiry, iat=issued-at, roles), and SIGNATURE (over header+payload with a secret/private key). The server verifies the signature to trust the claims WITHOUT a DB lookup — stateless auth. Never put secrets in the payload (it's base64-encoded, not encrypted) and always verify exp + signature.",
         tags=["jwt","claims","authentication","stateless","token"],
         example="A JWT 'xxxxx.yyyyy.zzzzz' carrying {sub:'123', exp:1699999999, role:'admin'} is trusted after the API verifies its signature and expiry — no session store needed."),
    dict(cat="glossary", title="Cookie security flags (Secure / HttpOnly / SameSite)",
         answer="Attributes that harden cookies. SECURE: send only over HTTPS. HTTPONLY: forbid JavaScript access (document.cookie) — mitigates XSS token theft. SAMESITE (Strict/Lax/None): control whether the cookie rides cross-site requests — Lax/Strict mitigate CSRF. Together they protect session cookies from interception, script theft, and forgery.",
         tags=["cookie-flags","secure","httponly","samesite","web-security"],
         example="A session cookie set 'Secure; HttpOnly; SameSite=Lax' can't be read by injected JS, can't leak over HTTP, and won't ride a cross-site POST — closing XSS and CSRF vectors."),
    dict(cat="glossary", title="HSTS (HTTP Strict Transport Security)",
         answer="A response header telling browsers to ALWAYS use HTTPS for a domain for a set duration, refusing any plain-HTTP connection even if the user types http:// or clicks an old link. It prevents SSL-stripping man-in-the-middle attacks and the insecure initial redirect. Preloading (a browser-shipped list) closes even the first-visit gap.",
         tags=["hsts","https","ssl-stripping","web-security","networking"],
         example="With 'Strict-Transport-Security: max-age=31536000; includeSubDomains', a browser upgrades every future request to HTTPS automatically, so an attacker can't downgrade the connection to HTTP."),
    dict(cat="conceptual", title="Why is UDP used for video, gaming, VoIP, and DNS despite being unreliable?",
         answer="TCP's reliability costs LATENCY that hurts real-time and tiny-request workloads. TCP guarantees IN-ORDER delivery, so one lost packet triggers a retransmit AND head-of-line blocking — all later data waits a full round trip. For a live call or game that stall is worse than the loss: by the time the retransmitted frame arrives it's stale; you'd rather skip it and show the next. UDP delivers datagrams immediately with no ordering/retransmit, letting the APP decide what to do about loss (interpolate a dropped frame, ignore a stale position). For DNS, a query/response is one tiny exchange; TCP's 3-way handshake would triple the round trips for no benefit, so UDP sends one packet and gets one back (falling back to TCP only for large responses). The principle: use UDP when late data is useless and loss is app-handleable; TCP when every byte and its order matter. (QUIC/HTTP/3 builds selective reliability ON TOP of UDP to get per-stream guarantees without TCP's head-of-line blocking.)",
         tags=["udp","tcp","latency","real-time","why"],
         example="A 100ms-late video frame is worthless, so a call uses UDP and drops it; a bank transfer uses TCP because a missing byte corrupts the data — the cost model, not 'reliable is always better', decides."),
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
