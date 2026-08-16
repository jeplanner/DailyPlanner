"""Java bank — ten-section deep dives, keyed by entry title.

WHY A PATCH DICT RATHER THAN A FIELD ON THE ENTRY. A deep dive is 12,000
characters; an entry is 3,000. Inlining them would make the entry modules
unreadable — you would scroll past three screens of prose to find the next
title — and the ratio only gets worse. Keeping them keyed by TITLE means the
entry modules stay browsable and a deep dive can be added to any entry later
without touching it.

Keyed by title rather than by index for the same reason progress is: inserting
an entry in the middle of a module must not silently re-point every deep dive
at the wrong topic. A title that matches nothing is a self-check failure, not
a silent no-op.

THE TEN SECTIONS are fixed and ordered as pedagogy, not preference:
    1  the goal, in plain English
    2  the intuition — why the rule exists at all
    3  the mechanism, in detail
    4  edge cases and failure modes
    5  the alternatives, and what each costs
    6  numbered how-to steps
    7  the answer in plain language — spoken register, for saying out loud
    8  the code, line by line
    9  a full trace
   10  complexity, numbered mistakes, one-sentence takeaway
"""

DEEP = {}


DEEP["equals and hashCode — the contract, and what breaks when you ignore it"] = [
"""1. THE GOAL IN PLAIN ENGLISH — teaching Java when two different objects count as the same thing

By default, Java thinks two objects are "equal" only if they are literally the SAME OBJECT — the same
thing in memory. That is almost never what you want for a value. Two `Point` objects both holding
(1, 2) are different objects and are obviously the same point, and you have to say so.

Saying so takes TWO methods, not one, and that is the entire source of the trouble.

    equals(Object)  — "do these two hold the same values?"
    hashCode()      — "give me a number summarising this object's values"

WHY TWO? Because a HashSet does not compare you against every element it holds — that would be O(n)
and would defeat the point of a hash set. It uses hashCode() to jump STRAIGHT to one small bucket, and
only compares with equals() against the handful of things already in that bucket.

    SO IF TWO EQUAL OBJECTS RETURN DIFFERENT HASH CODES, THEY GO TO DIFFERENT BUCKETS AND ARE NEVER
    COMPARED. The set contains one of them and cannot find the other. Nothing errors. `contains`
    simply returns false for an object the set demonstrably equals.

THE EVERYDAY VERSION: a library filing books by the first letter of the author's surname. equals is
"is this the same book?" and hashCode is "which shelf?". Get the shelf wrong and the book is still in
the library, and nobody will ever find it — because the search only ever looks on one shelf.

TERMS AS THEY APPEAR:
- CONTRACT: the rules the two methods must jointly satisfy, documented on java.lang.Object.
- BUCKET / BIN: one slot of a hash table's internal array.
- COLLISION: two unequal objects landing in the same bucket. Normal, expected, and handled.""",

"""2. THE INTUITION — the contract has one direction, and only one

The rule is stated as an implication, and the direction matters enormously:

    IF a.equals(b) THEN a.hashCode() == b.hashCode()          ← REQUIRED
    IF a.hashCode() == b.hashCode() THEN a.equals(b)          ← NOT required, and impossible anyway

THE SECOND DIRECTION CANNOT BE REQUIRED. A hashCode returns an int — about 4.3 billion possible values
— and there are infinitely many possible Strings. By the pigeonhole principle, distinct objects MUST
share hash codes eventually. A collision is not a bug; a hash table is built to handle them.

SO THE ONE-WAY CONTRACT IS EXACTLY AS STRONG AS IT CAN BE. Equal things must agree on their hash;
unequal things are free to agree or not.

WHICH IMMEDIATELY TELLS YOU THE TWO WAYS TO BREAK IT:

    OVERRIDE equals AND NOT hashCode — the common one. Two objects are now equal with different hash
    codes, which violates the contract directly. HashSet accumulates duplicates; HashMap loses keys.

    OVERRIDE hashCode AND NOT equals — rarer, and it does NOT violate the contract. Equal objects
    (identical references) still share a hash. But it is useless: the objects collide into one bucket,
    Object.equals compares references, and they are all kept as distinct entries. You have made the
    hash table slower without making it more correct.

    THAT ASYMMETRY IS WORTH INTERNALISING. Forgetting hashCode is a CORRECTNESS bug. Forgetting equals
    is a PERFORMANCE bug that behaves exactly as if you had overridden neither.

AND A LEGAL-BUT-TERRIBLE IMPLEMENTATION EXISTS: `return 1;`. Every object shares a hash code, the
contract holds perfectly, and every entry lands in one bucket. Since Java 8 that bucket becomes a
red-black tree at eight entries, so lookup degrades to O(log n) rather than the O(n) it would have
been before. STILL WRONG, and now wrong more slowly.""",

"""3. THE MECHANISM — what HashSet.contains actually does, step by step

    set.contains(new Point(1, 2))

    STEP 1. Call hashCode() on the argument.                     → say 994
    STEP 2. SPREAD it: h ^ (h >>> 16), mixing high bits down.
    STEP 3. Mask to an index: spread & (tableLength - 1).        → say bucket 2
    STEP 4. Walk bucket 2 — a linked list, or a tree if it grew past 8.
    STEP 5. For each entry: first `==` (a cheap identity check), then equals().
    STEP 6. Return true on the first match; false if the bucket runs out.

    NOTICE WHAT NEVER HAPPENS: NO OTHER BUCKET IS EVER EXAMINED. That is the whole performance
    argument for a hash table, and it is exactly why a wrong hashCode is fatal rather than merely
    inefficient. The object may be sitting in bucket 7; contains() will never look there.

THE FIVE FORMAL REQUIREMENTS ON equals, from the Object javadoc:

    REFLEXIVE     x.equals(x) is true.
    SYMMETRIC     x.equals(y) implies y.equals(x).
    TRANSITIVE    x.equals(y) and y.equals(z) implies x.equals(z).
    CONSISTENT    repeated calls give the same answer, if nothing changed.
    NULL          x.equals(null) is false — never throws.

SYMMETRY IS THE ONE PEOPLE BREAK, and they break it with subclasses. If `Point.equals` uses
`instanceof Point` and `ColourPoint extends Point` adds a colour to its comparison, then
`point.equals(colourPoint)` is TRUE (the point sees a Point with matching coordinates) while
`colourPoint.equals(point)` is FALSE (the colour point sees no colour). Asymmetric, and a collection
containing both behaves differently depending on iteration order.

    THE TWO WAYS OUT, AND NEITHER IS FREE:
    `getClass() != o.getClass()` — symmetric, and it means a subclass instance is never equal to a
    superclass instance, which breaks Liskov substitutability.
    `instanceof` plus a `canEqual` method — symmetric and correct, and it is machinery.
    THE PRACTICAL ANSWER: make value classes FINAL, or use a `record`, and the question does not
    arise.

CONSISTENCY IS THE OTHER SILENT ONE. Nothing stops you computing a hash from a mutable field. Mutate
it after inserting into a set and the object is now in the WRONG BUCKET — set.contains(thatVeryObject)
returns false, and it will still be there in the iteration, and in size().""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — equals WITHOUT hashCode. The default hashCode is identity-based, so two equal objects almost
certainly differ. HashSet holds duplicates; HashMap.get returns null for a key it contains; and every
direct `a.equals(b)` test you write passes, which is why this survives review. THE BUG IS INVISIBLE
UNTIL THE OBJECT MEETS A HASH-BASED COLLECTION.

CASE 2 — hashCode WITHOUT equals. Contract intact, behaviour unchanged from overriding neither, and
now everything collides. A pure performance loss.

CASE 3 — A MUTABLE FIELD IN THE HASH. Insert, mutate, and the object is unreachable in a collection
that still contains it. THE FIX IS NOT A BETTER hashCode — it is immutable fields.

CASE 4 — ASYMMETRY VIA A SUBCLASS. See section 3. Prefer final classes or records.

CASE 5 — `equals(MyType other)` INSTEAD OF `equals(Object)`. This is an OVERLOAD, not an override, so
collections keep calling Object.equals and your method is never invoked. `@Override` turns this into a
compile error instantly, which is the entire argument for always writing it.

CASE 6 — FLOATING-POINT FIELDS. `==` on a double says NaN != NaN, so an object holding NaN would not
equal itself and REFLEXIVITY breaks. Use Double.compare or Objects.equals on the boxed values —
Double.equals is defined to treat NaN as equal to itself precisely so this works.

CASE 7 — ARRAY FIELDS. `Objects.hash(arr)` hashes the array REFERENCE, not its contents, so two
objects with identical arrays get different hashes. Use Arrays.hashCode, or Arrays.deepHashCode for
nested arrays.

CASE 8 — INHERITING equals FROM A PARENT WITH EXTRA FIELDS. A subclass adding state must include it,
and then section 3's symmetry problem arrives.

CASE 9 — `return 1;` as a hashCode. Legal, contract-compliant, and it turns your HashMap into a
treeified list.

CASE 10 — RELYING ON hashCode ACROSS JVM RUNS. String.hashCode is specified and stable; almost
nothing else is. Object.hashCode varies per run. NEVER PERSIST A hashCode or use it as a database key.""",

"""5. THE ALTERNATIVES — and what each costs

WRITE IT BY HAND.
    Full control, and it is the version an interview asks for. The canonical shape is in section 8.
    COST: it is boilerplate, and every field added later must be added to both methods — which is
    exactly the maintenance failure that produces a class whose equals is quietly out of date.

LET THE IDE GENERATE IT.
    Correct, instantly, and regenerable when fields change. THE DEFAULT ANSWER FOR A REAL CODEBASE.
    COST: it does not regenerate itself, so the same drift is possible, just less likely.

`Objects.hash(a, b, c)` (Java 7+).
    One line and correct. COST: it ALLOCATES A VARARGS ARRAY on every call and boxes every primitive.
    For an object used as a hot-loop map key that is measurable, and the hand-written
    `31 * result + field` form avoids it. Measure before caring.

A `record` (Java 16+).
    Generates a correct equals, hashCode and toString from the components, and cannot drift because
    there is nothing to keep in sync. IT IS THE RIGHT ANSWER FOR A VALUE CLASS IN MODERN JAVA, and it
    also sidesteps the subclass-symmetry problem entirely by being implicitly final.
    COST: no inheritance, no mutability, and the representation is public by design.

LOMBOK'S @EqualsAndHashCode.
    Generates both at compile time. COST: an annotation processor in the build, and its default of
    including every field is frequently wrong — a cache or a back-reference should not be in equals.

APACHE COMMONS EqualsBuilder / HashCodeBuilder.
    Readable and reflective variants exist that are convenient and slow. Largely superseded by
    Objects.hash and records.

WHAT TO ACTUALLY SAY IN AN INTERVIEW: "For a value class I'd use a record. If it has to be a class,
I'd let the IDE generate them from the identity fields, keep those fields final, and write @Override
on both so an accidental overload is a compile error."
""",

"""6. HOW TO WRITE IT — numbered steps

STEP 1 — ASK WHICH FIELDS DEFINE IDENTITY. Not all of them: a cached value, a lazily-computed field,
a back-reference to a parent, a timestamp of last access — none of those make two objects different
things.

STEP 2 — MAKE THOSE FIELDS FINAL. It is the only real protection against the mutable-key failure, and
it is cheaper than any amount of documentation.

STEP 3 — WRITE @Override ON BOTH. It converts `equals(MyType)` — an overload that will never be
called — from a silent bug into a compile error.

STEP 4 — START equals WITH THE IDENTITY FAST PATH. `if (this == o) return true;` It is one comparison
and it short-circuits the common case of comparing an object with itself.

STEP 5 — USE `instanceof`, WHICH HANDLES null FOR FREE. `if (!(o instanceof Point p)) return false;`
— and since Java 16 that pattern also binds the cast variable, removing the separate cast line.

STEP 6 — COMPARE FIELD BY FIELD, CHEAPEST FIRST. Primitives with `==`, doubles with Double.compare,
objects with Objects.equals (null-safe), arrays with Arrays.equals.

STEP 7 — USE THE SAME FIELDS IN hashCode, IN THE SAME ORDER. `Objects.hash(x, y)` unless it is a hot
path.

STEP 8 — DO NOT INCLUDE A MUTABLE FIELD. If you must, document loudly that the object cannot be used
as a key after mutation — and then reconsider making it immutable.

STEP 9 — TEST THE FIVE PROPERTIES. Reflexive, symmetric, transitive, consistent, null-safe. And test
the one that actually matters: put two equal objects in a HashSet and assert the size is 1.

STEP 10 — OR SKIP ALL OF IT AND WRITE A RECORD.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'By default Java treats two objects as equal only if they're the same object in memory, which is
almost never what you want for a value. So you override equals to say what "the same" means — and you
have to override hashCode at the same time, because of how hash-based collections work.

A HashSet doesn't compare your object against everything it holds; that would be linear and would
defeat the point. It calls hashCode to jump straight to one bucket, and only calls equals against the
handful of things already in that bucket. So if two equal objects return different hash codes they
land in different buckets and are NEVER COMPARED. The set contains one and can't find the other.
Nothing throws — contains just returns false for an object the set demonstrably equals.

The contract runs in exactly one direction: equal objects MUST have equal hash codes, and the reverse
is not required and couldn't be. A hashCode is an int — about four billion values — and there are
infinitely many Strings, so by pigeonhole distinct objects must share hashes eventually. A collision
isn't a bug; the table is built to handle them.

That one-way rule also tells you which mistake is which. Overriding equals and forgetting hashCode is
a CORRECTNESS bug — the collection loses things. Overriding hashCode and forgetting equals doesn't
violate the contract at all; it just makes everything collide into one bucket while Object.equals
still compares references, so you've made the table slower without making it more correct.

For the implementation: I'd start with the identity fast path, `this == o`. Then `instanceof`, which
handles null for free — and since Java 16 the pattern form binds the cast variable too, so you don't
need a separate cast line. Then compare the identity fields, cheapest first. And use exactly those
same fields in hashCode.

Two things I'd flag. Use IMMUTABLE fields — if a field in the hash changes after the object is in a
set, the object is now in the wrong bucket and contains(thatVeryObject) returns false while it's still
sitting in the iteration and still counted in size(). And always write @Override, because
`equals(MyType other)` is an OVERLOAD rather than an override, so collections keep calling
Object.equals and your method is never invoked. @Override turns that from a silent bug into a compile
error.

Symmetry is the subtle one. If a subclass adds a field to the comparison, the parent thinks they're
equal and the child doesn't, so equals is asymmetric and a collection holding both behaves differently
depending on iteration order. The practical fix is to make value classes final — or just use a record,
which generates all of this correctly, can't drift when you add a field, and is implicitly final so
the symmetry question never arises.'""",

"""8. THE CODE, LINE BY LINE

    public final class Point {
    //     ^^^^^ FINAL. It removes the subclass-symmetry problem entirely rather
    //     than solving it, and for a value class there is no cost.

        private final int x, y;
        //      ^^^^^ FINAL FIELDS. The only real protection against the
        //      mutable-key failure — an object whose hash changes after
        //      insertion is unreachable in a collection that still holds it.

        @Override
        //  ^^^^^^^^^ NOT DECORATION. Without it, `equals(Point o)` compiles
        //  happily as an OVERLOAD, collections keep calling Object.equals, and
        //  your method is never invoked. With it, that is a compile error.
        public boolean equals(Object o) {
        //             ^^^^^^^ the parameter MUST be Object to override.

            if (this == o) return true;
            // ^ identity fast path. One comparison, and it short-circuits the
            //   extremely common case of an object compared with itself —
            //   which happens on every set.contains(x) that finds x.

            if (!(o instanceof Point p)) return false;
            //    ^^^^^^^^^^^^^^^^^^^^^ instanceof is FALSE for null, so this
            //    single line covers the null check too — no separate `o == null`.
            //    ^ the `p` binding is Java 16+ pattern matching: it replaces the
            //    `Point p = (Point) o;` line the old form needed.

            return x == p.x && y == p.y;
            //     ^ primitives compare with ==. For OBJECT fields use
            //       Objects.equals(a, b) — null-safe both ways. For DOUBLES use
            //       Double.compare, because == says NaN != NaN and an object
            //       holding NaN would then not equal ITSELF, breaking reflexivity.
            //       For ARRAYS use Arrays.equals — == compares references.
        }

        @Override
        public int hashCode() {
            return Objects.hash(x, y);
            //     ^ THE SAME FIELDS as equals, always. Adding a field to one and
            //       not the other is the drift that breaks the contract months
            //       after the class was written.
            //     ^ COST: allocates a varargs array and boxes both ints. Fine
            //       almost everywhere; for a hot-loop map key write the manual
            //       form below instead.
        }
    }

THE MANUAL hashCode, for when allocation matters:

    int result = Integer.hashCode(x);
    result = 31 * result + Integer.hashCode(y);
    return result;
    // ^ 31 is odd and prime, and 31*i compiles to (i << 5) - i, which mattered
    //   more in 1995 than now. ANY odd multiplier works; the primality is
    //   folklore rather than requirement. The MULTIPLY-AND-ADD is the part that
    //   matters — it makes the result depend on field ORDER, so (1,2) and (2,1)
    //   get different hashes where a plain sum would not.

OR, IN MODERN JAVA, THE WHOLE THING:

    public record Point(int x, int y) {}
    // equals, hashCode and toString generated from the components, implicitly
    // final, and it CANNOT drift when a component is added.""",

"""9. THE TRACE — watch the object become unfindable

TWO CLASSES, IDENTICAL EXCEPT FOR ONE OVERRIDE.

    class Good { int x; equals→compares x; hashCode→Objects.hash(x); }
    class Bad  { int x; equals→compares x; NO hashCode override; }

    Set<?> set = new HashSet<>();  table length 16.

GOOD:

    step                                  value           result
    ---------------------------------------------------------------------------
    set.add(new Good(5))
      hashCode() of Good(5)                 1029          → bucket 5
      bucket 5 is empty                                   → INSERTED
    set.contains(new Good(5))
      hashCode() of the NEW Good(5)         1029          → bucket 5   (same!)
      walk bucket 5, call equals            true          → TRUE
    set.size()                                            → 1

BAD:

    step                                  value           result
    ---------------------------------------------------------------------------
    set.add(new Bad(5))
      Object.hashCode() — identity      1698156408        → bucket 8
      bucket 8 is empty                                   → INSERTED
    set.contains(new Bad(5))
      Object.hashCode() of the NEW one   712345678        → bucket 14  (DIFFERENT)
      walk bucket 14 — EMPTY                              → FALSE
      equals() IS NEVER CALLED AT ALL
    set.add(new Bad(5))  again                            → INSERTED, bucket 3
    set.size()                                            → 2

    THE LINE THAT MATTERS IS "equals() IS NEVER CALLED AT ALL". The two objects are equal by every
    definition the class gives, `a.equals(b)` returns true if you test it directly, and the set never
    asks — because it looked in one bucket and they were not in the same one.

    AND NOTE THE SIZE. The set now contains two objects that are equal to each other. Every invariant
    a Set is supposed to provide is broken, silently, with no exception anywhere.

THE MUTATION FAILURE, traced:

    Good g = new Good(5);
    set.add(g);                    hashCode 1029 → bucket 5, inserted
    g.x = 6;                       (only possible if x is not final)
    set.contains(g)                hashCode is now 1060 → bucket 4
                                   bucket 4 is empty → FALSE
    set.size()                     → 1
    for (Good o : set) ...         → yields g

    THE SET CONTAINS AN OBJECT IT CANNOT FIND. contains(g) is false, size() is 1, and iterating
    produces g. That is why the fields must be final, and it is why the fix is immutability rather
    than a cleverer hash function.

WHICH LINE CAUSED WHICH ROW:

    `Objects.hash(x)` in Good     produced the SAME hash for two distinct objects, which is the entire
                                 requirement. Delete it and every row of the BAD table follows.
    Object's identity hashCode   produced 1698156408 and 712345678 — arbitrary, different every run,
                                 and different for every instance. That is correct behaviour for
                                 Object and catastrophic as a value's hash.
    `g.x = 6`                    produced the unfindable-object trace. Making x final makes that line
                                 a compile error, which is the whole point.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    HashSet.contains / HashMap.get: O(1) average, O(log n) worst case since Java 8 (treeified bins),
    O(n) before that.
    A CORRECT hashCode is what makes the average case average. A constant hashCode is contract-
    compliant and turns every operation into the worst case.
    Objects.hash allocates a varargs array and boxes primitives — irrelevant almost everywhere,
    measurable for a hot-loop map key.

    THE CONTRACT, in one line: a.equals(b) IMPLIES a.hashCode() == b.hashCode(). One direction only,
    and the reverse is impossible to require.

THE #1 MISTAKE: overriding equals and not hashCode. Every direct test passes; the collection loses
things. It is a correctness bug that is invisible until the object meets a HashMap.

THE #2 MISTAKE: a mutable field in the hash. Insert, mutate, and the object is unreachable in a
collection that still contains it and still counts it in size().

THE #3 MISTAKE: `public boolean equals(MyType o)`. An overload, never called by any collection.
@Override catches it at compile time, which is the entire reason to write @Override.

THE #4 MISTAKE: asymmetric equals via a subclass. Make value classes final, or use a record.

THE #5 MISTAKE: `==` on double fields. NaN != NaN breaks reflexivity — an object would not equal
itself. Use Double.compare.

THE #6 MISTAKE: `Objects.hash(someArray)`. That hashes the array REFERENCE. Use Arrays.hashCode.

THE #7 MISTAKE: different fields in equals and hashCode. Usually drift — a field added to one and not
the other, six months later.

THE #8 MISTAKE: persisting a hashCode, or using it as a database key. Only String's is specified and
stable; Object's varies per JVM run.

THE #9 MISTAKE: `return 1;`. Contract-compliant, and it turns your hash table into one treeified
bucket.

THE #10 MISTAKE: writing all of this by hand in 2026 for a plain value class. A record generates it
correctly, cannot drift, and is implicitly final.

ONE-SENTENCE TAKEAWAY: hashCode picks the BUCKET and equals decides membership INSIDE it, so two equal
objects with different hash codes land in different buckets and are never compared — the set contains
one and returns false for the other with no exception anywhere — which is why the contract runs one
way (equal implies same hash, never the reverse), why the fields must be immutable, why @Override is
not decoration, and why a `record` is the right answer whenever the class is just a value.""",
]


DEEP["How HashMap actually works — buckets, collisions, and treeification"] = [
"""1. THE GOAL IN PLAIN ENGLISH — finding something without looking through everything

A HashMap answers "what value is stored under this key?" in roughly constant time, no matter how many
entries it holds. A million entries and a hundred entries cost the same to look up. That is a strange
promise and it is worth understanding how it is kept.

THE IDEA: keep an ARRAY of slots. To find where a key belongs, turn the key into a number — that is
hashCode() — and use that number to pick a slot. Now a lookup is arithmetic plus one array access,
which does not care how big the array is.

    THE PROBLEM THAT IMMEDIATELY FOLLOWS: two different keys can produce the same slot. That is a
    COLLISION and it is not rare — it is guaranteed, because there are more possible keys than slots.

    THE ANSWER: each slot holds a small LIST rather than a single entry. A lookup jumps to the slot
    and then walks that short list comparing with equals(). As long as the lists stay short, the walk
    is a handful of comparisons and the whole thing is still effectively constant.

    THE PROBLEM AFTER THAT: what if the lists do not stay short? Since Java 8, a slot that grows past
    eight entries is converted into a BALANCED TREE, so even a pathological case degrades to O(log n)
    rather than O(n).

    AND THE LAST PIECE: as entries accumulate the lists lengthen everywhere. So when the table is 75%
    full, HashMap DOUBLES the array and redistributes everything, keeping the lists short again.

TERMS AS THEY APPEAR:
- BUCKET / BIN: one slot of the array.
- LOAD FACTOR: how full the table is allowed to get before it doubles. Default 0.75.
- TREEIFY: converting an over-long bucket into a red-black tree.""",

"""2. THE INTUITION — three design choices, each forced by the one before it

CHOICE 1: THE TABLE LENGTH IS ALWAYS A POWER OF TWO.

    The obvious way to turn a hash into an index is `hash % length`. A modulo is a division, and
    division is one of the slowest integer instructions on any CPU. But if the length is a power of
    two, `hash % length` is exactly `hash & (length - 1)` — a single AND against a mask of low bits.

    SO THE POWER-OF-TWO CHOICE BUYS A DIVISION-FREE INDEX, on the hottest path in the class.

CHOICE 2: THE HASH IS SPREAD BEFORE MASKING — h ^ (h >>> 16).

    This is FORCED BY CHOICE 1 and it is the part people miss. A mask keeps only the LOW bits and
    throws the high ones away entirely. So two keys differing only in their high bits collide on
    every single lookup, forever.

    Consider a key type whose hashCode is `id * 65536` — perfectly reasonable-looking. Every such
    hash has sixteen zero low bits, so with a table of 16 they ALL map to bucket 0.

    THE FIX IS ONE LINE: XOR the top 16 bits down into the bottom 16. Now a difference anywhere in
    the int influences the low bits, and the mask sees it. It is deliberately cheap — one shift and
    one XOR — because it runs on every operation, and it is a mitigation rather than a real hash
    function: it makes a mediocre hashCode survivable, not good.

CHOICE 3: OVER-LONG BUCKETS BECOME TREES.

    Before Java 8, a bucket was always a linked list. That made worst-case lookup O(n) — and it was
    ATTACKABLE. A web framework parsing user-supplied form parameters into a HashMap could be sent
    thousands of keys engineered to share one bucket, turning an O(n) parse into O(n²) and taking the
    server down with a single small request. That was a real, published denial-of-service class
    affecting most languages of the era, not a theoretical one.

    TREEIFICATION BOUNDS THE DAMAGE. At 8 entries in one bucket — and only if the table is at least
    64 long, because otherwise resizing is the better response — the bucket becomes a red-black tree
    and lookup within it is O(log n). The attack goes from quadratic to n log n, which is survivable.

    NOTE THE TWO THRESHOLDS. Eight is chosen because with a decent hash the probability of eight
    entries in one bucket is vanishingly small (Poisson, roughly 6 in 100 million), so a bucket that
    long means the hash is bad or hostile. Sixty-four exists so that a small, dense table resizes
    instead of building trees it will immediately have to take apart.""",

"""3. THE MECHANISM — put and get, in detail

    map.put(key, value)

    1. h = key.hashCode()
    2. h = h ^ (h >>> 16)                     the spread
    3. i = h & (table.length - 1)             the index
    4. if table[i] is empty → place a new Node there. Done.
    5. else walk the bucket:
         for each node, if node.hash == h AND (node.key == key || node.key.equals(key))
             → REPLACE its value, return the old one
       (the `node.hash == h` check first is an optimisation: comparing two ints is far cheaper than
        calling equals, and if the hashes differ the keys cannot be equal)
    6. not found → append a new node. If the bucket now has ≥ 8 entries AND the table is ≥ 64 long,
       TREEIFY the bucket.
    7. if ++size > threshold (capacity × 0.75) → RESIZE.

    map.get(key) is steps 1-3 and 5, with no mutation.

THE RESIZE, AND THE PROPERTY THAT MAKES IT CHEAP:

    The table doubles, from n to 2n. Because n is a power of two, the mask gains exactly ONE BIT. So
    for any entry, its new index is determined by that single new bit:

        the bit is 0 → the entry stays at index i
        the bit is 1 → the entry moves to index i + oldCapacity

    NO ENTRY GOES ANYWHERE ELSE. So a resize splits each bucket into exactly two, in one pass, with no
    rehashing and no comparisons — Java 8 exploits this to split a bucket into a "low" list and a
    "high" list and attach them at i and i + n. That is a direct consequence of choice 1 in section 2.

    THE COST IS O(n) and it is amortized away by the doubling — the same geometric-series argument as
    ArrayList's growth. TOTAL work across n insertions is O(n); a SINGLE insertion can be O(n).

WHY ITERATION ORDER IS WHAT IT IS:

    Iteration walks the table from index 0, and each bucket in list order. So the order is a
    deterministic function of the hash values and the table length. It is NOT random — it is stable
    for a fixed set of keys — AND IT CHANGES THE MOMENT THE TABLE RESIZES.

    That is the worst possible combination for a bug: code accidentally depending on order passes
    every test with ten keys and breaks in production at thirteen.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — A MUTABLE KEY. Insert, then change a field that hashCode reads. The entry is now in the
wrong bucket: map.get(thatVeryKey) returns null, the entry is still in entrySet(), and size() still
counts it. USE IMMUTABLE KEYS. This is the single most common HashMap bug.

CASE 2 — A KEY WITH equals BUT NO hashCode. Covered fully in the equals/hashCode entry: different
buckets, never compared, entries lost.

CASE 3 — null. HashMap ALLOWS one null key (special-cased to bucket 0) and any number of null values.
ConcurrentHashMap allows NEITHER, because `get(k) == null` would be ambiguous between "absent" and
"mapped to null" with no atomic way to disambiguate.

CASE 4 — CONCURRENT MODIFICATION. HashMap is not thread-safe. Before Java 8, a concurrent put during
a resize could produce a CIRCULAR LINKED LIST in a bucket, and a subsequent get would spin forever at
100% CPU — a genuinely famous production failure. Java 8's resize does not reverse the list order, so
that specific infinite loop is gone; the map is still corruptible and still must not be shared.

CASE 5 — RELYING ON ITERATION ORDER. Deterministic, and it changes on resize. Use LinkedHashMap for
insertion order or TreeMap for sorted order.

CASE 6 — A TERRIBLE hashCode. `return 1;` is contract-compliant and puts everything in one bucket,
which since Java 8 is one tree — O(log n) instead of O(1), plus the memory of tree nodes.

CASE 7 — TREEIFICATION NEEDS COMPARABLE KEYS TO BE EFFICIENT. If the keys do not implement Comparable,
the tree falls back to comparing identity hashes to establish an order, which works and is a weaker
guarantee.

CASE 8 — NOT PRE-SIZING A KNOWN-LARGE MAP. Building a map of a million entries from the default
capacity of 16 performs about 17 resizes and copies. `new HashMap<>(expectedSize / 0.75f + 1)` skips
them. The division by the load factor is the part people forget — passing the expected size directly
still resizes once.

CASE 9 — computeIfAbsent MODIFYING THE SAME MAP inside its mapping function. Undefined behaviour on
HashMap and explicitly forbidden on ConcurrentHashMap.

CASE 10 — MEMORY. Every entry is a Node object — roughly 32-40 bytes — plus the table slot. A
Map<Integer,Integer> of a million entries costs tens of megabytes where two int arrays would cost
eight.""",

"""5. THE ALTERNATIVES — and when each is right

HashMap. O(1) average, no ordering, one null key, not thread-safe. THE DEFAULT.

LinkedHashMap. A HashMap plus a doubly-linked list threading every entry in INSERTION order (or, with
one constructor flag, ACCESS order). Iteration is predictable, and the access-order mode plus an
overridden removeEldestEntry gives you an LRU CACHE IN ABOUT FIVE LINES — which is the reason to know
it exists. Costs two extra references per entry.

TreeMap. A red-black tree, O(log n), SORTED by natural order or a comparator, and it offers the
navigation methods a hash map cannot — firstKey, floorKey, ceilingKey, headMap, subMap. Use it when
you need order or range queries. AND REMEMBER IT DEFINES EQUALITY BY compareTo() == 0, NOT equals —
which silently drops entries whose comparator says they tie.

ConcurrentHashMap. Per-bin locking, weakly-consistent iterators that never throw, atomic compound
operations (putIfAbsent, merge, compute), and no nulls. THE ANSWER FOR SHARED MUTABLE MAPS.

EnumMap. Backed by a plain array indexed by the enum's ordinal. Faster and far smaller than a HashMap,
with no hashing at all. ALWAYS PREFER IT FOR ENUM KEYS.

IdentityHashMap. Uses == instead of equals. A specialist tool for object-graph traversal and
serialization, and a trap if reached for by accident.

Map.of / Map.copyOf (Java 9+). Small, immutable, and null-hostile. Ideal for constants. Note the
iteration order of Map.of is deliberately RANDOMISED PER JVM RUN to stop anyone depending on it —
which is the standard library making section 3's point for you.

WHAT TO SAY: "HashMap unless I need ordering, sorting, thread-safety, or enum keys — and for enum keys
it's always EnumMap."
""",

"""6. HOW TO USE IT WELL — numbered steps

STEP 1 — MAKE KEYS IMMUTABLE. Final fields, or a record. It eliminates the most common HashMap bug
outright rather than documenting around it.

STEP 2 — OVERRIDE equals AND hashCode TOGETHER, from the same fields.

STEP 3 — PRE-SIZE WHEN YOU KNOW THE SIZE. `new HashMap<>((int)(n / 0.75f) + 1)`. Dividing by the load
factor is the part people omit, and without it you still resize once at the end.

STEP 4 — USE EnumMap FOR ENUM KEYS. It is an array lookup with no hashing.

STEP 5 — USE getOrDefault, computeIfAbsent AND merge instead of hand-rolled check-then-act. They are
shorter, and on ConcurrentHashMap they are also atomic where the hand-rolled version is not.

STEP 6 — NEVER DEPEND ON ITERATION ORDER. If you need it, say so with the type: LinkedHashMap or
TreeMap.

STEP 7 — DO NOT SHARE A HashMap ACROSS THREADS. ConcurrentHashMap, or confine it to one thread.

STEP 8 — WATCH MEMORY FOR PRIMITIVE-KEYED MAPS. A Map<Integer,Integer> of a million entries is tens of
megabytes; consider a primitive-specialised map or parallel arrays if it matters.

STEP 9 — IF LOOKUPS ARE SLOW, LOOK AT hashCode BEFORE ANYTHING ELSE. A bad hash is the only way a
HashMap becomes slow, and it usually means the key's identity fields were chosen badly.

STEP 10 — FOR AN LRU CACHE, USE LinkedHashMap IN ACCESS ORDER with removeEldestEntry. It is five lines
and it is correct.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A HashMap keeps an array of buckets. To find where a key goes it calls hashCode, squeezes that into a
bucket index, and looks in that one bucket. Two keys can land in the same bucket — a collision — so
each bucket holds a short list, and lookup walks it comparing with equals. As long as the lists stay
short, a lookup is arithmetic plus a couple of comparisons regardless of how many entries the map
holds.

There are three design choices worth knowing and each one forces the next.

The table length is always a POWER OF TWO, so the index is `hash & (length - 1)` — a bitmask instead
of a modulo, and a division is one of the slowest integer instructions there is.

But a mask keeps only the LOW bits and throws the high ones away, so two keys differing only in their
high bits would collide on every lookup forever. Which is why HashMap SPREADS the hash first — `h xor
(h >>> 16)`, XORing the top sixteen bits down into the bottom. One shift and one XOR, deliberately
cheap because it runs on every operation. It doesn't make a bad hashCode good; it makes it survivable.

Third, since Java 8 a bucket that grows past eight entries becomes a RED-BLACK TREE, so worst-case
lookup is O(log n) instead of O(n). That wasn't a performance nicety — before Java 8 you could send a
web framework thousands of form parameters engineered to share one bucket and turn an O(n) parse into
O(n squared). It was a real denial-of-service class across most languages of that era.

The resize is the nicest consequence of the power-of-two choice. The table doubles, so the mask gains
exactly ONE BIT, which means every entry either stays at index i or moves to i plus the old capacity —
nowhere else. So a resize splits each bucket into two in a single pass with no rehashing at all.

Two things I'd flag as the real-world bugs. Keys must be IMMUTABLE: if you mutate a field that hashCode
reads after inserting, the entry is in the wrong bucket and map.get of that very key returns null while
the entry is still in entrySet and still counted in size. And iteration order is NOT random — it's a
deterministic function of the hashes and the table length, which means it's stable for a given set of
keys and CHANGES the moment the map resizes. That's the worst combination: code that accidentally
depends on it passes every test with ten keys and breaks in production at thirteen.'""",

"""8. THE CODE, LINE BY LINE — the parts of HashMap that matter

    // The spread. This is HashMap.hash(), essentially verbatim.
    static int hash(Object key) {
        int h;
        return (key == null) ? 0 : (h = key.hashCode()) ^ (h >>> 16);
        //     ^^^^^^^^^^^^^^^^^ A NULL KEY HASHES TO 0, so it always lands in
        //     bucket 0. That is the whole of HashMap's null-key support.
        //                          ^^^^^^^^^^^^^^^^^^^^^^^ XOR the top 16 bits
        //     down into the bottom 16. FORCED BY THE MASK: without it, two keys
        //     differing only above bit 16 collide on every lookup, forever.
        //     >>> is the UNSIGNED shift — with >> the sign bit would smear.
    }

    // The index. One AND. No division anywhere.
    int i = hash & (table.length - 1);
    //              ^^^^^^^^^^^^^^^^^ length is a power of two, so length-1 is a
    //              mask of low bits and this is exactly hash % length — at a
    //              fraction of the cost.

    // The bucket walk, with the cheap check first.
    for (Node<K,V> e = table[i]; e != null; e = e.next) {
        if (e.hash == hash && (e.key == key || key.equals(e.key))) return e.value;
        //  ^^^^^^^^^^^^^^ COMPARE THE STORED HASH FIRST. Two ints, one
        //  comparison — and if they differ the keys cannot be equal, so equals()
        //  is skipped entirely. On a bucket full of collisions this is most of
        //  the saving.
        //                   ^^^^^^^^^^^^^^ then identity, which is free and true
        //                   surprisingly often (interned strings, cached boxes).
        //                                    ^^^^^^^^^^^^^^^^^ only then equals.
    }

    // Treeify — the thresholds, and why there are two.
    if (binCount >= TREEIFY_THRESHOLD - 1) {            // 8
        if (table.length < MIN_TREEIFY_CAPACITY)        // 64
            resize();          // a SMALL dense table should GROW, not build trees
        else
            treeifyBin(table, hash);
    }
    // ^ 8 because with a decent hash the chance of eight in one bucket is about
    //   6 in 100 million (Poisson, load factor 0.75) — so a bucket that long
    //   means the hash is bad or hostile, not unlucky.
    // ^ 64 so a 16-slot table that is merely crowded resizes instead of building
    //   trees it would immediately have to dismantle.

    // The resize split — the payoff from the power-of-two choice.
    // Old capacity n, new capacity 2n. The mask gains exactly one bit, so:
    if ((e.hash & oldCap) == 0)  → goes in the LOW list, stays at index i
    else                         → goes in the HIGH list, moves to i + oldCap
    // ^ NO REHASHING AND NO COMPARISONS. One pass, each bucket splits in two,
    //   and no entry can go anywhere else. That is a direct consequence of the
    //   table length being a power of two.""",

"""9. THE TRACE — one put, one collision, one resize

TABLE LENGTH 16, so the mask is 0b1111. Three keys.

    key      hashCode()    h ^ (h>>>16)     & 15     bucket
    -------------------------------------------------------------
    "Aa"          2112              2112        0          0
    "BB"          2112              2112        0          0      ← COLLISION
    "Cc"          2143              2143       15         15

    "Aa" AND "BB" HAVE THE SAME hashCode — this is the famous String collision pair, and it is real:
    'A'*31 + 'a' = 2015 + 97 and 'B'*31 + 'B' = 2046 + 66 both equal 2112. So they must share a
    bucket, and no spread function can separate them, because the collision is in the hashCode itself.

    put("Aa", 1)   bucket 0 empty            → Node("Aa",1)
    put("BB", 2)   bucket 0 occupied         → walk: hash 2112 == 2112, so equals IS called
                                               "Aa".equals("BB") is false
                                             → append: bucket 0 = Node("Aa") → Node("BB")
    get("BB")      bucket 0                  → first node: hash matches, equals false, next
                                             → second node: hash matches, equals TRUE → 2

    NOTE THAT equals WAS CALLED TWICE for that get, and would have been called ZERO times if the
    hashes had differed — the `e.hash == hash` check is what makes a collision cheap when the hashes
    merely happen to mask to the same bucket, and expensive only when the hashes are genuinely equal.

THE SPREAD, MADE VISIBLE. A key type whose hashCode is `id << 16`:

    id    hashCode      binary (high|low)        & 15 WITHOUT spread   with spread
    -----------------------------------------------------------------------------
    1        65536      0000 0001 | 0000 0000            0                  1
    2       131072      0000 0010 | 0000 0000            0                  2
    3       196608      0000 0011 | 0000 0000            0                  3

    WITHOUT THE SPREAD, EVERY KEY GOES TO BUCKET 0 — a perfectly reasonable-looking hashCode reduced
    to a linked list. The XOR pulls the distinguishing bits down where the mask can see them. THAT IS
    THE WHOLE JUSTIFICATION FOR THAT ONE LINE.

THE RESIZE SPLIT, from 16 to 32. The mask goes from 0b01111 to 0b11111 — one new bit, value 16:

    entry     hash    hash & 16      old index    new index
    ------------------------------------------------------------
    A          33            0             1          1          (stays)
    B          17           16             1          17         (i + oldCap)
    C          49           16             1          17         (i + oldCap)
    D           1            0             1          1          (stays)

    ONE BUCKET BECAME TWO, decided by a single bit test, with no key comparisons and no calls to
    hashCode. Every entry that was at index 1 is now at 1 or 17 and nowhere else.

WHICH DESIGN CHOICE PRODUCED WHICH ROW:

    POWER-OF-TWO LENGTH    produced the `& 15` mask, and produced the one-bit resize split.
    THE SPREAD             produced the third table — delete it and those three keys collide forever.
    `e.hash == hash` FIRST produced "equals was called twice, and would have been zero times" —
                           the cheap guard that makes ordinary collisions nearly free.
    THE "Aa"/"BB" PAIR     is the case NO spread can fix, because the collision is in hashCode itself.
                           It is why treeification exists: some collisions cannot be hashed away.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    get / put / containsKey:  O(1) average, O(log n) worst case since Java 8, O(n) before.
    resize:                   O(n), amortized to O(1) per insertion by doubling.
    iteration:                O(capacity + size) — a large, sparse map is slow to iterate.
    memory:                   ~32-40 bytes per Node plus the table slot. A Map<Integer,Integer> of a
                              million entries is tens of MB against 8MB for two int arrays.

    DEFAULTS: initial capacity 16, load factor 0.75, treeify at 8 entries with a table of at least 64,
    untreeify back to a list at 6.

THE #1 MISTAKE: a mutable key. Insert, mutate, and get(thatVeryKey) returns null while the entry sits
in entrySet() and counts toward size().

THE #2 MISTAKE: equals without hashCode. Different buckets, never compared, entries lost.

THE #3 MISTAKE: depending on iteration order. Deterministic, and it changes on resize — so it passes
with ten keys and fails with thirteen.

THE #4 MISTAKE: sharing a HashMap across threads. Use ConcurrentHashMap; before Java 8 a concurrent
resize could build a circular list and spin a core forever.

THE #5 MISTAKE: not pre-sizing a known-large map, and then pre-sizing it wrong — the argument must be
expectedSize / 0.75, not expectedSize.

THE #6 MISTAKE: HashMap for enum keys. EnumMap is an array indexed by ordinal, with no hashing at all.

THE #7 MISTAKE: a constant or near-constant hashCode. Contract-compliant, and it turns the map into
one tree.

THE #8 MISTAKE: assuming a collision means something is wrong. Collisions are guaranteed by pigeonhole
and the table is built for them; only LONG buckets indicate a problem.

THE #9 MISTAKE: modifying the map inside computeIfAbsent's mapping function. Undefined on HashMap,
forbidden on ConcurrentHashMap.

THE #10 MISTAKE: reaching for a "faster map" before checking the hashCode. A bad hash is essentially
the only way a HashMap becomes slow.

ONE-SENTENCE TAKEAWAY: a HashMap is an array of buckets indexed by `hash & (length-1)` — a mask rather
than a modulo, which is why the length is a power of two, which in turn is why the hash must be SPREAD
with `h ^ (h >>> 16)` before masking or high-bit differences would be discarded entirely — with each
bucket a short list that becomes a red-black tree past eight entries (a denial-of-service fix, not a
performance one) and a resize that splits every bucket in two on a single bit test with no rehashing;
so the failures that matter are all about the KEY: mutate one and the entry becomes unreachable,
override equals without hashCode and it is lost, and depend on iteration order and it breaks the day
the table doubles.""",
]


def apply(entries):
    """Attach the deep dives, and fail loudly on a title that matches nothing.

    A silent no-op here would mean renaming an entry quietly detaches its deep
    dive, and nobody would notice until the card was opened months later.
    """
    by_title = {e["title"]: e for e in entries}
    missing = [t for t in DEEP if t not in by_title]
    if missing:
        raise KeyError("deep dive has no matching entry: " + "; ".join(missing))
    for title, sections in DEEP.items():
        if len(sections) != 10:
            raise ValueError(f"{title!r}: deep dive must be 10 sections, "
                             f"got {len(sections)}")
        by_title[title]["examples"] = list(sections)
    return entries


DEEP["synchronized, volatile, and atomic — three different problems"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two problems that look like one

When two threads touch the same data, two completely different things can go wrong, and almost every
concurrency bug comes from fixing one of them and assuming you fixed both.

    PROBLEM ONE — TAKING TURNS. Two threads run the same few lines at the same time and interleave.
    `count++` is really three steps: read the value, add one, write it back. Two threads can both read
    5, both compute 6, and both write 6. One increment simply vanishes. Nothing is corrupted, nothing
    throws — the number is just quietly wrong.

    PROBLEM TWO — SEEING. A thread writes a value and another thread never notices. Not "notices
    late" — never. The writing thread may keep the value in a CPU register, or the compiler may have
    decided the reading thread's loop can never change and hoisted the read out of it. Both are legal.

    THESE ARE INDEPENDENT. You can fix taking turns and still have an invisible write. You can fix
    seeing and still lose increments.

THE THREE TOOLS MAP ONTO THEM UNEVENLY, which is the source of the confusion:

    volatile     fixes SEEING only.               One variable.
    synchronized fixes BOTH.                      A block, at the cost of blocking.
    Atomic*      fixes BOTH.                      One variable, without blocking.

    SO `volatile int count; count++;` IS BROKEN, and it is broken in the exact way that survives every
    test you will write on your laptop and fails under load in production.

THE EVERYDAY VERSION: two people editing a shared shopping list. Taking turns is making sure you are
not both writing on the same line at once. Seeing is making sure the list you are looking at is the
current one, and not a photocopy you took ten minutes ago.

TERMS AS THEY APPEAR:
- VISIBILITY: whether one thread's write becomes observable to another.
- ATOMICITY: whether an operation happens all at once, with no other thread able to interleave.
- HAPPENS-BEFORE: the ordering guarantee the memory model actually gives you.""",

"""2. THE INTUITION — why "seeing" is even a problem

The natural assumption is that when a thread writes to a field, the value goes into memory and any
other thread reading that field gets it. That assumption is wrong on every modern machine, and it is
wrong for THREE separate reasons stacked on top of each other.

    1. THE COMPILER REORDERS. javac and, far more aggressively, the JIT may reorder any two operations
       whose order is not observable WITHIN A SINGLE THREAD. `a = 1; b = 2;` may become `b = 2; a = 1;`
       because no single-threaded program can tell. Another thread absolutely can.

    2. THE CPU REORDERS. Store buffers, out-of-order execution, speculative loads. A write may sit in
       a core's store buffer for a while before any other core can see it.

    3. THE CACHES ARE PER-CORE. A value read into a register or an L1 cache line may be re-read from
       there indefinitely. The classic symptom is a `while (!stopFlag)` loop that never exits, because
       the JIT hoisted the read out of the loop entirely — which it is entitled to do, since within
       that one thread nothing writes to stopFlag.

    NONE OF THIS IS A BUG. Every one of those transformations makes single-threaded code faster and is
    permitted by the specification. THE JAVA MEMORY MODEL EXISTS TO SAY EXACTLY WHEN YOU ARE ALLOWED
    TO ASSUME OTHERWISE.

AND THE MODEL'S ANSWER IS A SINGLE RELATION: HAPPENS-BEFORE.

    If action A happens-before action B, then everything A did is visible to B. If there is NO
    happens-before edge between two actions in different threads, YOU ARE GUARANTEED NOTHING — not
    "probably fine", not "eventually consistent", nothing.

THE EDGES YOU GET FOR FREE — and this list is short enough to memorise, which is the point:

    PROGRAM ORDER      within one thread, earlier statements happen-before later ones.
    MONITOR            unlocking a monitor happens-before any later lock of that same monitor.
    VOLATILE           a write to a volatile happens-before any later read of it.
    THREAD START       Thread.start() happens-before anything the new thread does.
    THREAD JOIN        everything a thread does happens-before join() returns.
    FINAL FIELDS       a correctly-constructed object's final fields are visible without any
                       synchronisation at all.

    EVERY CORRECT CONCURRENT PROGRAM IS BUILT OUT OF THOSE EDGES. If you cannot point at one, you do
    not have a guarantee.""",

"""3. THE MECHANISM — what each tool actually does

VOLATILE. A read of a volatile is guaranteed to see the most recent write, and reads and writes cannot
be reordered across it. Concretely the JIT emits memory barriers: a write is followed by a store
barrier, a read preceded by a load barrier.

    THE PART PEOPLE MISS: a volatile write also publishes EVERYTHING THE THREAD WROTE BEFORE IT. That
    is why volatile is useful for more than the one variable — writing a volatile flag after filling a
    data structure makes the whole structure visible to any thread that reads the flag.

    WHAT IT DOES NOT DO: make a read-modify-write atomic. `count++` on a volatile is still three
    operations with a gap in the middle.

SYNCHRONIZED. Acquiring a monitor blocks until it is free; releasing it flushes everything the thread
wrote. So it gives mutual exclusion AND the same visibility guarantee as volatile, over a whole block
rather than one variable.

    THE COST is blocking: a thread that cannot acquire the lock parks, and parking and unparking is a
    trip through the OS scheduler. Modern JVMs mitigate with BIASED and THIN locks so an uncontended
    lock is nearly free — the expense is contention, not the keyword.

ATOMIC CLASSES. AtomicInteger and friends are built on COMPARE-AND-SWAP, a single CPU instruction that
says "if this memory location still holds X, replace it with Y, and tell me whether you did".

    incrementAndGet is a LOOP:
        read the current value v
        compute v + 1
        compareAndSet(v, v + 1)
        if it failed, somebody else got there first — go round again

    NO THREAD EVER BLOCKS. A thread that loses the race retries immediately. That is LOCK-FREE: the
    system as a whole always makes progress, even though an individual thread might retry several
    times. Under moderate contention it beats a lock comfortably; under EXTREME contention the retries
    themselves become the bottleneck, which is why LongAdder exists — it spreads the count across
    several cells and sums them only when you ask.

    THE LIMIT: CAS works on ONE variable. An invariant spanning two fields — "a + b must stay
    constant" — cannot be maintained by two atomics, no matter how atomic each one is. That needs a
    lock, or a single immutable object holding both swapped atomically.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `volatile` ON A COUNTER. The canonical mistake. Visibility without atomicity: ten threads
incrementing a volatile int a thousand times each reliably total LESS than 10,000.

CASE 2 — DOUBLE-CHECKED LOCKING WITHOUT `volatile`. The famous one:

        if (instance == null) { synchronized (lock) { if (instance == null) instance = new Thing(); } }

    Without a volatile field this is BROKEN, and subtly. `instance = new Thing()` is really: allocate,
    run the constructor, assign the reference. The JIT may reorder the last two, so another thread can
    see a NON-NULL reference to a HALF-CONSTRUCTED object, skip the synchronized block entirely, and
    use it. Making the field volatile forbids that reordering and fixes it. USE A STATIC HOLDER CLASS
    INSTEAD and the problem does not arise — class initialisation is already thread-safe.

CASE 3 — `synchronized` ON A METHOD locks `this`. Any unrelated caller who synchronizes on your object
now blocks you, and they may not know they are doing it. USE A PRIVATE FINAL LOCK OBJECT.

CASE 4 — SYNCHRONIZING ON SOMETHING MUTABLE OR SHARED. Locking on a String literal or a boxed Integer
means locking on an interned, JVM-wide object — anyone else with the same literal shares your lock.
Locking on a field you then reassign means two threads lock different objects and neither excludes the
other.

CASE 5 — NON-ATOMIC `long` AND `double`. The spec permits a 64-bit non-volatile write to be split into
two 32-bit halves, so another thread can observe a value that was never written. Rare on 64-bit JVMs
and permitted, so declare shared longs volatile.

CASE 6 — TWO ATOMICS, ONE INVARIANT. Each operation is atomic and the PAIR is not. If a + b must stay
constant, atomics cannot do it.

CASE 7 — CHECK-THEN-ACT ON A CONCURRENT COLLECTION. `if (!map.containsKey(k)) map.put(k, v)` races
even on a ConcurrentHashMap. Each call is atomic; a sequence of calls is not. Use putIfAbsent.

CASE 8 — THE ABA PROBLEM. CAS checks the VALUE, not the history. A value that changed from A to B and
back to A passes compareAndSet as though nothing happened. Usually harmless for counters, fatal for
lock-free stacks — AtomicStampedReference adds a version counter for exactly this.

CASE 9 — SWALLOWING InterruptedException. Catching it CLEARS the interrupt flag, so every caller above
you loses the cancellation signal. Restore it: `Thread.currentThread().interrupt()`.

CASE 10 — TESTING FOR CORRECTNESS. You cannot. A race that never appears in a million runs on your
laptop appears in the first hour on a machine with a different core count. REASON ABOUT THE
HAPPENS-BEFORE EDGES; the test can only ever find a bug, never establish its absence.""",

"""5. THE ALTERNATIVES — and what each costs

DON'T SHARE STATE AT ALL. Immutable objects, thread confinement, message passing, a copy per thread.
NO SYNCHRONISATION IS NEEDED FOR DATA NOBODY ELSE CAN SEE OR CHANGE, and this remains the best answer
by a wide margin. Most concurrency bugs are the punishment for sharing something that did not need to
be shared.

IMMUTABLE OBJECTS. All fields final, no setters, defensive copies of mutable components. The memory
model's FINAL FIELD guarantee means a correctly-constructed immutable object is safe to publish
anywhere with no synchronisation at all. Update by replacing the whole object, via an
AtomicReference if it must be shared.

volatile. One variable, visibility only, and free on reads. RIGHT FOR: a flag written by one thread and
polled by others; a reference published after being fully built. WRONG FOR: anything read-modify-write.

Atomic*. One variable, lock-free, and it scales better than a lock under moderate contention. Under
severe contention use LongAdder for counters — it spreads writes across cells and only sums on read.

synchronized. Both problems, any number of variables, arbitrary blocks. THE DEFAULT WHEN AN INVARIANT
SPANS MORE THAN ONE FIELD. Uncontended it is nearly free; the cost is contention.

ReentrantLock. Everything synchronized does, plus tryLock with a timeout, interruptible acquisition,
fairness, and multiple Conditions. THE COST is that you must unlock in a finally block — the language
does it for you with synchronized and will not here. ALSO: it does NOT pin a virtual thread where
synchronized does, which makes it the preferred choice on Java 21.

CONCURRENT COLLECTIONS. ConcurrentHashMap, BlockingQueue, CopyOnWriteArrayList. Almost always better
than a lock you wrote around a plain collection, because the locking is finer-grained than you would
bother to make it.

HIGHER-LEVEL COORDINATION. CountDownLatch (wait for N events, once), CyclicBarrier (N threads meet
repeatedly), Semaphore (N permits), Phaser. PREFER THESE TO wait/notify, which is error-prone —
notify() wakes an arbitrary waiter and a wait() must always sit in a loop because of spurious wakeups.""",

"""6. HOW TO GET IT RIGHT — numbered steps

STEP 1 — TRY NOT TO SHARE. Confine the data to one thread, or make it immutable. Everything below is
the price of failing this step.

STEP 2 — IF IT IS SHARED AND NEVER CHANGES, MAKE IT `final`. The final-field guarantee means it needs
no synchronisation at all.

STEP 3 — IDENTIFY WHICH PROBLEM YOU HAVE. Only visibility, with a single writer? volatile. A
read-modify-write on one variable? Atomic. An invariant across several fields? A lock.

STEP 4 — NEVER USE `volatile` FOR A COUNTER. `++` is three operations regardless of the modifier.

STEP 5 — LOCK ON A PRIVATE FINAL OBJECT, not on `this` and not on a class you do not own. `private
final Object lock = new Object();`

STEP 6 — HOLD THE LOCK FOR THE WHOLE INVARIANT AND NOT ONE INSTRUCTION LONGER. Never call unknown code
— a listener, a callback, an overridable method — while holding a lock; that is how deadlocks form
between your code and code you have never read.

STEP 7 — IF YOU NEED TWO LOCKS, ORDER THEM GLOBALLY. Same locks, same order, no cycle, no deadlock.

STEP 8 — PREFER THE CONCURRENT COLLECTION TO A LOCK YOU WROTE. It is finer-grained than yours.

STEP 9 — DOCUMENT THE POLICY. "All access to `balance` is guarded by `lock`" as a comment or a
@GuardedBy annotation. A concurrency policy that lives only in one person's head is not a policy.

STEP 10 — REASON, DO NOT TEST. Point at the happens-before edge. A passing test proves nothing about a
race, and the absence of a failure on your machine is not evidence.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'There are two problems here, not one, and most concurrency bugs come from fixing one and assuming you
fixed both.

The first is TAKING TURNS. `count++` is really read, add, write — three steps — so two threads can
both read 5, both compute 6, and both write 6. One increment vanishes silently.

The second is SEEING. A thread writes a value and another thread never observes it. Not late — never.
And there are three independent reasons: the compiler can reorder anything whose order isn't
observable within a single thread; the CPU reorders too, with store buffers and out-of-order
execution; and caches are per-core, so a value read into a register can be re-read from there forever.
The classic symptom is a `while (!stopFlag)` loop that never exits because the JIT hoisted the read
out — which it's entitled to do, since nothing in THAT thread writes to the flag.

None of that is a bug. Every one of those transformations makes single-threaded code faster and is
permitted. The Java Memory Model exists to say exactly when you're allowed to assume otherwise, and
its answer is one relation: HAPPENS-BEFORE. If A happens-before B, everything A did is visible to B.
If there's no edge between two actions in different threads, you're guaranteed NOTHING — not
"probably fine", nothing.

The edges you get for free are a short list worth memorising: program order within a thread; unlocking
a monitor before any later lock of it; a volatile write before any later read of it; Thread.start
before anything the thread does; everything a thread does before join returns; and final fields of a
correctly-constructed object, which are visible with no synchronisation at all.

So the three tools map onto the two problems unevenly. VOLATILE fixes seeing only — one variable, and
a volatile write also publishes everything the thread wrote BEFORE it, which is why it's useful for
more than the one field. SYNCHRONIZED fixes both, over a whole block, at the cost of blocking. And the
ATOMIC classes fix both for a single variable without blocking, using compare-and-swap in a retry
loop — no thread ever parks, so under moderate contention they beat a lock.

The headline mistake is `volatile int count; count++;`. Visibility without atomicity, and it's broken
in exactly the way that survives every test on your laptop and fails under load.

The second one I'd raise is DOUBLE-CHECKED LOCKING without a volatile field. `instance = new Thing()`
is allocate, construct, assign — and the JIT may reorder the last two, so another thread sees a
non-null reference to a HALF-CONSTRUCTED object, skips the synchronized block, and uses it. volatile
forbids the reordering. Though I'd use a static holder class instead, because class initialisation is
already thread-safe and the problem never arises.

And the thing I'd want to land: YOU CANNOT TEST FOR THIS. A race that never appears in a million runs
on your machine appears in the first hour on one with a different core count. You have to point at the
happens-before edge; a test can find a bug but never establish its absence.'""",

"""8. THE CODE, LINE BY LINE

    // ── WRONG. The single most common concurrency mistake in Java. ──────
    static volatile int broken = 0;
    static void incBroken() { broken++; }
    //                        ^^^^^^^^ THREE operations: read broken, add 1,
    //   write broken. `volatile` guarantees each of those three SEES the
    //   latest value and does nothing whatever about the GAPS between them.
    //   Two threads read 5, both write 6, one increment is gone.
    //   VOLATILE IS ABOUT SEEING, NOT ABOUT WINNING.

    // ── RIGHT for a single counter: one indivisible operation. ──────────
    static final AtomicInteger counter = new AtomicInteger();
    static void incAtomic() { counter.incrementAndGet(); }
    //                                ^^^^^^^^^^^^^^^^ internally a CAS LOOP:
    //   read v; compute v+1; compareAndSet(v, v+1); if it failed, retry.
    //   NO THREAD EVER BLOCKS — a loser retries immediately. Lock-free.
    //   Under EXTREME contention the retries themselves cost; that is what
    //   LongAdder is for.

    // ── RIGHT for an invariant spanning several fields. ─────────────────
    private static final Object lock = new Object();
    //      ^^^^^^^ PRIVATE and FINAL. Synchronizing on `this` lets any
    //      unrelated caller who locks your object block you, possibly without
    //      knowing they are doing it. Private means only your code can lock it.
    static int a = 0, b = 0;
    static void moveOne() {
        synchronized (lock) { a--; b++; }
        //                    ^^^^^^^^^ a + b stays constant. TWO ATOMICS
        //   COULD NOT DO THIS — each operation would be atomic and the PAIR
        //   would not, so another thread could observe the moment between them.
    }

    // ── THE CLASSIC volatile: a flag, one writer, many readers. ─────────
    static volatile boolean running = true;
    static void worker() {
        while (running) { /* ... */ }
        //     ^^^^^^^ WITHOUT volatile the JIT may hoist this read out of the
        //     loop entirely — nothing in THIS thread writes to it — and the
        //     loop never terminates. With it, the read is guaranteed fresh.
    }

    // ── DOUBLE-CHECKED LOCKING. The volatile is not optional. ───────────
    private static volatile Thing instance;
    //             ^^^^^^^^ REMOVE THIS AND THE CODE IS BROKEN. `new Thing()`
    //   is allocate, construct, assign — and the last two may be REORDERED, so
    //   another thread can see a non-null reference to a half-built object,
    //   skip the synchronized block, and use it.
    static Thing get() {
        if (instance == null) {                    // cheap, unsynchronised
            synchronized (lock) {
                if (instance == null)              // re-check under the lock
                    instance = new Thing();
            }
        }
        return instance;
    }

    // ── BETTER: the holder idiom. No locks, no volatile, no reasoning. ──
    private static class Holder { static final Thing INSTANCE = new Thing(); }
    static Thing getBetter() { return Holder.INSTANCE; }
    //  ^ Class initialisation is ALREADY thread-safe and lazy — the JVM
    //    guarantees it runs exactly once, on first use. The whole problem
    //    above simply does not arise.""",

"""9. THE TRACE — the increment that vanishes, and the edge that saves it

TWO THREADS, ONE `volatile int count = 0`, one increment each.

    time   thread A                     thread B                     count in memory
    ---------------------------------------------------------------------------------
    t1     read count → 0                                                   0
    t2                                  read count → 0                      0
    t3     compute 0 + 1 = 1                                                0
    t4                                  compute 0 + 1 = 1                   0
    t5     write 1                                                          1
    t6                                  write 1                             1

    TWO INCREMENTS, FINAL VALUE 1. And `volatile` did its job perfectly at every step — both reads saw
    the true current value of 0, and both writes were immediately visible. THE PROBLEM IS THE GAP
    BETWEEN t1 AND t5, which no amount of visibility can close.

THE SAME SEQUENCE WITH AtomicInteger:

    time   thread A                              thread B                       count
    ---------------------------------------------------------------------------------
    t1     read 0, compute 1                                                       0
    t2                                           read 0, compute 1                 0
    t3     compareAndSet(0, 1) → SUCCESS                                           1
    t4                                           compareAndSet(0, 1) → FAILS       1
    t5                                           (it saw 0, memory holds 1)
    t6                                           RETRY: read 1, compute 2          1
    t7                                           compareAndSet(1, 2) → SUCCESS     2

    THE FAILED CAS AT t4 IS THE WHOLE MECHANISM. Thread B's assumption ("count is still 0") was
    checked at the instant of the write and found to be stale, so the write did not happen and B went
    round again. Nobody blocked; B simply did the work twice.

THE VISIBILITY FAILURE, which is a different shape entirely:

    boolean running = true;      // NOT volatile

    thread A                                thread B
    -----------------------------------------------------------------------
    while (running) { ... }                 running = false;
      ^ the JIT observes that nothing in
        THIS thread writes to `running`,
        hoists the read out of the loop,
        and compiles it to `while (true)`
                                            ^ the write happens, and lands in
                                              B's store buffer or B's cache

    THREAD A NEVER STOPS. Not "stops late" — never. And the program is correct on every JVM that
    happens not to make that optimisation, which is why this reliably works in development and hangs
    in production.

    THE FIX IS ONE KEYWORD, and what it buys is precisely a happens-before edge: B's volatile WRITE
    happens-before A's subsequent volatile READ, so the read cannot be hoisted and cannot be stale.

WHICH LINE PRODUCED WHICH ROW:

    `volatile` ON THE COUNTER      produced correct reads at t1 and t2 and did nothing about the gap.
                                   Visibility was never the problem in that table.
    THE THREE-STEP `++`            produced the lost update. Any read-modify-write has this shape,
                                   including `x = x + 1`, `list.size()` then `list.add()`, and
                                   check-then-act on a map.
    `compareAndSet`                produced the FAILURE at t4, which is the only reason the final
                                   value is 2. A CAS that could not fail would be a plain write.
    THE ABSENCE OF `volatile` on the flag
                                   produced the infinite loop — and note the loop is not "slow to
                                   notice", it is compiled to never check again.""",
"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    volatile      read is free (a plain load plus a barrier); write costs a store barrier. VISIBILITY
                  AND ORDERING ONLY — no atomicity, ever.
    synchronized  uncontended is nearly free on a modern JVM (thin locks); CONTENDED costs a park and
                  unpark through the OS scheduler, which is microseconds. Both problems solved.
    Atomic*       lock-free CAS retry loop. Beats a lock under moderate contention, degrades under
                  extreme contention as retries pile up — use LongAdder for hot counters.
    final fields  free. A correctly-constructed object's final fields are visible with NO
                  synchronisation at all, which is why immutability is the cheapest concurrency
                  strategy there is.

    THE MODEL IN ONE SENTENCE: without a happens-before edge between two actions in different threads,
    you are guaranteed nothing.

THE #1 MISTAKE: `volatile` on a counter. Visibility without atomicity — `++` is three operations, and
ten threads incrementing a thousand times each reliably total less than 10,000.

THE #2 MISTAKE: double-checked locking without a volatile field. The construction can be reordered
past the assignment, publishing a half-built object. Use a static holder class instead.

THE #3 MISTAKE: `synchronized` on a method, which locks `this`. Any unrelated caller locking your
object blocks you. Use a private final lock.

THE #4 MISTAKE: locking on a String literal, a boxed Integer, or a field you reassign. The first two
are JVM-wide interned objects; the third means two threads lock different objects and neither excludes
the other.

THE #5 MISTAKE: two atomics guarding one invariant. Each operation is atomic and the PAIR is not.

THE #6 MISTAKE: check-then-act on a concurrent collection. Every individual call is atomic; a sequence
of them is not. That is what putIfAbsent, merge and compute exist for.

THE #7 MISTAKE: assuming a 64-bit `long` write is atomic. The spec permits it to be split in two, so a
shared long should be volatile.

THE #8 MISTAKE: swallowing InterruptedException. Catching it CLEARS the flag, destroying the
cancellation signal for every caller above you. Restore it.

THE #9 MISTAKE: calling unknown code — a listener, a callback, an overridable method — while holding a
lock. That is how a deadlock forms with code you have never read.

THE #10 MISTAKE: believing a passing test. A race that never appears in a million runs on your laptop
appears in the first hour on a machine with a different core count.

ONE-SENTENCE TAKEAWAY: there are TWO problems and three tools that cover them unevenly — `volatile`
fixes SEEING only, `synchronized` fixes seeing and TAKING TURNS at the cost of blocking, and the atomic
classes fix both for a single variable with a lock-free CAS retry loop — so `volatile int count;
count++;` is broken in exactly the way that passes every test on your laptop; and the only real tool
for reasoning about any of it is HAPPENS-BEFORE, because without an edge between two actions in
different threads the specification guarantees you nothing at all.""",
]


DEEP["Generics and type erasure — what actually survives to runtime"] = [
"""1. THE GOAL IN PLAIN ENGLISH — a promise the compiler keeps and then forgets

`List<String>` tells the compiler "this list holds Strings". The compiler checks every add and every
get against that promise, and then — this is the part that surprises people — IT THROWS THE PROMISE
AWAY. The class file contains a plain `List`. At runtime there is no such thing as a List of Strings;
there is a List, and a set of casts the compiler quietly inserted wherever you read from it.

    List<String> names = new ArrayList<>();
    names.add("hi");
    String s = names.get(0);

    ...compiles to roughly:

    List names = new ArrayList();
    names.add("hi");
    String s = (String) names.get(0);
                ^^^^^^^^ YOU DID NOT WRITE THIS CAST. The compiler did, because it knows the promise
                and the runtime does not.

THAT IS ERASURE, and almost every strange rule about Java generics is a direct consequence of it. You
cannot make an array of a type parameter. You cannot ask an object what its generic type is. Two
methods differing only in their generic parameter will not compile. None of those are arbitrary —
they all reduce to "there is nothing there at runtime to check".

THE EVERYDAY VERSION: a customs form declaring the contents of a box. The inspector checks the form
against the contents at the border, stamps it, and then removes the form. Downstream, the box is just
a box — and anyone who tears the form off before the border can put anything they like inside.

TERMS AS THEY APPEAR:
- ERASURE: replacing a type parameter with its bound and inserting casts.
- RAW TYPE: `List` with no parameter — the pre-generics form, still legal for compatibility.
- HEAP POLLUTION: a variable of a parameterised type referring to an object that is not of that type.""",

"""2. THE INTUITION — why Java chose erasure, when C# chose otherwise

Generics arrived in Java 5, nine years after the language. By then there were millions of lines of
`List` and `Map` in production and, more importantly, millions of COMPILED CLASS FILES in jars nobody
was going to rebuild.

    THE CONSTRAINT WAS MIGRATION COMPATIBILITY, and it was absolute:
    * new code using `List<String>` had to work with old libraries expecting `List`;
    * old compiled code had to keep running on the new JVM unchanged;
    * a library could add generics to its signatures WITHOUT breaking its existing callers.

    ERASURE SATISFIES ALL THREE FOR FREE, because after erasure the new code IS the old code. A
    `List<String>` and a raw `List` are byte-for-byte the same type to the JVM, so they interoperate
    perfectly and no bytecode had to change.

    C# MADE THE OPPOSITE CHOICE two years later and REIFIED its generics — the runtime genuinely knows
    a `List<string>` from a `List<int>`. It could, because .NET was young enough that breaking the
    ecosystem was affordable, and because they changed the runtime itself. Java could not change the
    JVM without invalidating every class file in existence.

    SO THE TRADE IS EXPLICIT: C# gets `new T[]`, `typeof(T)`, `List<int>` without boxing, and paid for
    it with a runtime change. Java got a smooth migration and pays for it in every restriction below.

    THAT IS THE ANSWER TO "WHY IS JAVA'S GENERICS SYSTEM LIKE THIS" — not an oversight, a deliberate
    purchase. And Project Valhalla is the long-running attempt to buy back the specialisation without
    breaking anything, which is why it has been in progress for over a decade.

WHAT ERASURE ACTUALLY DOES, precisely:

    <T>                    becomes Object
    <T extends Number>     becomes Number          ← the LEFTMOST BOUND, not Object
    <T extends A & B>      becomes A
    List<String>           becomes List
    T[]                    becomes Object[]

    ...and the compiler inserts a checked cast at every point where a value of type T is read out.""",

"""3. THE MECHANISM — casts, bridge methods, and where the exception lands

THE CASTS ARE THE VISIBLE HALF. Every read of a generic value gets a compiler-inserted cast, which is
why a mistake surfaces AT THE READ rather than at the write:

    List<String> a = new ArrayList<>();
    List raw = a;                 // legal, with an unchecked warning
    raw.add(42);                  // NO CHECK HAPPENS HERE. The list has no idea.
    String s = a.get(0);          // ClassCastException HERE — at a line that looks correct

    THE EXCEPTION LANDS AT A CAST YOU DID NOT WRITE, IN A LINE THAT HAS NOTHING WRONG WITH IT. That
    displacement is the practical cost of erasure and it is why unchecked warnings are worth taking
    seriously — they mark the place where the compiler stopped being able to help.

BRIDGE METHODS ARE THE INVISIBLE HALF, and they are the part that most people have never heard of.

    Consider `class StringBox implements Comparable<StringBox>` with
    `public int compareTo(StringBox other)`.

    After erasure, `Comparable`'s method is `compareTo(Object)`. But StringBox declares
    `compareTo(StringBox)` — a DIFFERENT SIGNATURE, so by the JVM's rules it does not override
    anything, and polymorphism would break: `Comparable c = new StringBox(); c.compareTo(x)` would
    find no implementation.

    SO javac GENERATES A THIRD METHOD you never wrote:

        public int compareTo(Object o) { return compareTo((StringBox) o); }   // synthetic, bridge

    That bridge restores the override relationship and inserts the cast. It is why passing the wrong
    type through a raw reference throws ClassCastException inside a method whose source contains no
    cast at all — the cast is in the bridge.

WHAT SURVIVES ERASURE, which is the detail that makes reflection possible at all:

    The class file keeps a SIGNATURE ATTRIBUTE recording the generic type of FIELDS, of METHOD
    PARAMETERS AND RETURN TYPES, and of CLASS AND INTERFACE DECLARATIONS.

    So reflection CAN tell you that a field is declared `List<String>`, or that a method returns
    `Map<String, List<Integer>>`. What it CANNOT tell you is the type argument of an OBJECT — because
    the object genuinely does not carry one.

    THAT GAP IS EXACTLY WHAT THE SUPER TYPE TOKEN TRICK EXPLOITS. `new TypeReference<List<String>>(){}`
    creates an anonymous SUBCLASS, and a subclass's generic superclass IS recorded in the Signature
    attribute — so the type argument can be recovered by reflection. It is how Jackson and Gson accept
    a generic target type, and it works only because of what the class file kept.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `new T[10]` IS ILLEGAL. There is no T at runtime, so the array has no element type to check
stores against. The workaround is `(T[]) new Object[10]` plus an unchecked warning — and it can throw
ClassCastException later at a compiler-inserted cast somewhere else entirely. ArrayList does exactly
this internally, and keeps the array `Object[]` privately to contain the damage.

CASE 2 — `instanceof List<String>` IS ILLEGAL. Nothing to test. Only `instanceof List<?>` compiles.

CASE 3 — TWO METHODS WITH THE SAME ERASURE CLASH. `f(List<String>)` and `f(List<Integer>)` both erase
to `f(List)` and the error says so literally: "have the same erasure". Note `f(List<String>)` and
`f(Set<String>)` are fine — their erasures differ.

CASE 4 — A STATIC MEMBER CANNOT USE THE CLASS'S TYPE PARAMETER. There is ONE static field for all
parameterisations, so `static T instance;` has no coherent meaning.

CASE 5 — YOU CANNOT CATCH A GENERIC EXCEPTION. `catch (T e)` is illegal, because catch matching is a
runtime type test.

CASE 6 — HEAP POLLUTION VIA VARARGS. `static <T> void f(T... args)` creates a `T[]`, which erases to
`Object[]`, which can be assigned anything. That is why javac warns and why @SafeVarargs exists — the
annotation is YOU ASSERTING the method never stores into the array.

CASE 7 — OVERLOADING ON A BOUND. `<T extends Number>` erases to Number, so a method taking it clashes
with one taking Number.

CASE 8 — A GENERIC ARRAY CREATION EXPRESSION. `new List<String>[10]` is illegal for the same reason as
case 1, and the workaround has the same caveat.

CASE 9 — RAW TYPES DISABLE GENERICS ENTIRELY, not just for the raw variable. Using a raw `List`
suppresses type checking on OTHER generic methods of the same class, which is a deliberately blunt
rule from the migration era and a good reason never to use raw types in new code.

CASE 10 — `List<Object>` IS NOT A SUPERTYPE OF `List<String>`. Generics are INVARIANT, and this is the
restriction people resent most — it exists because arrays made the other choice and pay for it with a
runtime check on every store.""",

"""5. THE ALTERNATIVES — living with erasure

WILDCARDS, which recover most of the flexibility invariance takes away.

    `List<? extends Number>` — a PRODUCER. You may READ Numbers from it; you may not add, because the
    actual list might be a List<Double>.
    `List<? super Integer>` — a CONSUMER. You may ADD Integers; you may only read Objects, because the
    actual list might be a List<Object>.
    PECS: Producer Extends, Consumer Super. It is the single most useful mnemonic in Java generics and
    Collections.copy(dest, src) is the canonical signature carrying both.

CLASS TOKENS, when you genuinely need the type at runtime.

    `<T> T read(Class<T> type, String json)` — pass the Class object explicitly, and use
    `type.cast(x)` for a checked cast. It is what erasure forces and it is honest about it.

SUPER TYPE TOKENS, for generic targets a Class cannot express.

    `new TypeReference<List<String>>(){}` — an anonymous subclass, whose generic superclass IS in the
    Signature attribute and IS readable by reflection. Jackson's TypeReference and Guava's TypeToken.

MAKE THE ARRAY AN ArrayList. Most `new T[]` problems evaporate: an ArrayList has none of the
restrictions and is what you wanted anyway.

REIFIED GENERICS, for comparison and not as an option. C#, and Kotlin's `inline fun <reified T>` which
achieves it by INLINING the function at each call site so the compiler can substitute the concrete
type. Java's Project Valhalla is the long-running effort to get specialisation without breaking the
existing model.

WHAT TO SAY IN AN INTERVIEW: "Generics are compile-time only — erased to their bound with casts
inserted. If I need the type at runtime I pass a Class token, or a TypeReference for a parameterised
target. And I'd never use a raw type in new code, because it disables type checking more broadly than
people expect."

""",

"""6. HOW TO WORK WITH IT — numbered steps

STEP 1 — TREAT UNCHECKED WARNINGS AS ERRORS. Each one marks a place the compiler stopped being able to
help, and where a ClassCastException may later surface somewhere unrelated.

STEP 2 — NEVER USE A RAW TYPE IN NEW CODE. It disables generic checking beyond the one variable, and
it is only legal at all for the sake of 2004.

STEP 3 — PREFER A List TO AN ARRAY when a type parameter is involved. It sidesteps the array
restrictions entirely.

STEP 4 — USE WILDCARDS ON PARAMETERS, PECS. A method that only reads takes `? extends T`; one that only
writes takes `? super T`. It widens what callers can pass at no cost to you.

STEP 5 — PASS A `Class<T>` TOKEN when you genuinely need the runtime type — for a cast, a reflective
instantiation or a deserialisation target.

STEP 6 — USE A SUPER TYPE TOKEN for a parameterised target, and know WHY it works: a subclass's generic
superclass survives in the Signature attribute where an object's own type argument does not.

STEP 7 — CONFINE ANY UNCHECKED CAST TO ONE PRIVATE PLACE, annotate it @SuppressWarnings("unchecked")
narrowly, and comment why it is safe. A suppression on a whole class hides the next one.

STEP 8 — USE @SafeVarargs ONLY WHEN IT IS TRUE — the method must never store into the varargs array nor
let it escape.

STEP 9 — REMEMBER STATIC MEMBERS CANNOT USE THE CLASS'S PARAMETER. Make the METHOD generic instead:
`static <T> Box<T> empty()`.

STEP 10 — WHEN AN OVERLOAD WILL NOT COMPILE, CHECK THE ERASURES. "Have the same erasure" means the two
signatures are identical after type parameters are stripped, and the fix is different names.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Generics in Java are a COMPILE-TIME feature. The compiler checks every use against the declared type
and then erases it — the class file just contains `List`, and the compiler has inserted casts wherever
you read from it. So at runtime there's no such thing as a List of Strings; a List<String> and a
List<Integer> are the same class, and `getClass()` on both returns ArrayList.

The reason is MIGRATION COMPATIBILITY, and it was an absolute constraint rather than an oversight.
Generics arrived nine years into Java's life, when there were millions of compiled class files nobody
was going to rebuild. Erasure means new generic code IS old raw code after compilation, so they
interoperate perfectly and no bytecode had to change. C# made the opposite call two years later and
reified its generics — it could, because .NET was young enough to break its ecosystem and because they
changed the runtime. Java couldn't change the JVM without invalidating every jar in existence.

So the trade was bought deliberately: C# gets `new T[]`, `typeof(T)` and `List<int>` without boxing;
Java got a smooth migration and pays for it in every restriction. That's the honest answer to "why is
Java's generics system like this".

What erasure does precisely: an unbounded T becomes Object, a bounded `T extends Number` becomes
NUMBER — the leftmost bound, not Object — and casts go in at every read.

The consequence people hit first is that the exception lands in the wrong place. If you smuggle a
wrong value in through a raw reference, the add succeeds silently — the list has no idea what it's
supposed to hold — and the ClassCastException fires later at `String s = list.get(0)`, a line that
looks completely correct. The cast that fails is one you never wrote.

The half most people haven't heard of is BRIDGE METHODS. If you implement `Comparable<StringBox>`, you
write `compareTo(StringBox)` — but after erasure the interface's method is `compareTo(Object)`, a
different signature, so by the JVM's rules yours doesn't override anything and polymorphism would
break. So javac generates a synthetic bridge, `compareTo(Object)`, that casts and delegates. That's
why the ClassCastException can appear inside a method whose source contains no cast — it's in the
bridge.

And the thing worth knowing about what SURVIVES: the class file keeps a Signature attribute recording
the generic types of fields, method signatures and class declarations. So reflection CAN tell you a
field is declared List<String>. What it can't tell you is an OBJECT's type argument, because the
object genuinely doesn't carry one. That gap is exactly what the super-type-token trick exploits —
`new TypeReference<List<String>>(){}` creates an anonymous SUBCLASS, and a subclass's generic
superclass IS in the Signature attribute. It's how Jackson accepts a generic target type.

Practically: never use raw types in new code, treat unchecked warnings as errors, use wildcards on
parameters — PECS, producer extends, consumer super — and pass a Class token when you genuinely need
the type at runtime.'""",

"""8. THE CODE, LINE BY LINE

    List<String> a = new ArrayList<>();
    List<Integer> b = new ArrayList<>();
    System.out.println(a.getClass() == b.getClass());     // true
    //                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^ THE SAME CLASS OBJECT. There is
    //   one ArrayList class and it has no idea what it was declared to hold.
    //   This single line is erasure in its entirety.

    // ── SMUGGLING A WRONG VALUE IN, AND WHERE IT SURFACES ───────────────
    List raw = a;
    //   ^^^ A RAW TYPE. Legal, with an unchecked warning — and legal only because
    //   pre-2004 code had to keep compiling. Never write this deliberately.
    raw.add(42);
    //  ^^^^^^^ NO CHECK OCCURS. The ArrayList has no element type at runtime, so
    //  there is nothing to check against. The list now genuinely holds an Integer
    //  in a variable the compiler believes holds Strings — HEAP POLLUTION.
    // String s = a.get(0);
    //            ^^^^^^^^^ ClassCastException HERE, at a compiler-inserted
    //  (String) cast, on a line containing no visible cast and no visible fault.
    //  THE DISPLACEMENT BETWEEN THE BUG AND THE CRASH IS THE COST OF ERASURE.

    // ── A BOUNDED PARAMETER ERASES TO THE BOUND, NOT TO OBJECT ──────────
    static <T extends Number> double sum(List<T> xs) {
        //   ^^^^^^^^^^^^^^^ erases to Number. Which is exactly why the next line
        //   compiles — the erased parameter type has doubleValue(). An unbounded
        //   <T> would erase to Object and this would not compile.
        double t = 0;
        for (T x : xs) t += x.doubleValue();
        return t;
    }

    // ── THE BRIDGE METHOD YOU NEVER WROTE ───────────────────────────────
    class StringBox implements Comparable<StringBox> {
        public int compareTo(StringBox other) { return 0; }
        //         ^^^^^^^^^^^^^^^^^^^^^^^^^ after erasure the INTERFACE declares
        //   compareTo(Object), so this signature overrides NOTHING and
        //   polymorphism through a Comparable reference would break.
        //
        //   So javac synthesises this, which is in the class file and not in
        //   your source:
        //
        //       public int compareTo(Object o) {
        //           return compareTo((StringBox) o);      // <- THE CAST LIVES HERE
        //       }
        //
        //   Pass the wrong type through a raw Comparable and the
        //   ClassCastException is thrown inside a method you did not write.
    }

    // ── WHAT SURVIVES, AND THE TRICK THAT EXPLOITS IT ───────────────────
    class Holder { List<String> names; }
    // reflection CAN read this:
    //   Holder.class.getDeclaredField("names").getGenericType()
    //     -> java.util.List<java.lang.String>
    // ...because the class file's SIGNATURE ATTRIBUTE records a FIELD's generic
    // type. It cannot do the same for an OBJECT, which carries nothing.
    //
    // Hence the super type token — an anonymous SUBCLASS, whose generic
    // superclass IS recorded:
    //   new TypeReference<List<String>>() {}
    //   ((ParameterizedType) getClass().getGenericSuperclass())
    //       .getActualTypeArguments()[0]     -> List<String>""",

"""9. THE TRACE — the same program, before and after the compiler

SOURCE:

    class Box<T extends Number> {
        private T value;
        void set(T v)      { this.value = v; }
        T get()            { return value; }
        double doubled()   { return value.doubleValue() * 2; }
    }

    Box<Integer> b = new Box<>();
    b.set(21);
    int x = b.get();

AFTER ERASURE — what the class file effectively contains:

    class Box {
        private Number value;              // T ERASED TO ITS BOUND, not to Object
        void set(Number v)   { this.value = v; }
        Number get()         { return value; }
        double doubled()     { return value.doubleValue() * 2; }
        //                            ^^^^^^^^^^^^^^^ compiles because the erased
        //   field type is Number. With an UNBOUNDED <T> the field would be Object
        //   and this line would not compile — which is what a bound is FOR.
    }

    Box b = new Box();
    b.set(Integer.valueOf(21));            // autoboxing, then a widening reference
    int x = ((Integer) b.get()).intValue();
    //       ^^^^^^^^^ THE COMPILER PUT THIS HERE. Every read of a generic value
    //       carries one, and it is where a violated promise turns into an exception.

THE FAILURE, step by step:

    step                                    what the compiler knows   what the JVM knows
    -------------------------------------------------------------------------------------
    List<String> a = new ArrayList<>();     a holds Strings           a holds Objects
    List raw = a;                           unchecked — warning       identical reference
    raw.add(42);                            nothing (raw type)        add an Object. FINE.
    ...
    String s = a.get(0);                    inserts (String)          CAST FAILS → CCE

    THE TWO COLUMNS DIVERGE AT ROW 2 AND THE PROGRAM CRASHES AT ROW 4. Everything between is correct
    by both sets of rules, which is precisely why the stack trace points somewhere useless.

WHAT ERASURE DOES TO EACH FORM:

    declared                    erased to        why it matters
    ---------------------------------------------------------------------------------
    <T>                         Object           you lose every method but Object's
    <T extends Number>          Number           you keep Number's methods — USE BOUNDS
    <T extends A & B>           A                the LEFTMOST bound wins
    List<String>                List             same class as List<Integer>
    T[]                         Object[]         which is why new T[] is illegal
    void f(List<String>)        void f(List)     which is why the overload clashes

WHICH RULE PRODUCED WHICH ROW:

    "REPLACE T WITH ITS BOUND"        produced `private Number value`, and therefore produced the fact
                                      that `doubled()` compiles at all. An unbounded T would erase to
                                      Object and the method would be rejected.
    "INSERT A CAST AT EVERY READ"     produced `((Integer) b.get())`, and produced the crash site in
                                      the failure table — at a line the programmer did not write.
    "ERASE THE PARAMETER FROM THE
     SIGNATURE"                       produced `void f(List)`, and therefore the "have the same
                                      erasure" compile error for two overloads that look distinct.
    "KEEP THE SIGNATURE ATTRIBUTE"    is why the FIELD's declared type is still recoverable by
                                      reflection even though the OBJECT's is not — the one thing
                                      erasure did not take.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    ERASURE COSTS NOTHING AT RUNTIME — generics are entirely a compile-time construct, so a generic
    method is exactly as fast as the raw equivalent. The costs are all in EXPRESSIVENESS.
    THE ONE PERFORMANCE COST IS INDIRECT: no reified primitives, so a List<Integer> boxes every value.
    An int[] of a million entries is 4MB; a List<Integer> of distinct values is roughly 20MB. That
    ratio is why IntStream and int[] exist alongside Stream<Integer>.

    WHAT ERASURE REMOVES: `new T[]`, `instanceof List<String>`, `catch (T e)`, `static T field`,
    overloads differing only by type argument, and an object's knowledge of its own type argument.
    WHAT IT KEEPS: the Signature attribute — the generic types of FIELDS, METHOD SIGNATURES and CLASS
    DECLARATIONS — which is what makes reflection and super type tokens possible at all.

THE #1 MISTAKE: ignoring an unchecked warning. Each one marks the point where the compiler stopped
being able to help, and where a ClassCastException may later appear somewhere unrelated.

THE #2 MISTAKE: using a raw type in new code. It disables generic checking more broadly than the one
variable, and it exists only for 2004's sake.

THE #3 MISTAKE: expecting the exception where the bug is. A wrong value goes in silently and the crash
happens at a compiler-inserted cast on a later, innocent-looking line.

THE #4 MISTAKE: `new T[10]`. Use a List, or `(T[]) new Object[10]` confined to one private field.

THE #5 MISTAKE: overloading on the type argument. Both erase to the same signature and the compiler
says so literally.

THE #6 MISTAKE: an unbounded `<T>` where a bound was wanted. `<T extends Number>` erases to Number and
keeps its methods; `<T>` erases to Object and keeps nothing.

THE #7 MISTAKE: a static field of type T. There is one static field across all parameterisations, so
it has no coherent meaning. Make the method generic instead.

THE #8 MISTAKE: @SafeVarargs on a method that stores into the array or lets it escape. The annotation
is an assertion, and an untrue one is worse than the warning.

THE #9 MISTAKE: a blanket @SuppressWarnings("unchecked") on a class or method. It hides the NEXT
unchecked operation, which nobody reviewed. Put it on the narrowest declaration possible.

THE #10 MISTAKE: believing invariance is arbitrary. Arrays made the other choice and pay for it with a
type check on every single store, plus a runtime ArrayStoreException. The restriction IS the fix.

ONE-SENTENCE TAKEAWAY: generics are checked at compile time and then ERASED — a type parameter becomes
its leftmost bound and casts are inserted at every read — so List<String> and List<Integer> are the
same class at runtime, which is why you cannot write `new T[]` or `instanceof List<String>` or two
overloads differing only by type argument; the choice was bought deliberately for MIGRATION
COMPATIBILITY when generics arrived nine years late and millions of class files could not be rebuilt;
and the practical consequences are that a violated promise surfaces as a ClassCastException at a cast
you never wrote, sometimes inside a synthetic BRIDGE METHOD, while the Signature attribute keeps just
enough for reflection to read a FIELD's generic type even though an OBJECT can never report its own.""",
]


DEEP["Streams — laziness, one-shot use, and when a loop is better"] = [
"""1. THE GOAL IN PLAIN ENGLISH — describing the work, then doing it once

A stream is not a collection. It holds no data. It is a DESCRIPTION of a pipeline — filter these, map
those, collect the rest — and writing that description does nothing at all. The work only starts when
you ask for a result at the end, and then all the steps happen together, one element at a time.

    THE TWO CONSEQUENCES THAT SURPRISE PEOPLE:

    A PIPELINE WITH NO ENDING DOES NOTHING. `list.stream().map(x -> save(x))` looks like it saves
    everything and saves nothing. There is no terminal operation, so the description was built and
    thrown away. The compiler does not warn.

    THE ELEMENTS DO NOT GO THROUGH STAGE BY STAGE. It is not "filter everything, then map everything".
    Each element is pulled through the WHOLE pipeline before the next one starts. Which is why a
    stream over an infinite source plus `limit(5)` terminates, and why `findFirst` on a million
    elements can touch exactly one.

THE EVERYDAY VERSION: a recipe versus cooking. Writing "chop the onions, fry them, add stock" produces
no dinner. And when you do cook, you do not chop every vegetable in the kitchen before frying anything
— you take one thing through the steps that apply to it.

    A STREAM IS ALSO SINGLE-USE. Once consumed it is spent, like a queue rather than a list. Operating
    on it again throws IllegalStateException, which is the API refusing to pretend it can rewind.

TERMS AS THEY APPEAR:
- INTERMEDIATE operation: returns another stream. Lazy. filter, map, sorted, distinct, limit, peek.
- TERMINAL operation: produces a result or a side effect, and TRIGGERS EVERYTHING. collect, forEach,
  reduce, count, anyMatch, findFirst.
- SHORT-CIRCUITING: a terminal that may finish without consuming the whole source.""",

"""2. THE INTUITION — the pull model, and what laziness buys

The natural mental model is that each stage runs to completion and hands a collection to the next.
That would be a PUSH model, it would allocate an intermediate collection per stage, and it could never
handle an infinite source.

    STREAMS ARE A PULL MODEL INSTEAD. The terminal operation asks for one element; the request travels
    UP the pipeline to the source; the element comes back down through every stage in turn; and only
    then is the next one requested.

    THAT SINGLE DESIGN DECISION BUYS FOUR THINGS AT ONCE:

    NO INTERMEDIATE COLLECTIONS. A filter-map-collect over a million elements allocates one result,
    not three million-element lists. This is called STAGE FUSION, and it is why a long pipeline is not
    proportionally slower than a short one.

    SHORT-CIRCUITING BECOMES POSSIBLE. `findFirst` stops asking after the first match; `anyMatch`
    after the first true; `limit(5)` after five. On a million-element source that can be a million-fold
    saving, and it is impossible in a push model because the earlier stages have already run.

    INFINITE SOURCES BECOME USABLE. `Stream.iterate(1, n -> n * 2).limit(10)` is fine, because nothing
    is produced until something asks.

    AND THE ORDER OF OPERATIONS STARTS TO MATTER. `filter(...).map(expensive)` maps only what survives
    the filter; `map(expensive).filter(...)` maps everything. Identical results, and one may be ten
    times the work — which is a real optimisation you can perform by reading, without measuring.

THE ONE PLACE LAZINESS BREAKS DOWN — and it is the detail worth knowing:

    STATEFUL INTERMEDIATE OPERATIONS. `sorted()` cannot emit its first element until it has seen the
    LAST one, so it is a full barrier: everything upstream runs to completion, is buffered, and only
    then does anything downstream begin. `distinct()` must remember everything seen so far.

    WHICH MEANS `sorted().limit(3)` STILL SORTS EVERYTHING. The limit cannot short-circuit through the
    sort. If you want the three smallest of a million elements, a bounded priority queue is O(n log 3)
    and the sort is O(n log n) — the stream reads better and does far more work.""",

"""3. THE MECHANISM — Spliterator, fusion, and what parallel actually does

UNDERNEATH EVERY STREAM IS A SPLITERATOR, which is an iterator that can also split itself:

    tryAdvance(action)   process one element. The pull.
    trySplit()           hand back a Spliterator covering roughly half, keeping the rest. The parallel.
    estimateSize()       how many are left, for deciding whether splitting is worth it.
    characteristics()    SIZED, ORDERED, DISTINCT, SORTED, IMMUTABLE, NONNULL, CONCURRENT.

    THE CHARACTERISTICS ARE NOT DECORATION — the pipeline reads them and skips work. A stream already
    marked DISTINCT skips `distinct()` entirely. A SIZED stream can pre-allocate the result array. A
    stream that is not ORDERED may let `findFirst` behave like `findAny`.

    AND trySplit IS WHY SOME SOURCES PARALLELISE AND OTHERS DO NOT. An ArrayList or an array splits in
    O(1) into two exact halves, because it knows its size and can index. A LinkedList must WALK to
    find its middle, and a stream from a BufferedReader or an Iterator cannot split meaningfully at
    all — it hands back null and the "parallel" stream runs on one thread with extra overhead.

STAGE FUSION. The intermediate operations are composed into a single chain of Consumers before
anything runs, so `filter(p).map(f).forEach(c)` becomes roughly one nested call per element rather than
three passes over three collections.

PARALLEL STREAMS. `.parallel()` splits the source recursively via trySplit, processes the pieces on the
COMMON ForkJoinPool, and combines the results.

    THREE THINGS ARE WORTH KNOWING AND ARE ROUTINELY MISSED:

    THE POOL IS SHARED BY THE ENTIRE JVM. ForkJoinPool.commonPool() is sized to availableProcessors()
    MINUS ONE, and every parallel stream, every CompletableFuture that omitted an executor, and every
    library doing the same all use it. A blocking operation inside a parallel stream stalls unrelated
    code elsewhere in the process.

    THE COMBINE STEP IS REAL WORK. Splitting is cheap; merging results is not always. Collecting into
    a HashMap in parallel merges maps, which can cost more than the parallelism saved.

    ORDER SURVIVES BUT COSTS. `forEachOrdered` preserves encounter order and serialises the tail of the
    pipeline; `forEach` does not and is faster. `findFirst` must respect order, `findAny` need not —
    which is precisely why both exist.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — NO TERMINAL OPERATION. The pipeline is built and discarded. Nothing runs, nothing warns, and
the symptom is "my forEach isn't executing" from someone who wrote `.map(x -> sideEffect(x))` and
never terminated the chain.

CASE 2 — REUSING A CONSUMED STREAM. IllegalStateException: "stream has already been operated upon or
closed". Assign the SOURCE to a variable, not the stream.

CASE 3 — `sorted().limit(n)` EXPECTING A SHORT-CIRCUIT. Sorting is a full barrier; limit cannot reach
through it. For the top-n of a large source use a bounded priority queue.

CASE 4 — MODIFYING THE SOURCE DURING THE STREAM. Explicitly undefined behaviour, and it usually
manifests as ConcurrentModificationException from the terminal operation — a stack trace pointing at
`collect` rather than at the mutation.

CASE 5 — `Collectors.toMap` ON DUPLICATE KEYS. Throws IllegalStateException rather than overwriting.
Supply a merge function: `toMap(k, v, (a, b) -> b)`. AND toMap THROWS ON A NULL VALUE, where a HashMap
would accept one — a real difference when replacing a loop with a stream.

CASE 6 — `peek()` FOR ANYTHING BUT DEBUGGING. The Javadoc says debugging only, and implementations may
SKIP it when the result is not needed — a `count()` on a SIZED stream may not traverse at all, so the
peek never fires.

CASE 7 — SIDE EFFECTS IN A LAMBDA. `stream.forEach(x -> list.add(x))` is not thread-safe in parallel
and defeats the point in serial. Use a collector.

CASE 8 — PARALLEL ON A SOURCE THAT WILL NOT SPLIT. A LinkedList, an Iterator, a BufferedReader: you
pay the coordination cost and get one thread's throughput.

CASE 9 — PARALLEL WITH A SMALL N. The fork/join overhead dominates below roughly ten thousand elements
of real work, and often far above that.

CASE 10 — `Stream.toList()` vs `collect(Collectors.toList())`. Java 16's `toList()` returns an
UNMODIFIABLE list; the collector traditionally returns an ArrayList. Swapping one for the other turns
a later `.add()` into an UnsupportedOperationException, and it is a genuine migration hazard.

CASE 11 — BOXING. `list.stream().map(x -> x.getCount()).reduce(0, Integer::sum)` boxes every value.
`mapToInt(...).sum()` does not, and the difference is large on a hot path.""",

"""5. THE ALTERNATIVES — and when a loop is simply better

A PLAIN for LOOP. Faster on primitives, debuggable with a breakpoint on any line, and it can `break`,
`continue`, and `return` from the middle. A STREAM CANNOT RETURN FROM THE ENCLOSING METHOD, cannot
carry a checked exception out of a lambda, and produces stack traces full of internal frames.

    USE A LOOP WHEN: the body is imperative, you need early return, you are working on primitives in a
    hot path, or the pipeline would need more than about three stages to express.

AN ENHANCED for OVER A COLLECTION. The same, with less index arithmetic.

`Collection.removeIf(predicate)`. One pass, no iterator management, and on an ArrayList it COMPACTS in
a single pass rather than shifting per removal — so it beats both a stream and a manual loop.

PRIMITIVE STREAMS — IntStream, LongStream, DoubleStream. All the readability with no boxing.
`mapToInt`, `sum`, `average`, `summaryStatistics`. USE THESE WHENEVER THE VALUES ARE PRIMITIVES; the
difference against `Stream<Integer>` is not marginal.

COLLECTORS, which are the part of the API worth learning properly. A Collector is four functions:

    supplier      make a new empty container
    accumulator   fold one element into a container
    combiner      merge two containers  ← ONLY used in parallel, and the usual source of bugs
    finisher      convert the container to the final result

    groupingBy, partitioningBy, joining, counting, summingInt, mapping, teeing (Java 12), and
    groupingBy with a DOWNSTREAM collector, which is where the real expressiveness lives:
    `groupingBy(Person::dept, counting())`.

PARALLEL STREAMS. Worth it only when ALL of: the source splits well, N is large, the per-element work
is CPU-bound and substantial, there is no shared mutable state, and you have measured it. THAT IS FIVE
CONDITIONS, and failing any one usually makes it slower.

WHAT TO SAY: "Streams for readability on collection transformations, primitive streams whenever the
values are primitives, a loop when the body is imperative or needs early exit, and parallel only after
measuring."

""",

"""6. HOW TO USE THEM WELL — numbered steps

STEP 1 — END EVERY PIPELINE WITH A TERMINAL OPERATION. If nothing happened, this is why.

STEP 2 — PUT `filter` BEFORE `map`. Mapping only what survives is free to arrange and can be an
order-of-magnitude difference.

STEP 3 — USE PRIMITIVE STREAMS FOR PRIMITIVES. `mapToInt(...).sum()` rather than
`map(...).reduce(0, Integer::sum)`.

STEP 4 — DO NOT PUT SIDE EFFECTS IN LAMBDAS. Collect a result instead; a stream that mutates external
state is a loop wearing a costume.

STEP 5 — REMEMBER `sorted()` AND `distinct()` ARE BARRIERS. Nothing downstream starts until everything
upstream finishes, so `sorted().limit(3)` sorts the whole source.

STEP 6 — SUPPLY A MERGE FUNCTION TO `toMap`. It throws on duplicate keys, and it throws on null
values, where the equivalent loop with a HashMap would not.

STEP 7 — LEARN `groupingBy` WITH A DOWNSTREAM COLLECTOR. It is where most of the expressiveness is,
and it replaces the most tedious loops you write.

STEP 8 — TREAT `peek` AS DEBUG-ONLY. It may legitimately never run.

STEP 9 — BEFORE `parallel()`, CHECK ALL FIVE CONDITIONS: splittable source, large N, CPU-bound work,
no shared state, and a measurement. And remember the common pool is shared with the whole JVM.

STEP 10 — WHEN A PIPELINE PASSES ABOUT THREE STAGES OR NEEDS A COMMENT TO EXPLAIN IT, WRITE THE LOOP.
Readability was the reason to use a stream; past a point it stops being the readable option.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A stream isn't a collection — it holds no data. It's a DESCRIPTION of a pipeline, and building that
description does nothing. The work only starts when you write a terminal operation at the end.

Which means a pipeline with no terminal operation does NOTHING AT ALL, silently. That usually shows up
as "my forEach isn't running" from someone who wrote map with a side effect and never ended the chain,
and the compiler won't warn you.

The second surprise is that elements don't go through stage by stage. It's not "filter everything then
map everything" — each element is pulled through the WHOLE pipeline before the next one starts. It's a
PULL model: the terminal asks for an element, the request travels up to the source, and the element
comes back down through every stage.

That one decision buys four things. No intermediate collections — a filter-map-collect over a million
elements allocates one result, not three million-element lists. Short-circuiting becomes possible, so
findFirst can touch exactly one element out of a million. Infinite sources become usable, because
nothing is produced until something asks. And the ORDER of your operations starts to matter:
filter-then-map maps only what survives, map-then-filter maps everything. Same result, potentially ten
times the work, and you can fix it by reading rather than measuring.

The place laziness breaks down is STATEFUL operations. `sorted()` can't emit its first element until
it's seen the LAST one, so it's a full barrier — everything upstream runs to completion and is
buffered. Which means `sorted().limit(3)` still sorts everything. If you want the three smallest of a
million, a bounded priority queue is O(n log 3) and the sort is O(n log n) — the stream reads better
and does far more work.

Underneath it all is a SPLITERATOR — an iterator that can also split itself in half. That's what makes
parallel possible, and it's also why some sources parallelise and others don't: an ArrayList or array
splits in constant time into exact halves, while a LinkedList has to walk to find its middle and an
Iterator or a BufferedReader can't split at all. Those hand back null and your "parallel" stream runs
on one thread with extra overhead.

On parallel generally — I'd want five conditions before reaching for it: the source splits well, N is
large, the work is CPU-bound and substantial, there's no shared mutable state, and I've measured it.
And the pool is ForkJoinPool.commonPool, sized to cores minus one and shared by the WHOLE JVM, so
anything blocking inside a parallel stream stalls unrelated code.

Two practical things. Use primitive streams whenever the values are primitives — mapToInt then sum,
rather than map then reduce with Integer::sum, which boxes every value. And Collectors.toMap throws on
duplicate keys AND on null values, where the equivalent loop with a HashMap would happily accept both
— which catches people converting a loop to a stream.

And I'd say plainly: streams are for READABILITY, not speed. On a simple loop over primitives they're
slower. When a pipeline passes about three stages or needs a comment, the loop was the readable
option.'""",

"""8. THE CODE, LINE BY LINE

    // ── NOTHING HAPPENS HERE. No terminal operation. ────────────────────
    Stream.of("a", "b", "c").filter(s -> {
        System.out.println("filtering " + s);
        return true;
    });
    // ^ The pipeline is CONSTRUCTED and discarded. The println never runs, the
    //   compiler does not warn, and the symptom is "my code isn't executing".

    // ── ONE ELEMENT AT A TIME, THROUGH THE WHOLE CHAIN ──────────────────
    List<String> out = Stream.of("a", "b", "c")
        .peek(s  -> System.out.println("filter " + s))
        .map (s  -> { System.out.println("  map " + s); return s.toUpperCase(); })
        .collect(Collectors.toList());
    //   ^^^^^^^ THE TERMINAL. Everything above ran because of this line.
    //
    //   The output INTERLEAVES — filter a, map a, filter b, map b — because the
    //   stages are FUSED into one chain of Consumers and each element is pulled
    //   all the way through before the next is requested. A push model would
    //   print all three filters and then all three maps.

    // ── SHORT-CIRCUITING: one element out of three is touched ───────────
    Stream.of("x", "y", "z")
        .peek(s -> System.out.println("touched " + s))
        .findFirst();
    // ^ prints "touched x" and stops. On a million-element source this is a
    //   million-fold saving, and it is IMPOSSIBLE in a push model because the
    //   earlier stage would already have run to completion.

    // ── ORDER MATTERS, AND IT IS FREE TO FIX ────────────────────────────
    people.stream().filter(p -> p.age() > 60).map(Person::expensiveReport)
    // ^ maps only the survivors.
    people.stream().map(Person::expensiveReport).filter(r -> r.age() > 60)
    // ^ maps EVERYONE. Same result. Potentially ten times the work.

    // ── THE BARRIER. limit cannot reach through sorted. ─────────────────
    million.stream().sorted().limit(3).toList();
    //                ^^^^^^^^ CANNOT emit anything until it has seen the LAST
    //   element, so the entire source is buffered and sorted — O(n log n) —
    //   and only then does limit take three. A bounded PriorityQueue is
    //   O(n log 3). The stream reads better and does far more work.

    // ── PRIMITIVE STREAMS: the boxing difference ────────────────────────
    int total = items.stream().mapToInt(Item::count).sum();
    //                         ^^^^^^^^^ IntStream — no Integer objects at all.
    // int total = items.stream().map(Item::count).reduce(0, Integer::sum);
    //                            ^^^ boxes EVERY value. Same answer, and on a
    //   hot path the difference is not marginal.

    // ── toMap's TWO SURPRISES ───────────────────────────────────────────
    // .collect(Collectors.toMap(Person::name, Person::age))
    //   ^ throws IllegalStateException on a DUPLICATE KEY (a HashMap would
    //     overwrite) AND NullPointerException on a null VALUE (a HashMap would
    //     accept it). Both bite when converting a loop to a stream.
    .collect(Collectors.toMap(Person::name, Person::age, (a, b) -> b));
    //                                                   ^^^^^^^^^^ the merge
    //   function. Supply it unless you genuinely want the exception.""",

"""9. THE TRACE — pull, fuse, short-circuit

THE PIPELINE:

    Stream.of("a", "b", "c")
          .peek(s -> print("filter " + s))
          .map (s -> { print("  map " + s); return s.toUpperCase(); })
          .collect(toList());

WHAT A PUSH MODEL WOULD PRINT — stage by stage, and this is what people expect:

    filter a
    filter b
    filter c
      map a
      map b
      map c

WHAT ACTUALLY PRINTS — element by element, because the stages are FUSED:

    filter a
      map a
    filter b
      map b
    filter c
      map c

    THE DIFFERENCE IS NOT COSMETIC. In the push model, stage one has fully materialised a collection
    before stage two begins — so an intermediate list exists, an infinite source hangs, and
    short-circuiting is impossible because the work is already done.

THE SHORT-CIRCUIT, traced:

    step   what the terminal asks           what the source does        printed
    ---------------------------------------------------------------------------------
    1      findFirst: "give me one"         emits "x"                   touched x
    2      an element arrived → DONE        never asked again           —

    TWO ELEMENTS NEVER TOUCHED. The pull direction is what makes this possible: the terminal controls
    how many requests are made, so it can simply stop asking.

THE BARRIER, traced — `sorted().limit(3)` over a million elements:

    stage         behaviour                                   elements processed
    -------------------------------------------------------------------------------
    source        emits                                       1,000,000
    sorted        BUFFERS EVERYTHING, cannot emit until the    1,000,000 buffered
                  last element has arrived                     + O(n log n) compares
    limit(3)      takes 3 and stops asking                     3
    toList        collects                                     3

    LIMIT SHORT-CIRCUITS AND IT SHORT-CIRCUITS TOO LATE. It stops the stage ABOVE it from being asked
    for a fourth element — and that stage is `sorted`, which has already done all the work. The
    laziness is real and it cannot reach past a stateful operation.

PARALLEL SPLITTING, and why the source decides:

    source            trySplit()                        result
    -------------------------------------------------------------------------------
    ArrayList         O(1), exact halves, SIZED         splits cleanly, scales
    int[]             O(1), exact halves, SIZED         the best case
    HashMap.keySet    splits by table range             reasonable
    LinkedList        must WALK to find the middle      splits poorly
    BufferedReader    returns null                      NO SPLIT — one thread,
                                                        plus fork/join overhead

WHICH DESIGN DECISION PRODUCED WHICH ROW:

    THE PULL MODEL             produced the interleaved output, the short-circuit, and the ability to
                               consume an infinite source. All three are the same fact.
    STAGE FUSION               produced "one result allocated, not three collections" — the reason a
                               five-stage pipeline is not five passes.
    STATEFULNESS OF `sorted`   produced the barrier table. It is a property of the OPERATION, not of
                               streams — `distinct` and `limit`-after-`sorted` behave the same way.
    Spliterator.trySplit       produced the parallel table. Parallelism is a property of the SOURCE
                               first and of your code second.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    A stream adds allocation and a virtual call per element per stage. For a simple loop over
    primitives it is typically SLOWER than a for loop; for multi-stage transformations over objects
    the difference is usually noise. USE THEM FOR CLARITY.
    Stage fusion means an n-stage pipeline is ONE pass, not n passes.
    Short-circuiting terminals can turn O(n) into O(1) on the lucky element.
    `sorted()` is O(n log n) and a FULL BARRIER; `distinct()` is O(n) time and O(n) space.
    Primitive streams remove boxing entirely — the largest single win available in stream code.
    Parallel needs a splittable source, large N, CPU-bound work, no shared state, and a measurement.

THE #1 MISTAKE: no terminal operation. The pipeline is built and discarded, silently, with no warning.

THE #2 MISTAKE: expecting stage-by-stage execution. Elements go through the whole chain one at a time,
which is why short-circuiting and infinite sources work at all.

THE #3 MISTAKE: `sorted().limit(n)` for a top-n. The sort is a barrier and limit cannot reach through
it. Use a bounded priority queue.

THE #4 MISTAKE: `map` before `filter`. Free to fix by reading, and potentially an order of magnitude.

THE #5 MISTAKE: `Stream<Integer>` where `IntStream` belongs. Every value boxed.

THE #6 MISTAKE: `Collectors.toMap` without a merge function. It throws on duplicate keys and on null
values, unlike the HashMap loop it replaced.

THE #7 MISTAKE: side effects in lambdas. Not thread-safe in parallel, and pointless in serial.

THE #8 MISTAKE: `peek` for anything real. Debug-only by specification, and it may never run.

THE #9 MISTAKE: `parallel()` as a performance button. Five conditions must hold, the pool is shared
with the entire JVM, and a blocking call inside one stalls unrelated code.

THE #10 MISTAKE: reusing a consumed stream. Keep a reference to the SOURCE, not to the stream.

THE #11 MISTAKE: assuming `Stream.toList()` and `collect(toList())` are interchangeable. The first is
UNMODIFIABLE since Java 16, and a later `.add()` throws.

ONE-SENTENCE TAKEAWAY: a stream is a lazily-evaluated DESCRIPTION of a pipeline that does nothing until
a terminal operation pulls elements through the whole fused chain ONE AT A TIME — which is what makes
short-circuiting, infinite sources and single-pass execution possible, and what makes `filter` before
`map` a free optimisation — with the laziness breaking down at stateful operations like `sorted()`,
which buffers everything and means `sorted().limit(3)` still sorts a million elements; use primitive
streams for primitives, reach for a loop when the body is imperative or needs an early exit, and treat
`parallel()` as five conditions to verify rather than a button to press.""",
]


DEEP["The JIT — why your first benchmark is always wrong"] = [
"""1. THE GOAL IN PLAIN ENGLISH — code that gets faster while it runs

Java starts by INTERPRETING your program — reading each instruction and doing what it says, one at a
time, which is slow. While it does that it also WATCHES: which methods run often, which branches are
taken, which actual types show up at each call. Once a method looks hot, a compiler translates it to
machine code, using everything that was observed to make choices it could never make ahead of time.

    SO THE SAME METHOD RUNS AT SEVERAL DIFFERENT SPEEDS DURING ONE PROGRAM. The first few hundred calls
    are interpreted. Later calls run compiled but conservatively. Later still they run through an
    aggressive compiler that has a behavioural profile to work from. Speedups of ten to a hundred times
    between the first call and the steady state are ordinary, not exotic.

    WHICH IS WHY YOUR FIRST BENCHMARK IS ALWAYS WRONG. If you time a method the first time it runs,
    you have measured the interpreter. If you time it in a loop with no warm-up, you have measured a
    blend of interpreter, half-optimised and optimised code, weighted by whichever phase happened to
    take longest. Neither number describes the code that will run in production.

THE EVERYDAY VERSION: a new employee reading the manual for every task, while a supervisor takes notes.
After a week the supervisor writes a one-page cheat sheet based on what this person ACTUALLY does —
"you always get the blue form, so here it is pre-filled" — and the job gets much faster. Time them on
day one and you have measured the manual, not the job.

TERMS AS THEY APPEAR:
- JIT: just-in-time compiler. Compiles at RUN time, from observed behaviour.
- AOT: ahead-of-time. Compiles before the program runs, from source alone.
- PROFILE: the counters and type records collected while interpreting.
- SPECULATION: compiling on an assumption the profile supports but cannot prove.
- DEOPTIMISATION: throwing away compiled code when a speculation turns out to be false.
- WARM-UP: running code enough times to reach its steady state before you measure it.""",

"""2. THE INTUITION — why running late beats running early

An ahead-of-time compiler must produce code that is CORRECT FOR EVERY POSSIBLE EXECUTION. It sees a
call through an interface and must emit a dynamic dispatch, because any implementation might arrive.
It sees a branch and must compile both sides. It sees a field read and must actually read it.

    A JIT KNOWS WHAT ACTUALLY HAPPENED. Not what could happen — what did. And in real programs the gap
    between those is enormous:

    THE CALL THAT LOOKS POLYMORPHIC IS USUALLY MONOMORPHIC. A `List` variable in a real application is
    an ArrayList at 99% of call sites, every single time. The JIT observes one type, INLINES that
    implementation directly, and leaves a cheap class check in front of it. AOT cannot do this
    honestly, because the code must survive the case it never sees.

    HALF THE BRANCHES ARE NEVER TAKEN. Null checks that never fire, error paths, feature flags that
    are off. The JIT compiles the taken path densely and replaces the untaken side with a TRAP — an
    instruction that means "if control ever arrives here, abandon this compiled code and fall back to
    the interpreter". Zero cost while the assumption holds.

    INLINING IS THE ENABLER, NOT AN OPTIMISATION. On its own, inlining just removes a call. But once
    the callee's body sits inside the caller, every other optimisation can see across the old boundary:
    constants fold through it, redundant null checks collapse, and the escape analyser can finally
    prove that an object never leaves. MOST OF WHAT THE JIT WINS IS DOWNSTREAM OF INLINING — which is
    why a method too large to inline is a performance cliff, not a gentle slope.

THE PRICE, and it is the honest half of the story:

    COMPILATION COSTS TIME AND IT COSTS IT AT RUN TIME. A JVM spends its first seconds slow, competing
    with your application for CPU while it compiles. Startup is worse than a native binary and always
    will be. A short-lived process — a CLI tool, a lambda invocation — may EXIT before it ever reaches
    the fast code it paid for.

    AND EVERY SPECULATION IS A DEBT. Load a second implementation of that interface and the inlined
    call is invalidated, the compiled method is discarded, execution falls back to the interpreter, and
    the whole thing recompiles more conservatively. Normally invisible. Occasionally the cause of a
    latency spike nobody can explain.""",

"""3. THE MECHANISM — tiers, inlining, escape analysis, and deoptimisation

TIERED COMPILATION, which is the default and explains the shape of every warm-up curve:

    TIER 0   the INTERPRETER. Slow, but it collects the profile.
    TIER 1   C1, no profiling. For trivial methods that will never benefit from more.
    TIER 2   C1, limited profiling. A short-lived stage used when the C2 queue is backed up.
    TIER 3   C1, FULL profiling. Fast-ish code that still counts branches and records types.
             This is where most hot code lives on its way up, and it is deliberately slower than
             tier 1 because it is carrying instrumentation.
    TIER 4   C2. The aggressive optimiser. No profiling — it CONSUMES the profile instead.

    THE USUAL PATH IS 0 → 3 → 4. Roughly a couple of hundred invocations to leave the interpreter and
    on the order of ten thousand to reach C2, though the thresholds are adaptive and depend on how
    busy the compiler queues are. Two runs of the same program can compile at different points.

ON-STACK REPLACEMENT (OSR). A method called ONCE that contains a million-iteration loop would never
reach the invocation threshold. So loop back-edges are counted too, and when the count trips, the JVM
compiles the method and SWAPS THE RUNNING FRAME for the compiled version mid-loop. This is why `main`
with one big loop still gets fast, and why OSR code is often slightly worse than normally-compiled code
— it had to be entered at an awkward point.

INLINING, with the two thresholds that decide it:
    a small method (roughly ≤ 35 bytes of bytecode) is inlined almost anywhere;
    a HOT method gets a much larger budget (roughly ≤ 325 bytes);
    a huge method is never inlined, and everything downstream of that decision is lost.
    -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining tells you which, and why not.

INLINE CACHES — how a virtual call gets inlined at all:
    MONOMORPHIC   one type ever seen → inline it behind a single class-pointer compare. Nearly free.
    BIMORPHIC     two types → inline both behind a two-way check. Still good.
    MEGAMORPHIC   three or more → give up, fall back to a vtable/itable lookup, INLINING IS LOST,
                  and with it every optimisation that depended on it.
    THAT CLIFF IS THE REASON A CALL SITE'S HISTORY MATTERS. The same code is fast in a service that
    only ever passes one implementation and slow in one that passes four.

ESCAPE ANALYSIS. If the JIT can prove an object never leaves the compiled region, it can SCALAR
REPLACE it — the object is never allocated at all, its fields become registers. This is why "avoid
allocation" advice is often obsolete: the allocation may not exist. Inlining is what makes the proof
possible, which is the dependency again.

DEOPTIMISATION. Every speculation is guarded. When a guard fails — a second implementation is loaded,
a never-taken branch is taken, a null finally arrives — the compiled method is marked NOT ENTRANT, the
running frame is rebuilt as an interpreter frame, and execution continues correctly, slowly, until a
new compilation arrives. Correctness is never at risk. Predictable timing is.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — DEAD CODE ELIMINATION EATS THE BENCHMARK. If the result is never used, C2 can prove the whole
computation is unobservable and delete it. The loop becomes nothing. The classic tell is a number that
is PHYSICALLY IMPOSSIBLE — a fraction of a nanosecond per operation, faster than one memory access.

CASE 2 — CONSTANT FOLDING. If the inputs are `static final` or otherwise compile-time constants, the
answer is computed once at compile time and the "loop" returns a literal. You measured a return.

CASE 3 — LOOP HOISTING. A computation that does not depend on the loop variable is moved OUT of the
loop and done once, so a million iterations become one.

CASE 4 — NO WARM-UP AT ALL. The whole measurement is interpreter time. Typically ten to a hundred
times slower than the truth, which is why microbenchmarks so often "prove" the wrong option wins.

CASE 5 — MEASURING DURING THE CLIMB. A loop that runs long enough to trip compilation MID-MEASUREMENT
gives you a weighted average of three different implementations, and the weights depend on the machine.

CASE 6 — PROFILE POLLUTION, the subtlest of all. Running two implementations of the same interface in
ONE JVM makes the shared call site BIMORPHIC or MEGAMORPHIC, so both are measured worse than either
would be alone — and the one measured second may inherit the first one's profile. This is precisely
why JMH forks a fresh JVM per benchmark by default.

CASE 7 — A DEOPTIMISATION STORM. Code compiled on an assumption that keeps breaking recompiles
repeatedly. Symptom: throughput that oscillates rather than settling.

CASE 8 — CLASS LOADING INVALIDATES INLINING LATE. A method inlined because it had exactly one
implementation is discarded the moment a second is loaded — potentially hours in, when a plugin, a
lazily-initialised path, or a proxy first appears.

CASE 9 — SHORT-LIVED PROCESSES NEVER GET THERE. CLI tools, serverless invocations, tests. They pay the
compilation cost and exit before collecting.

CASE 10 — THE CODE CACHE FILLS UP. Compiled code lives in a fixed-size region. When it fills, the JVM
prints a warning and STOPS COMPILING ENTIRELY — the application quietly reverts toward interpreted
speed and stays there.

CASE 11 — TIMING WITH `System.currentTimeMillis()`. It is wall-clock, subject to NTP adjustment, and
its granularity can be milliseconds. Use `System.nanoTime()`, which is monotonic — and even then only
for durations, never as a timestamp.

CASE 12 — ONE MEASUREMENT. GC, the OS scheduler, another tenant on the box, CPU frequency scaling.
A single number carries no information about its own variance.""",

"""5. THE ALTERNATIVES — and what to reach for instead of a hand-rolled timer

JMH (Java Microbenchmark Harness), written by the people who wrote the JIT, and the only honest answer
for anything at method scale. What it does that your loop does not:

    RETURNING THE VALUE, or handing it to a Blackhole, so dead code elimination cannot fire.
    @State OBJECTS the compiler cannot fold to constants.
    @Fork — a FRESH JVM per benchmark, which is the fix for profile pollution.
    @Warmup ITERATIONS run and DISCARDED, so you measure the steady state.
    Many measurement iterations, reported with a confidence interval rather than one number.
    It also warns you when your benchmark looks suspicious.

ASYNC-PROFILER or JFR for anything at APPLICATION scale. A microbenchmark answers "which of these two
methods is faster"; a profiler answers "does this method matter at all", which is almost always the
question you actually had. MOST MICROBENCHMARKS OPTIMISE SOMETHING THAT IS 0.3% OF THE PROFILE.

-XX:+PrintCompilation — a live log of what is being compiled, at which tier, and what is being thrown
away. `%` marks OSR, `s` synchronized, `!` an exception handler, and `made not entrant` is a
deoptimisation. Reading this once teaches more about warm-up than any article.

-XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining — why a method was or was not inlined. "too big",
"hot method too big", "callee is too large". This is the flag for the "why is this slow when the
identical smaller version is fast" question.

-Xint (interpreter only) and -XX:-TieredCompilation (C2 only) — as EXPERIMENTS, to see how much of a
result is compilation.

GraalVM NATIVE IMAGE — AOT compilation to a native binary. Millisecond startup, low memory, no warm-up
— and a LOWER PEAK than a warmed JIT, because it never sees the profile. It also requires a closed
world: reflection and dynamic loading must be declared. THE TRADE IS EXPLICIT: it is the right choice
for short-lived processes and the wrong one for a long-running server.

CLASS DATA SHARING and the JVM's profile-replay options reduce startup without giving up peak.

WHAT TO SAY: "For method-scale questions, JMH — nothing hand-rolled is trustworthy. For real
performance questions, a profiler first, because the method I was about to micro-optimise is usually
not in the top twenty."

""",

"""6. HOW TO BENCHMARK WITHOUT LYING TO YOURSELF — numbered steps

STEP 1 — ASK WHETHER IT MATTERS. Profile the application first. A microbenchmark of a method that is
0.3% of the profile is a correct answer to a question nobody asked.

STEP 2 — USE JMH. Not a loop with nanoTime. Every failure mode in section 4 is one it already handles.

STEP 3 — CONSUME THE RESULT. Return it from the benchmark method or pass it to a Blackhole, or dead
code elimination will delete the thing you are measuring.

STEP 4 — KEEP THE INPUTS OUT OF REACH OF CONSTANT FOLDING. Put them in an @State object; never in a
`static final`.

STEP 5 — WARM UP AND DISCARD. Several seconds of iterations, thrown away, before anything counts.

STEP 6 — FORK A FRESH JVM PER BENCHMARK. This is the profile-pollution fix, and it is the one that
looks unnecessary until it silently reverses a result.

STEP 7 — REPORT VARIANCE, NOT A NUMBER. If the intervals overlap, you have not shown a difference.

STEP 8 — WHEN THE RESULT LOOKS TOO GOOD, DISBELIEVE IT. Under about a nanosecond per operation, assume
the loop was eliminated until you have proved otherwise.

STEP 9 — READ -XX:+PrintCompilation ONCE ON YOUR ACTUAL WORKLOAD. Watch the tiers climb and watch
`made not entrant` scroll past. It makes warm-up concrete in a way no description does.

STEP 10 — IF SOMETHING IS INEXPLICABLY SLOW, CHECK INLINING. -XX:+PrintInlining, and look for "too
big" and for a call site that has gone megamorphic.

STEP 11 — FOR SERVICES, WARM UP IN PRODUCTION TOO. Send synthetic traffic before taking a new instance
into the load balancer, or the first real users pay for your compilation.

STEP 12 — MEASURE ON THE HARDWARE THAT WILL RUN IT. Core count, cache sizes and frequency scaling all
move these numbers.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Java starts by INTERPRETING — reading each instruction and doing what it says. While it does that it's
also watching: which methods run often, which branches get taken, which actual types show up at each
call. Once a method looks hot, it gets compiled to machine code using everything that was observed.

So the same method runs at several different speeds during one program. First few hundred calls,
interpreted. Then compiled but conservatively, with instrumentation still attached. Then compiled
aggressively by C2 with a real behavioural profile. Ten to a hundred times between the first call and
the steady state is ordinary.

Which is why the first benchmark is always wrong. Time it once and you measured the interpreter. Time
it in a loop with no warm-up and you measured a blend of three different implementations, weighted by
whichever phase happened to take longest on that machine. Neither number describes production.

The reason a JIT can beat ahead-of-time compilation at all is that it knows what ACTUALLY happened, not
what could. A List variable is an ArrayList at basically every call site, every time — so the JIT
inlines that implementation directly behind a cheap class check. An AOT compiler can't do that
honestly, because its code has to survive the case it never sees.

And inlining is the ENABLER, not the optimisation. On its own it just removes a call. But once the
callee's body is inside the caller, everything else can see across the old boundary — constants fold
through, null checks collapse, and escape analysis can finally prove an object never leaves, so it's
never allocated at all. Most of what the JIT wins is downstream of inlining, which is why a method too
big to inline is a cliff rather than a slope.

The cost is that every speculation is a debt. If a second implementation of that interface gets loaded,
the inlined call is invalidated — the compiled code is marked not entrant, the running frame is rebuilt
as an interpreter frame, and it recompiles more conservatively. Correctness is never at risk. Predictable
timing is. And that can happen hours in, when some plugin or lazy path first loads a class.

The failure mode I'd watch for most in a hand-rolled benchmark is DEAD CODE ELIMINATION. If nothing
uses the result, C2 proves the computation is unobservable and deletes it. The tell is a number that's
physically impossible — a fraction of a nanosecond per operation, faster than a single memory access.
The subtler one is PROFILE POLLUTION: measuring two implementations of the same interface in one JVM
makes the shared call site megamorphic, so both look worse than either would alone. That's exactly why
JMH forks a fresh JVM per benchmark by default.

So: JMH for anything at method scale, nothing hand-rolled. Consume the result, keep the inputs in a
@State object so they can't fold to constants, warm up and discard, fork per benchmark, and report a
confidence interval rather than a number. And honestly — profile the application first, because the
method I was about to micro-optimise is usually not in the top twenty.'""",

"""8. THE CODE, LINE BY LINE — a benchmark that measures nothing

    // ── THE VERSION EVERYONE WRITES FIRST ───────────────────────────────
    long start = System.currentTimeMillis();
    //           ^^^^^^^^^^^^^^^^^^^^^^^^ WALL CLOCK. Subject to NTP stepping,
    //           and its granularity can be milliseconds. nanoTime is monotonic.
    for (int i = 0; i < 1_000_000; i++) {
        expensiveCalculation(i);
    //  ^ THE RESULT IS DISCARDED. C2 can prove the call has no observable
    //    effect and delete the entire loop. Not "optimise" — DELETE.
    }
    System.out.println(System.currentTimeMillis() - start + " ms");
    // ^ Prints 0. Which is not a fast result; it is the absence of a result.
    //   And even if the loop survived, the first ~10,000 iterations were
    //   INTERPRETED, so the average is mostly warm-up.

    // ── THE THREE WAYS THE COMPILER CAN CHEAT ───────────────────────────
    static final int N = 1000;              // ← CONSTANT FOLDING: the compiler
    int r = 0;                              //   knows N, so the whole sum can be
    for (int i = 0; i < N; i++) r += i;     //   computed at compile time and
    // the loop becomes `r = 499500;`       //   replaced with a literal.

    for (int i = 0; i < n; i++) sum += list.size() * factor;
    //                                ^^^^^^^^^^^^^^^^^^^^ LOOP HOISTING: nothing
    //   here depends on i, so it is computed ONCE and the loop just adds.

    for (int i = 0; i < n; i++) hash(data);
    //                          ^^^^^^^^^^ DEAD CODE ELIMINATION: unused result,
    //   no side effect, no loop.

    // ── THE HONEST VERSION ──────────────────────────────────────────────
    @State(Scope.Benchmark)                 // ← inputs live in an object the
    public static class Input {             //   compiler cannot fold to constants
        int[] data = randomArray(10_000);
    }

    @Benchmark
    @Fork(value = 3)                        // ← THREE FRESH JVMs. This is the
    //                                          profile-pollution fix: measuring
    //                                          two impls in ONE JVM makes the
    //                                          shared call site megamorphic and
    //                                          slows BOTH.
    @Warmup(iterations = 5, time = 1)       // ← run and DISCARD. You are waiting
    //                                          for tier 4, not measuring tier 0.
    @Measurement(iterations = 10, time = 1)
    public int sum(Input in) {
        int s = 0;
        for (int v : in.data) s += v;
        return s;
    //  ^^^^^^^^ RETURNING IT is what stops dead code elimination. JMH consumes
    //  the return value; for multiple results, Blackhole.consume(x).
    }

    // ── THE FLAGS THAT SHOW YOU WHAT HAPPENED ───────────────────────────
    // -XX:+PrintCompilation
    //     3    java.lang.String::hashCode (55 bytes)      ← tier 3, C1+profiling
    //     4 %  Main::sum @ 12 (43 bytes)                  ← % means OSR
    //     3    Main::sum   made not entrant               ← A DEOPTIMISATION.
    // -XX:+UnlockDiagnosticVMOptions -XX:+PrintInlining
    //     @ 7  Main::helper (312 bytes)  hot method too big  ← the cliff, named.""",

"""9. THE TRACE — one method, four speeds

THE SAME METHOD, timed at four points in one JVM's life. Numbers are ILLUSTRATIVE SHAPES, not measured
constants — the ratios are what matters, and they are the ratios people actually observe:

    invocation      what is executing                              relative time
    ---------------------------------------------------------------------------------
    1               tier 0, INTERPRETER. Every bytecode dispatched  ~100x
                    through a switch. The profile starts filling.
    ~500            tier 3, C1 WITH FULL PROFILING. Real machine    ~8x
                    code, but carrying counters — deliberately
                    slower than tier 1, because it is paying to
                    learn.
    ~12,000         tier 4, C2. Profile consumed. The hot path      ~1x
                    inlined, the untaken branches replaced by
                    traps, the escaping-nowhere object never
                    allocated at all.
    later           a second implementation is loaded → the guard   ~100x briefly,
                    fails → MADE NOT ENTRANT → back to the           then ~1.4x
                    interpreter → recompile, this time with a
                    bimorphic call and no scalar replacement.

    THE LAST ROW IS THE ONE THAT SURPRISES PEOPLE. Nothing was wrong, nothing was misconfigured, and no
    code changed. A class was loaded, an assumption became false, and the JVM did the only correct
    thing — which cost a latency spike and a permanently slightly-slower steady state.

WHY EACH DROP HAPPENED — mapping the row to the mechanism:

    100x → 8x       LEAVING THE INTERPRETER. Bytecode dispatch removed. This is the largest single
                    step and it is why an unwarmed measurement is not off by a bit, it is off by
                    two orders of magnitude.
    8x → 1x         INLINING, and everything downstream of it: constant folding across the old call
                    boundary, dead branch removal via uncommon traps, and scalar replacement removing
                    the allocation entirely.
    1x → 1.4x       THE CALL SITE WENT BIMORPHIC. Inlining survived but with a two-way guard, and
                    escape analysis could no longer prove the object was confined.

NOW THE NAIVE BENCHMARK, traced against that table:

    what you wrote                          what you measured
    ---------------------------------------------------------------------------------
    time one call                           the interpreter. ~100x too slow.
    loop 1,000 times, no warm-up            mostly interpreter, some tier 3. ~30x too slow.
    loop 1,000,000, no warm-up              a weighted average that DEPENDS ON THE MACHINE,
                                            because the thresholds are adaptive.
    result unused                           0 ms. The loop does not exist.
    inputs are `static final`               0 ms. The answer is a literal in the class file.
    two impls, one JVM, no fork             both slower than either alone, and possibly REVERSED
                                            in ranking. This is the one that survives review.

    THE SHAPE OF THE WHOLE THING: every single row above is a case of the measurement disturbing what
    it measures. The JIT optimises for what it observes, and a benchmark is a strange, unrepresentative
    thing to observe. JMH's entire design is a list of defences against exactly this table.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Interpreted → C2 steady state is commonly 10–100x. This is the number that makes unwarmed
    measurements worthless rather than merely imprecise.
    Roughly a couple of hundred invocations to leave the interpreter; on the order of ten thousand to
    reach C2 — ADAPTIVE, so two runs of the same program compile at different points.
    Inlining budget: about 35 bytes of bytecode cold, about 325 hot. Past that, a cliff.
    Inline caches: 1 type is nearly free, 2 is fine, 3+ loses inlining and everything downstream.
    Deoptimisation is correct, cheap in aggregate, and occasionally the unexplained latency spike.
    Compilation competes with your application for CPU during startup — this is real, and it is why a
    native image starts in milliseconds and a JVM does not.

THE #1 MISTAKE: no warm-up. You measured the interpreter, and it is not close.

THE #2 MISTAKE: discarding the result. Dead code elimination deletes the loop; the tell is a time that
is physically impossible.

THE #3 MISTAKE: `static final` inputs. Constant-folded to a literal at compile time.

THE #4 MISTAKE: measuring two implementations in one JVM. Profile pollution can slow both and REVERSE
the ranking. Fork per benchmark.

THE #5 MISTAKE: `System.currentTimeMillis()`. Wall clock, NTP-adjustable, coarse. Use `nanoTime`, and
only for durations.

THE #6 MISTAKE: one measurement, no variance. Overlapping intervals are not a result.

THE #7 MISTAKE: microbenchmarking before profiling. The method usually is not in the top twenty.

THE #8 MISTAKE: believing a suspiciously good number. Under a nanosecond per operation, assume the work
was eliminated.

THE #9 MISTAKE: expecting a short-lived process to reach peak. CLI tools and serverless invocations pay
for compilation and exit before collecting; that is a native-image case, not a tuning case.

THE #10 MISTAKE: forgetting the code cache can fill. When it does, the JVM stops compiling and quietly
drifts back toward interpreted speed — with a warning nobody reads.

THE #11 MISTAKE: assuming allocation costs what it used to. Escape analysis may have removed the object
entirely — but only if the enclosing method was inlined, which is why the advice is conditional.

ONE-SENTENCE TAKEAWAY: the JVM interprets first while PROFILING, then compiles hot code using what it
actually observed — inlining monomorphic calls, replacing never-taken branches with traps, and removing
allocations it can prove never escape — so the same method runs 10–100x apart between its first call
and its steady state, every one of those optimisations is a SPECULATION that can be deoptimised when a
class loads or a branch finally fires, and consequently any benchmark without warm-up, without
consuming its result, without non-constant inputs, and without a forked JVM is measuring the harness
rather than the code.""",
]


DEEP["Garbage collection — the generational hypothesis, and which collector to pick"] = [
"""1. THE GOAL IN PLAIN ENGLISH — why nobody frees memory in Java

In C you ask for memory and you give it back. Forget to give it back and the program grows until it
dies; give it back twice, or use it after giving it back, and the program corrupts itself in a way that
shows up somewhere else entirely, hours later. Those two bug classes have caused an enormous share of
the security vulnerabilities of the last forty years.

    JAVA REMOVES THE QUESTION. You never free anything. Periodically the JVM works out which objects
    are still REACHABLE — meaning there is some chain of references from a running thread, a static
    field, or a local variable to that object — and everything else is, by definition, garbage that no
    code could ever look at again.

    THE KEY WORD IS REACHABLE, NOT USED. The collector cannot tell whether you are FINISHED with an
    object. It can only tell whether you can still GET to it. Which is why Java still has memory leaks:
    a cache, a static list or a listener registry that holds a reference forever keeps the object alive
    forever, and the collector is doing exactly its job while your heap fills.

THE EVERYDAY VERSION: a library that never asks you to return books, but every night walks the building
and removes any book that nobody has a note pointing to. If you leave a note in a drawer you forgot
about, the book stays. That is a Java memory leak, and no amount of tuning fixes it.

    THE SECOND SURPRISE IS THAT COLLECTION IS CHEAP IN PROPORTION TO WHAT SURVIVES, NOT TO WHAT DIED.
    A young-generation collection copies the survivors elsewhere and then declares the entire region
    empty in one step. Ten thousand dead objects cost NOTHING. This inverts the usual instinct:
    creating short-lived garbage is close to free, and it is long-lived objects that are expensive.

TERMS AS THEY APPEAR:
- HEAP: where objects live. STACK: where local variables and frames live, per thread.
- ROOT: a starting point for reachability — a thread's stack, a static field, a JNI reference.
- STOP THE WORLD (STW): a pause where application threads are frozen so the collector can work.
- MINOR / YOUNG GC: collects the young generation only. Frequent, short.
- FULL GC: collects everything, usually with a long pause. Something has gone wrong if these are
  frequent.""",

"""2. THE INTUITION — the weak generational hypothesis, and what it buys

One observation drives almost every collector ever shipped:

    THE WEAK GENERATIONAL HYPOTHESIS: MOST OBJECTS DIE YOUNG.

    It is not a theory, it is a measurement, and it holds across wildly different programs. The string
    you built to log a line, the iterator, the boxed Integer, the intermediate list — the overwhelming
    majority of allocations are dead within milliseconds. A smaller set — caches, connection pools,
    the object graph of a long-lived session — lives essentially forever. VERY LITTLE LIVES A MEDIUM
    AMOUNT OF TIME.

IF THAT IS TRUE, TWO DESIGN DECISIONS FOLLOW IMMEDIATELY:

    SEPARATE THE YOUNG FROM THE OLD, and collect the young region far more often. You spend your effort
    where the garbage is, and you almost never touch the region where nothing is dying.

    COLLECT THE YOUNG REGION BY COPYING, NOT BY SWEEPING. Walk the roots, copy every live object out to
    another space, then mark the whole original region free in a single operation. THE COST IS
    PROPORTIONAL TO THE SURVIVORS. If 98% of the region is dead — which the hypothesis says it will be
    — you did 2% of the work of examining it object by object.

    AND COPYING COMPACTS FOR FREE. Because survivors are copied out one after another, the space left
    behind has no holes. Which means ALLOCATION becomes a pointer bump: to allocate, add the object's
    size to a pointer. That is a handful of instructions, and it is why "object allocation is slow in
    Java" has been wrong for about twenty years.

THE MECHANISM THAT MAKES THE POINTER BUMP THREAD-SAFE WITHOUT A LOCK is worth naming: each thread gets
its own THREAD-LOCAL ALLOCATION BUFFER (TLAB), a private slice of Eden. Allocating inside your own TLAB
needs no synchronisation at all. Only refilling it does.

THE PRICE OF THE SPLIT, and it is the part that is easy to forget: if the collector only walks the
young region, it must still find references INTO the young region FROM the old one. It cannot scan the
whole old generation — that would defeat the purpose. So the JVM tracks those references as they are
created, using a WRITE BARRIER on every reference store into an old object, recording the location in a
CARD TABLE. Every reference assignment in your program pays a tiny tax so that young collections can
stay short. THAT TRADE — a small constant cost everywhere to buy a large saving at collection time — is
the shape of nearly every choice in this area.""",

"""3. THE MECHANISM — Eden, survivors, promotion, and what each collector does differently

THE CLASSIC LAYOUT:

    ┌───────────────── YOUNG ─────────────────┐  ┌──────── OLD (Tenured) ────────┐
    │   Eden (large)   │  S0  │  S1  │           │    long-lived objects         │
    └──────────────────┴──────┴──────┘           └───────────────────────────────┘

    ALLOCATION goes into Eden, by pointer bump inside a TLAB.
    WHEN EDEN FILLS → a MINOR GC. Live objects in Eden and in the occupied survivor space are copied
    into the OTHER survivor space; Eden and the vacated survivor are then wholesale empty.
    EACH SURVIVAL INCREMENTS AN AGE COUNTER in the object header. Past the TENURING THRESHOLD the
    object is PROMOTED to the old generation instead.
    THE OLD GENERATION is collected rarely and expensively.

    NOTE WHAT THIS IMPLIES: AN OBJECT'S ADDRESS CHANGES. Repeatedly. Which is why Java has no
    meaningful pointer arithmetic, why `identityHashCode` has to be stored once computed, and why a
    native library holding a raw address must pin the object.

THE COLLECTORS, and the ONE trade-off that distinguishes them — you may have low pause time, high
throughput, or small footprint, and no collector gives all three:

    SERIAL       one thread, stop-the-world. Small heaps, containers with one CPU. Genuinely the
                 fastest choice below a few hundred MB, because it has no coordination cost.
    PARALLEL     multiple threads, still fully stop-the-world. THE HIGHEST THROUGHPUT of any collector.
                 Correct for batch jobs where a two-second pause costs nothing.
    G1           the default since Java 9. Splits the heap into REGIONS (1–32 MB) rather than
                 contiguous generations, and each region is designated Eden, Survivor or Old
                 DYNAMICALLY. Marks concurrently, then evacuates the regions with the most garbage
                 first — "garbage first" — so it can aim at a PAUSE TARGET (default 200 ms) by simply
                 collecting fewer regions per cycle.
    ZGC          concurrent almost everywhere, sub-millisecond pauses that are INDEPENDENT OF HEAP
                 SIZE — the same pause at 4 GB and 4 TB. Uses coloured pointers and LOAD BARRIERS: the
                 barrier fixes up a reference as it is read, so objects can be relocated while the
                 application runs. Generational since Java 21. Costs some throughput and footprint.
    SHENANDOAH   the same goal by a different route, concurrent evacuation with a forwarding pointer.

TWO G1 DETAILS THAT CAUSE REAL INCIDENTS:

    HUMONGOUS OBJECTS — anything larger than half a region is allocated directly into contiguous Old
    regions and is handled poorly. A steady stream of large arrays can fragment the heap and trigger
    full GCs on a heap that looks nowhere near full.
    EVACUATION FAILURE — if there is no free region to copy survivors into, G1 falls back to a FULL,
    single-threaded, compacting collection. That is the multi-second pause in the log.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — THE STATIC COLLECTION THAT ONLY GROWS. A `static Map` used as a cache with no eviction. Every
entry is reachable, so nothing is collectable, and the leak is in your code, not the collector.

CASE 2 — THE UNREGISTERED LISTENER. An object registers a callback and is never removed. The registry
holds it, so it and everything it references live forever. THE MOST COMMON LEAK IN LONG-RUNNING JAVA
APPLICATIONS.

CASE 3 — THE INNER CLASS THAT OUTLIVES ITS OUTER. A non-static inner class holds an implicit reference
to the enclosing instance. Hand one to a long-lived executor and the enclosing object cannot die.

CASE 4 — ThreadLocal IN A POOLED THREAD. The thread is never destroyed, so the value is never cleared.
Classic in servlet containers. Always `remove()` in a finally.

CASE 5 — PROMOTION OF THINGS THAT SHOULD HAVE DIED. If the survivor spaces are too small, objects are
promoted to the old generation prematurely, the old generation fills, and full GCs begin. THE SYMPTOM
IS OLD-GEN GROWTH IN AN APPLICATION THAT ALLOCATES NOTHING LONG-LIVED.

CASE 6 — ALLOCATION RATE AS THE REAL DIAL. If the application allocates faster than the collector can
keep up, no tuning flag saves it. GC time is a symptom; allocation rate is usually the cause.

CASE 7 — HUMONGOUS ALLOCATION UNDER G1. Large arrays fragment the region layout and force full GCs.

CASE 8 — CALLING `System.gc()`. A hint, not a command. Under some collectors it forces a full
stop-the-world collection you did not want. Production code should essentially never call it, and
`-XX:+DisableExplicitGC` exists because libraries do.

CASE 9 — FINALIZERS. Deprecated, and rightly: they run on an unspecified thread at an unspecified time,
can resurrect the object, and DELAY collection by at least one extra cycle. Use try-with-resources for
resources and `Cleaner` if you truly need a native-memory hook.

CASE 10 — HEAP TOO LARGE. Above about 32 GB the JVM can no longer use COMPRESSED ORDINARY OBJECT
POINTERS (4-byte references instead of 8), so every reference doubles in size and effective capacity
can go DOWN as you raise -Xmx. A 31 GB heap can hold more objects than a 33 GB one.

CASE 11 — CONTAINER MEMORY LIMITS. A JVM that does not see the cgroup limit sizes its heap from the
HOST's memory and is killed by the OOM killer with no Java-level error at all. Modern JVMs are
container-aware; older ones need -XX:MaxRAMPercentage.

CASE 12 — MEASURING GC BY PAUSE COUNT. What matters is the percentage of wall time spent paused and
the tail of the pause distribution, not how many collections happened.""",

"""5. THE ALTERNATIVES — how to choose, and what to reach for instead of a flag

CHOOSING A COLLECTOR is mostly one question: WHAT DOES A PAUSE COST YOU?

    A BATCH JOB, A BUILD, AN ETL PIPELINE. Nothing is waiting. Use PARALLEL — it has the highest
    throughput of anything available, precisely because it does not do concurrent work.
    A WEB SERVICE WITH ORDINARY LATENCY GOALS. G1, the default. Set a pause target and leave it.
    A LATENCY-CRITICAL SERVICE, OR A VERY LARGE HEAP. ZGC or Shenandoah. Pauses stay sub-millisecond
    at any heap size, and you pay in throughput and footprint.
    A SMALL CONTAINER, ONE OR TWO CPUS. SERIAL. Concurrent collectors need spare cores; without them
    they steal from the application.
    A PROCESS THAT EXITS BEFORE IT COLLECTS. EPSILON — a no-op collector. Genuinely useful for
    short-lived tools and for proving how much memory a benchmark really allocates.

BEFORE TUNING ANYTHING, REDUCE ALLOCATION. It is usually the larger win and it is always the more
durable one:
    primitive collections or arrays instead of `List<Integer>`;
    `StringBuilder` rather than concatenation in a loop;
    `mapToInt` rather than `Stream<Integer>`;
    reusing buffers on genuinely hot paths.
    AND MEASURE FIRST — escape analysis may already have removed the allocation you are worried about.

REFERENCE TYPES, for the cases where you want the collector to help you:
    SOFT       cleared only when memory is tight. A memory-sensitive cache — though in practice a
               bounded LRU cache is easier to reason about and behaves better.
    WEAK       cleared as soon as nothing strong points at it. This is what WeakHashMap uses, and it
               is the right tool for keying metadata by an object you do not own.
    PHANTOM    for cleanup after collection, via a reference queue. What `Cleaner` is built on.

OFF-HEAP AND ALTERNATIVES:
    ByteBuffer.allocateDirect and the Java 21+ Foreign Function & Memory API move data outside the
    heap, so the collector never walks it. Right for very large caches and for I/O buffers; wrong
    almost everywhere else, because you have reintroduced manual lifetime management.

WHAT TO LOOK AT INSTEAD OF GUESSING:
    -Xlog:gc* (Java 9+) for the log. A heap dump plus Eclipse MAT for a leak — its dominator tree
    answers "what is keeping this alive", which is the only question that matters. JFR for allocation
    profiling by call site.

WHAT TO SAY: "Default to G1, use Parallel for batch and ZGC for latency-critical or very large heaps.
But almost every GC problem I have actually seen was an allocation-rate problem or a retention bug, and
neither is fixed with a flag."

""",

"""6. HOW TO DIAGNOSE A GC PROBLEM — numbered steps

STEP 1 — ESTABLISH WHICH PROBLEM YOU HAVE. Long pauses, or growth? They have almost nothing in common.
Pauses are a tuning and collector question; growth is a retention bug in your code.

STEP 2 — TURN ON THE LOG. `-Xlog:gc*:file=gc.log:time,uptime,level,tags`. It costs almost nothing and
you cannot reason without it.

STEP 3 — READ THE PERCENTAGE, NOT THE COUNT. Time paused as a fraction of wall time, plus the p99 pause.
Thousands of 1 ms pauses are healthy; three 4-second pauses are not.

STEP 4 — CHECK WHETHER THE OLD GENERATION IS GROWING ACROSS FULL GCs. Old-gen occupancy that is higher
after every full collection than after the last one is a LEAK, and no flag will help.

STEP 5 — FOR A LEAK, TAKE A HEAP DUMP AND OPEN THE DOMINATOR TREE. `jcmd <pid> GC.heap_dump`. Ask what
is retaining the largest object, not what is largest.

STEP 6 — FOR PAUSES, LOOK AT THE ALLOCATION RATE FIRST. MB/s promoted and MB/s allocated. High
allocation is fixed in code and only mitigated by flags.

STEP 7 — CHECK FOR PREMATURE PROMOTION. Objects reaching the old generation at a low age means the
young generation or survivor spaces are too small for the workload.

STEP 8 — LOOK FOR FULL GCs AND NAME THE CAUSE. Evacuation failure, humongous allocation, metaspace, or
an explicit `System.gc()`. Each has a different fix.

STEP 9 — SET -Xms EQUAL TO -Xmx for a server. Heap resizing causes full collections, and a server will
reach its maximum anyway.

STEP 10 — CHANGE ONE FLAG AT A TIME AND MEASURE. GC tuning is where cargo-culted flag lists go to
accumulate; most inherited flag sets contain options that are obsolete, contradictory, or no longer
exist.

STEP 11 — IN A CONTAINER, VERIFY THE JVM SEES THE LIMIT. `-XX:MaxRAMPercentage` and check the resolved
heap size, or the OOM killer will end the process with no Java-level error.

STEP 12 — BEFORE ANY OF THIS, CONSIDER ALLOCATING LESS. It is the fix that keeps working after the
next JVM upgrade changes all the defaults.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The collector works out which objects are still REACHABLE — meaning there's a chain of references from
a running thread, a static field or a local variable — and everything else is garbage by definition,
because no code could ever look at it again.

The key word is reachable, not used. The collector can't tell whether you're FINISHED with an object,
only whether you can still get to it. That's why Java still has memory leaks: a static cache, a
listener registry, a ThreadLocal in a pooled thread. The collector is doing its job exactly right while
the heap fills.

The design is built on one measurement, the weak generational hypothesis: most objects die young. It's
not a theory, it holds across wildly different programs. So you split the heap, collect the young part
constantly, and collect the young part BY COPYING — walk the roots, copy the survivors out, then mark
the whole region free in one step. The cost is proportional to what SURVIVED, not to what died. If 98%
of the region is garbage you did 2% of the work.

That inverts the usual instinct. Creating short-lived garbage is nearly free. And because copying
leaves no holes, allocation becomes a pointer bump — a handful of instructions in a thread-local buffer
with no synchronisation at all. "Allocation is slow in Java" has been wrong for about twenty years.

The price is that if you only collect the young region, you still have to find references INTO it from
the old one — and you can't scan the old generation, that would defeat the point. So there's a write
barrier on every reference store into an old object, recording it in a card table. Your program pays a
tiny tax on every reference assignment to keep young collections short. That trade — a small cost
everywhere to buy a big saving at collection — is the shape of nearly every decision in this area.

On collectors: there's one trade-off, and you get two of three. Throughput, pause time, footprint.
Parallel is the highest throughput and fully stop-the-world, so it's right for batch. G1 is the default
— region-based, marks concurrently, evacuates the regions with the most garbage first, which is how it
can aim at a pause target: collect fewer regions. ZGC gives sub-millisecond pauses INDEPENDENT of heap
size, same pause at 4 GB and 4 TB, using load barriers that fix up references as they're read so
objects can move while the application runs. Costs throughput. And Serial genuinely wins on a
one-CPU container, because concurrent collectors need spare cores to be concurrent in.

But honestly — almost every GC problem I've actually seen was either an allocation-rate problem or a
retention bug, and neither is fixed with a flag. So I'd separate the two questions first: long pauses,
or growth? If old-gen occupancy is higher after every full GC than after the last one, that's a leak,
take a heap dump and read the dominator tree. If it's pauses, look at allocation rate before touching
any option.'""",

"""8. THE CODE, LINE BY LINE — a leak, and why it is not the collector's fault

    // ── THE LEAK EVERY LONG-RUNNING SERVICE HAS HAD ─────────────────────
    public class EventBus {
        private static final List<Listener> LISTENERS = new ArrayList<>();
        //                   ^^^^^^ STATIC. A GC ROOT. Everything in this list is
        //                   reachable from a root forever, by definition.

        public static void register(Listener l) { LISTENERS.add(l); }
        // ^ and no unregister. Every listener ever added lives until the JVM exits,
        //   ALONG WITH EVERYTHING IT REFERENCES — which for an inner class is the
        //   entire enclosing object graph.
    }

    class Session {                          // 50 MB of cached user state
        void start() {
            EventBus.register(e -> handle(e));
    //                        ^^^^^^^^^^^^^ this lambda captures `this`, because
    //      handle() is an instance method. The Session — and its 50 MB — is now
    //      reachable from a static field. Ten thousand sessions later, OutOfMemory.
        }
    }
    // THE COLLECTOR IS CORRECT AT EVERY STEP. Reachable is not the same as needed.

    // ── THE OTHER CLASSIC: ThreadLocal IN A POOLED THREAD ───────────────
    static final ThreadLocal<Context> CTX = new ThreadLocal<>();
    void handleRequest(Request r) {
        CTX.set(new Context(r));             // ← the POOL thread never dies, so
        process();                           //   this value is never cleared, and
    }                                        //   it holds the request alive.
    // FIX: try { ... } finally { CTX.remove(); }

    // ── WHY ALLOCATION IS NOT THE THING TO WORRY ABOUT ──────────────────
    for (int i = 0; i < 1_000_000; i++) {
        String s = "row " + i;                // a million short-lived objects
        process(s);
    }
    // ^ These die in Eden. A minor GC copies only the SURVIVORS — near zero — and
    //   declares the whole region empty. The million dead objects cost NOTHING.
    //   Each allocation was a pointer bump inside this thread's own TLAB: no lock,
    //   no free list, a handful of instructions. And escape analysis may have
    //   removed some of them entirely.

    // ── THE ALLOCATION THAT ACTUALLY HURTS ──────────────────────────────
    cache.put(key, new byte[8 * 1024 * 1024]);
    //             ^^^^^^^^^^^^^^^^^^^^^^^^^ larger than half a G1 region, so it is
    //   a HUMONGOUS object: allocated straight into contiguous Old regions, never
    //   young-collected, and a steady stream of them fragments the heap into full
    //   GCs while the heap looks far from full.

    // ── WHAT TO RUN, NOT WHAT TO GUESS ──────────────────────────────────
    // -Xlog:gc*:file=gc.log:time,uptime,level,tags   the log
    // jcmd <pid> GC.heap_info                        live occupancy
    // jcmd <pid> GC.heap_dump /tmp/h.hprof           then MAT's dominator tree
    // System.gc();  ← a HINT, and under some collectors a full STW pause you did
    //                 not ask for. Production code should never call it.""",

"""9. THE TRACE — one minor GC, and the cost that is not where you expect

STARTING STATE. Eden 512 MB, survivors 64 MB each, old 2 GB. The application has just allocated a
million short-lived strings and holds onto three of them.

    step  what happens                                          cost
    -----------------------------------------------------------------------------------
    1     Eden fills. An allocation cannot bump the pointer.      —
    2     Threads roll forward to a SAFEPOINT and stop.           the pause begins here,
          Not instantly — a thread in a long counted loop can     and "time to safepoint"
          take a while to reach one.                              is its own metric
    3     Roots are scanned: every thread stack, every static
          field, JNI references.                                  proportional to ROOTS
    4     The CARD TABLE is consulted for old→young references.   proportional to DIRTY
          This is why the write barrier existed.                  CARDS, not to old size
    5     Live objects are COPIED to the empty survivor space,
          ages incremented, anything past the tenuring
          threshold promoted to Old.                              PROPORTIONAL TO SURVIVORS
    6     Eden and the old survivor space are declared empty
          wholesale. No per-object work.                          O(1)
    7     Threads resume.                                         pause ends

    THE MILLION DEAD OBJECTS APPEAR NOWHERE IN THIS TABLE. That is the whole point. Step 5 touched
    three objects. Step 6 reclaimed 512 MB in a single operation.

NOW THE SAME TRACE WITH A CACHE THAT RETAINS 400 MB OF WHAT WAS ALLOCATED:

    step 5     400 MB must be COPIED, then promoted           the pause grows by orders
    step 6     unchanged                                      of magnitude
    old gen    grows by 400 MB every cycle                    → old fills → FULL GC

    SAME ALLOCATION RATE. SAME COLLECTOR. SAME FLAGS. The difference is entirely SURVIVAL RATE, which
    is a property of your code. This is the single most useful thing to know about GC: you tune the
    collector, but you control the survival rate, and the survival rate is what the cost is
    proportional to.

READING THE LOG — what each line is telling you:

    [gc] Pause Young (Normal) 512M->8M(2G) 4.2ms
          ^ healthy. 512 MB in, 8 MB survived, 4 ms. Survival rate 1.5%.

    [gc] Pause Young (Normal) 512M->480M(2G) 210ms
          ^ 94% SURVIVED. Either a leak, or the young generation is too small for the
            workload so objects that would have died are being caught mid-life.

    [gc] Pause Full (G1 Evacuation Pause) 1.9G->1.8G(2G) 3400ms
          ^ THE INCIDENT. A full, compacting collection that freed almost nothing.
            G1 had no free region to evacuate into. The next one will be worse.

    [gc] Pause Young (Concurrent Start) (G1 Humongous Allocation)
          ^ an object larger than half a region. A steady stream of these fragments
            the heap, and the heap will not look full when it fails.

    THE DIAGNOSTIC RULE THAT COVERS MOST CASES: compare the number AFTER the arrow across successive
    FULL collections. If it climbs every time, you have a retention bug and no flag will help. If it
    returns to the same floor, the heap is behaving and the question is pauses, not growth.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Allocation is a pointer bump in a thread-local buffer — a handful of instructions, no lock.
    A young collection costs O(survivors), NOT O(allocated). Dead objects are free.
    A full collection costs O(live heap) and is the pause that shows up in incident reviews.
    The write barrier taxes every reference store into an old object; that is what buys short young
    pauses.
    G1 pause target: default 200 ms, achieved by collecting FEWER REGIONS, not by working faster.
    ZGC pauses are sub-millisecond and INDEPENDENT of heap size — 4 GB and 4 TB alike.
    Above ~32 GB compressed oops are lost and every reference doubles in size.

THE #1 MISTAKE: believing Java cannot leak. Reachable is not the same as needed, and unbounded caches,
listener registries and ThreadLocals in pooled threads leak exactly as reliably as `malloc` without
`free`.

THE #2 MISTAKE: tuning flags for a retention bug. If old-gen occupancy after each full GC keeps
climbing, no option helps. Take a heap dump.

THE #3 MISTAKE: optimising away short-lived allocation. It is nearly free, and escape analysis may have
removed it already. Optimise SURVIVAL, not allocation.

THE #4 MISTAKE: calling `System.gc()`. A hint that can become a full stop-the-world pause you did not
want.

THE #5 MISTAKE: raising -Xmx past 32 GB without realising compressed oops are lost, so effective
capacity can fall as the number rises.

THE #6 MISTAKE: using a concurrent collector on one or two cores. It needs spare CPU to be concurrent
in; without it, it steals from the application. Serial is genuinely correct there.

THE #7 MISTAKE: judging GC health by collection count. Percentage of wall time paused and the p99
pause are the numbers.

THE #8 MISTAKE: relying on finalizers. Unspecified thread, unspecified time, and they DELAY collection
by an extra cycle. try-with-resources, or `Cleaner`.

THE #9 MISTAKE: leaving -Xms below -Xmx on a server. Heap growth triggers full collections on the way
to a maximum the server will reach anyway.

THE #10 MISTAKE: ignoring humongous allocations under G1. Large arrays fragment the region layout and
force full GCs on a heap that looks half empty.

THE #11 MISTAKE: copying an inherited flag list. Most contain options that are obsolete, mutually
contradictory, or removed in the JVM actually running.

ONE-SENTENCE TAKEAWAY: garbage collection reclaims what is UNREACHABLE — not what is unused, which is
why Java leaks — and it is built on the measurement that most objects die young, so the heap is split
and the young region collected by COPYING SURVIVORS OUT and freeing the rest wholesale, making the cost
proportional to what lived rather than what died and making allocation a lock-free pointer bump; choose
Parallel for throughput, G1 by default, ZGC when pauses matter at any heap size, and Serial on one
core — but diagnose growth and pauses as separate problems first, because almost every real GC incident
is a retention bug or an allocation rate, and neither is fixed with a flag.""",
]


DEEP["Virtual threads (Java 21) — what actually changed"] = [
"""1. THE GOAL IN PLAIN ENGLISH — getting blocking code back

For twenty-five years a Java thread was an OPERATING SYSTEM thread. One-to-one. The OS reserved about a
megabyte of stack for each one, switching between them meant a trip through the kernel, and the
practical ceiling was a few thousand per process — not because Java said so, but because the OS did.

    THAT CEILING SHAPED HOW EVERYONE WROTE SERVERS. The natural design — one thread per request, write
    plain blocking code, let the thread wait — stopped working the moment you needed ten thousand
    concurrent requests. So the industry moved to callbacks, then futures, then reactive streams: every
    blocking call rewritten as "start this, and here is what to do when it finishes".

    THE COST OF THAT MOVE WAS ENORMOUS AND MOSTLY UNCOUNTED. Stack traces became useless, because the
    stack no longer contains the logical caller. Breakpoints stopped meaning anything. try/catch and
    try-with-resources no longer spanned the operation. ThreadLocal stopped working. And the code
    inverted: the sequence you wanted to express was scattered across a dozen callbacks.

    VIRTUAL THREADS REMOVE THE CEILING, SO THE ORIGINAL DESIGN WORKS AGAIN. A virtual thread is
    scheduled by the JVM, not the OS. It costs a few hundred bytes, not a megabyte. You can have
    millions. So you go back to writing `var response = http.send(request)` on one line, blocking, in a
    thread of its own — and your stack traces, debugger, and exception handling all work again.

    THE HEADLINE IS NOT SPEED. A virtual thread does not make one request faster. It makes it cheap to
    have a million requests in flight, WITHOUT giving up the programming model. THAT is the change.

THE EVERYDAY VERSION: a restaurant where each waiter can serve exactly one table and must stand there
while the kitchen cooks. With ten waiters you seat ten tables. The old fix was to make every waiter
juggle twenty tables with a clipboard of half-finished orders — more throughput, far more mistakes, and
nobody can tell you what is happening at table six. Virtual threads make waiters nearly free instead:
one per table again, and each one can simply stand and wait.

TERMS AS THEY APPEAR:
- PLATFORM THREAD: the old kind. One OS thread each.
- CARRIER THREAD: a platform thread that a virtual thread is currently running on.
- MOUNT / UNMOUNT: a virtual thread being placed on, or lifted off, a carrier.
- PINNING: a virtual thread that cannot unmount, so it holds its carrier while blocked.""",

"""2. THE INTUITION — why blocking became cheap

WHEN A PLATFORM THREAD BLOCKS ON I/O, the OS parks it. Its stack — up to a megabyte of reserved address
space — sits idle, and the kernel must be involved to switch to something else. Ten thousand of those
is ten gigabytes of reserved stack and a scheduler with ten thousand entries to manage.

    A VIRTUAL THREAD'S STACK LIVES ON THE JAVA HEAP. That single fact is the whole design.

    When a virtual thread blocks, the JVM COPIES ITS STACK FRAMES TO THE HEAP, lifts it off the carrier,
    and runs a different virtual thread on that same carrier. When the I/O completes, the frames are
    copied back onto a carrier — not necessarily the same one — and it continues from exactly where it
    was. The Java code never notices. It called `read()`, and `read()` returned.

    SO "BLOCKING" NO LONGER MEANS "OCCUPYING AN OS THREAD". It means "parking a small heap object". A
    blocked virtual thread costs roughly what its live stack costs, which starts in the hundreds of
    bytes and grows only as deep as the call chain actually goes.

    AND THE SWITCH NEVER ENTERS THE KERNEL. The JVM schedules virtual threads itself, onto a small
    ForkJoinPool of carriers sized by default to the number of processors. Switching is a user-space
    operation, roughly the cost of a method call plus some copying, rather than a kernel context
    switch.

WHICH GIVES THE COMPARISON THAT MATTERS:

                             platform thread          virtual thread
    ---------------------------------------------------------------------
    cost to create           OS syscall, ~1 MB        heap object, ~hundreds of bytes
    practical count          a few thousand           millions
    blocking costs           an OS thread             a parked heap object
    context switch           kernel                   user space
    scheduled by             the OS                   the JVM
    CPU-BOUND THROUGHPUT     THE SAME                 THE SAME

    THAT LAST ROW IS THE ONE PEOPLE MISS, AND IT IS THE MOST IMPORTANT. If your task is computing
    rather than waiting, virtual threads do nothing whatsoever. You still have the same number of cores.
    Virtual threads solve WAITING, and only waiting. A CPU-bound workload wants a bounded pool sized to
    the cores, exactly as before.

THE DEEPER POINT: the reason we pooled threads was that threads were expensive. POOLING WAS NEVER THE
GOAL — it was a workaround. Remove the expense and the workaround becomes an anti-pattern, which is why
the recommended usage is one virtual thread per task, created and discarded, with no pool at all.""",

"""3. THE MECHANISM — continuations, carriers, and pinning

UNDERNEATH A VIRTUAL THREAD IS A CONTINUATION — an object that can capture the current call stack, be
put aside, and later be resumed. `Continuation.yield()` copies the frames from the carrier's stack onto
the heap; `Continuation.run()` copies them back and jumps to where it left off.

    EVERY BLOCKING OPERATION IN THE JDK WAS REWRITTEN TO YIELD INSTEAD OF BLOCK. Socket reads, file
    channel operations, `Thread.sleep`, `BlockingQueue.take`, lock acquisition, `Future.get`. When a
    virtual thread calls one, the JDK registers interest in the event, yields, and the carrier
    immediately picks up another virtual thread.

    THIS IS WHY IT ONLY WORKS FOR JDK BLOCKING. A blocking call inside a NATIVE library — a JNI
    method, or an old driver doing its own socket I/O — cannot yield, because the JVM cannot copy a
    native frame to the heap and put it back. It blocks the carrier.

THE CARRIER POOL. A dedicated ForkJoinPool, in FIFO mode, with parallelism defaulting to
`availableProcessors()`. It is NOT the common pool. Its size caps how many virtual threads can be
RUNNING at once, which is exactly right — that number should equal your cores. What is uncapped is how
many can be WAITING.

PINNING — the one failure mode you must know:

    A virtual thread CANNOT unmount while it is inside a `synchronized` block or method, or while it
    has native frames on its stack. In those states, blocking blocks the CARRIER.

    THE SYMPTOM IS A THROUGHPUT CLIFF, NOT AN ERROR. If every request holds a `synchronized` lock
    across its database call, then on an 8-core machine you have 8 carriers, all pinned, and your
    million virtual threads run 8 at a time. Nothing throws. The application is simply and
    inexplicably serialised. In the worst case it DEADLOCKS: every carrier pinned, waiting on work that
    needs a carrier to proceed.

    THIS IS WHY THE STANDARD ADVICE WAS TO REPLACE `synchronized` WITH `ReentrantLock`, which is
    virtual-thread aware and unmounts correctly. JEP 491 in JDK 24 removed the `synchronized`
    limitation, so on a modern JDK it is largely historical — but native frames still pin, and a great
    deal of production code still runs on 21.

    DETECTING IT: the JFR event `jdk.VirtualThreadPinned`, or `-Djdk.tracePinnedThreads=full` on 21.

OTHER PROPERTIES WORTH KNOWING: virtual threads are ALWAYS daemon threads, so they do not keep the JVM
alive. Priorities are ignored. Thread groups are vestigial. And `jcmd <pid> Thread.dump_to_file
-format=json` gives you a dump of a million of them, grouped, which is the observability story that
callbacks never had.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — POOLING VIRTUAL THREADS. `Executors.newFixedThreadPool` of virtual threads reintroduces the
exact limit they exist to remove. Use `newVirtualThreadPerTaskExecutor()`. THE POOL WAS THE WORKAROUND,
NOT THE GOAL.

CASE 2 — PINNING ON `synchronized` (JDK 21–23). A lock held across a blocking call pins the carrier;
throughput collapses to the carrier count, silently. `ReentrantLock` instead, or JDK 24+.

CASE 3 — PINNING ON NATIVE FRAMES. A JNI-based driver or a native crypto call cannot unmount. Still
true on every JDK version.

CASE 4 — EXPECTING CPU-BOUND WORK TO GET FASTER. It will not. You have the same cores. Virtual threads
address waiting only.

CASE 5 — THE LIMITER MOVED, AND NOBODY NOTICED. A 200-thread pool was silently rate-limiting your
database to 200 concurrent queries. Replace it with unbounded virtual threads and the database receives
ten thousand, and falls over. THE THREAD POOL WAS LOAD-SHEDDING INFRASTRUCTURE THAT NOBODY DOCUMENTED.
Use a `Semaphore` to bound the resource explicitly, which is the honest version of what the pool was
doing.

CASE 6 — CONNECTION POOL EXHAUSTION AS THE NEW BOTTLENECK. Ten thousand virtual threads queueing for
twenty connections is not progress; it is the same queue in a different place, now with ten thousand
objects waiting in it.

CASE 7 — ThreadLocal AT SCALE. It still works, but a ThreadLocal holding 1 KB across a million virtual
threads is a gigabyte. `ScopedValue` is the designed replacement: immutable, bounded to a syntactic
scope, and inherited by child threads cheaply.

CASE 8 — LONG CPU-BOUND SECTIONS INSIDE A VIRTUAL THREAD. Nothing preempts them. A virtual thread only
yields at a blocking point, so a tight computational loop monopolises its carrier.

CASE 9 — `Thread.currentThread()` IDENTITY AS A KEY. With a thread per task, identity-keyed caches now
have a million entries instead of two hundred.

CASE 10 — MONITORING THAT COUNTS THREADS. Dashboards, alerts and thread-count-based autoscaling all
become meaningless. Count in-flight TASKS instead.

CASE 11 — STACK DEPTH. Deep recursion in a virtual thread grows a heap-allocated stack; it is not free,
and the failure mode is memory pressure rather than a neat StackOverflowError at a familiar depth.

CASE 12 — ASSUMING FRAMEWORK SUPPORT MEANS FRAMEWORK READINESS. A framework may run your handler on a
virtual thread while its own internals still hold `synchronized` locks across I/O, giving you all of
the migration and none of the benefit.""",

"""5. THE ALTERNATIVES — and what virtual threads replaced

PLATFORM THREADS WITH A BOUNDED POOL. Still exactly right for CPU-BOUND work: you want as many runnable
tasks as cores and no more. `Executors.newFixedThreadPool(cores)` is not obsolete; it was never about
I/O in the first place.

REACTIVE — Reactor, RxJava, Mutiny. What virtual threads are largely displacing for the ordinary case:
    THEY DELIVERED the same scalability, years earlier, on Java 8.
    THEY COST stack traces that do not show your caller, debuggers that cannot step, exceptions that
    escape into an error channel, ThreadLocal-based context that has to be reimplemented, and the
    "coloured function" problem where one async call forces every caller to become async.
    THEY STILL WIN when you genuinely need STREAM SEMANTICS — backpressure, windowing, merging, and
    operators over an unbounded flow. Virtual threads give you cheap concurrency, not a dataflow
    algebra. Do not rewrite a real streaming pipeline into blocking calls.

ASYNCHRONOUS NIO AND CompletableFuture BY HAND. Same trade as reactive, less machinery, more
boilerplate. `CompletableFuture` remains the right tool for COMPOSING independent operations and for
timeouts; it is no longer needed merely to avoid blocking a thread.

KOTLIN COROUTINES. The same idea — suspending instead of blocking — implemented in the compiler rather
than the runtime, with the `suspend` keyword making the colouring explicit. Virtual threads put it in
the JVM instead, so it works for every language and every existing library without recompilation.

STRUCTURED CONCURRENCY (`StructuredTaskScope`), which is the piece that makes virtual threads a
programming model rather than just a cheap thread:
    tasks forked in a block CANNOT OUTLIVE the block;
    a failure in one can cancel its siblings automatically;
    the parent's stack trace contains the child's, so an error is traceable to its origin;
    cancellation propagates down the tree instead of leaking.
    It restores to concurrency what `try`/`finally` did to resources: a lifetime bounded by syntax.

WHAT TO SAY: "Virtual threads for I/O-bound concurrency and thread-per-request, a bounded platform pool
for CPU-bound work, and reactive only where I genuinely need streaming semantics rather than just
scalability. And a Semaphore wherever the old thread pool was quietly limiting a downstream resource."

""",

"""6. HOW TO ADOPT THEM — numbered steps

STEP 1 — CONFIRM YOUR WORKLOAD IS I/O-BOUND. If threads are computing rather than waiting, virtual
threads change nothing and you should stop here.

STEP 2 — USE `Executors.newVirtualThreadPerTaskExecutor()`. One thread per task, created and discarded.
Do not pool them; that is the thing being removed.

STEP 3 — FIND EVERY `synchronized` BLOCK THAT SPANS A BLOCKING CALL. On JDK 21–23 these pin the carrier
and silently cap you at the core count. Convert to `ReentrantLock`, or move to JDK 24+.

STEP 4 — AUDIT NATIVE CALLS. JNI-based drivers and native crypto still pin on every version.

STEP 5 — REPLACE THE POOL'S IMPLICIT RATE LIMIT WITH AN EXPLICIT ONE. A `Semaphore` around the database,
the downstream service, the disk. THIS IS THE STEP MOST MIGRATIONS SKIP, and it is what turns "we
enabled virtual threads" into "we took down the database".

STEP 6 — SIZE THE CONNECTION POOL FOR THE NEW CONCURRENCY. Ten thousand threads and twenty connections
is the same queue, relocated.

STEP 7 — REVIEW ThreadLocal USAGE. Multiply its size by the number of concurrent tasks. Move context to
`ScopedValue` where you can.

STEP 8 — TURN ON PINNING DETECTION BEFORE YOU BELIEVE IT WORKS. JFR's `jdk.VirtualThreadPinned`, or
`-Djdk.tracePinnedThreads=full`. A pinning problem produces no error at all — only a number that is
lower than you expected.

STEP 9 — FIX YOUR MONITORING. Thread count is no longer a signal. Alert on in-flight tasks, queue depth
at the real bottleneck, and latency.

STEP 10 — USE `StructuredTaskScope` FOR FAN-OUT. Bounded lifetimes, automatic sibling cancellation, and
child stack traces attached to the parent.

STEP 11 — LOAD TEST WITH THE REAL DOWNSTREAM. The failure mode of this migration is never the JVM; it
is whatever the JVM is now allowed to hit ten thousand times at once.

STEP 12 — LEAVE CPU-BOUND WORK ON A BOUNDED PLATFORM POOL. Mixing the two is fine and expected; the
distinction is the point.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'For twenty-five years a Java thread was an OS thread, one to one. About a megabyte of reserved stack
each, switching went through the kernel, and you got a few thousand per process. That ceiling is why
everyone abandoned thread-per-request and moved to callbacks and reactive.

And that move cost a lot that nobody counted. Stack traces stopped containing your caller. Breakpoints
stopped meaning anything. try-with-resources no longer spanned the operation. ThreadLocal broke. And
one async call forces every caller to become async — the coloured function problem.

A virtual thread is scheduled by the JVM instead of the OS, and its stack lives on the HEAP. That one
fact is the whole design. When it blocks, the JVM copies its frames to the heap, lifts it off the
carrier thread, and runs something else there. When the I/O completes the frames get copied back — not
necessarily onto the same carrier — and it continues. The Java code never notices; it called read(),
and read() returned.

So blocking no longer means occupying an OS thread. It means parking a small heap object, a few hundred
bytes, and the switch never enters the kernel. You can have millions.

The thing people get wrong is thinking this is about speed. It is not. CPU-bound throughput is
IDENTICAL — you still have the same cores. Virtual threads solve WAITING, and only waiting. CPU-bound
work still wants a bounded pool sized to the cores.

And the second thing: don't pool them. We pooled threads because threads were expensive. Pooling was
never the goal, it was a workaround, so a pool of virtual threads reintroduces exactly the limit they
remove. It's newVirtualThreadPerTaskExecutor, one per task, created and thrown away.

The failure mode to know is PINNING. A virtual thread can't unmount while it's inside a synchronized
block or has native frames on its stack — so blocking there blocks the CARRIER. And the symptom is a
throughput cliff with no error at all: eight cores, eight carriers, all pinned, and your million
virtual threads run eight at a time. In the worst case it deadlocks. That's why the advice on 21 was
ReentrantLock instead of synchronized; JEP 491 in JDK 24 fixed the synchronized case, but native frames
still pin.

The operational trap I'd flag hardest, though, is that THE LIMITER MOVED. That 200-thread pool was
silently rate-limiting your database to 200 concurrent queries — it was load-shedding infrastructure
nobody documented. Swap in unbounded virtual threads and the database gets ten thousand and falls over.
So you replace the pool's implicit limit with an explicit Semaphore around each downstream resource.
That's the step migrations skip.

And the piece that makes it a programming model rather than just cheap threads is structured
concurrency — StructuredTaskScope. Forked tasks can't outlive the block, a failure cancels its
siblings, and the child's stack trace is attached to the parent's. It does for concurrency what
try/finally did for resources: a lifetime bounded by syntax.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE OLD CEILING, MADE CONCRETE ──────────────────────────────────
    var pool = Executors.newFixedThreadPool(200);
    //                                      ^^^ 200 OS threads, ~200 MB of reserved
    //   stack, and a HARD CAP OF 200 CONCURRENT REQUESTS — not because 200 is
    //   right, but because 10,000 OS threads is not affordable.

    // ── THE NEW VERSION. Note what is NOT here: a size. ─────────────────
    try (var exec = Executors.newVirtualThreadPerTaskExecutor()) {
    //               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ONE VIRTUAL THREAD PER TASK.
    //   Not a pool. Creating and discarding a virtual thread is the intended usage;
    //   pooling them reintroduces the exact limit they exist to remove.
        for (var req : requests) {
            exec.submit(() -> handle(req));      // a million of these is fine
        }
    }   // close() waits for all tasks — the executor is an AutoCloseable barrier

    String handle(Request r) {
        var user = db.findUser(r.userId());      // BLOCKS. The virtual thread's
        //                                          frames are copied to the heap and
        //                                          the carrier immediately runs
        //                                          another virtual thread.
        var prefs = prefsService.fetch(user);    // BLOCKS again. Same story.
        return render(user, prefs);
    }
    // ^ Plain, sequential, blocking code. The stack trace of any exception in here
    //   contains handle() and its caller. A breakpoint works. try/catch spans the
    //   whole operation. THAT is what was given up for scalability, and given back.

    // ── PINNING: the bug with no error message ──────────────────────────
    synchronized (lock) {                 // ← the carrier CANNOT be released while
        var row = db.query(sql);          //   this frame is on the stack (JDK 21-23)
    }
    // ^ 8 cores → 8 carriers → all 8 pinned → your million virtual threads run
    //   EIGHT AT A TIME. Nothing throws. Throughput is just inexplicably flat.
    private final ReentrantLock lock = new ReentrantLock();
    lock.lock();
    try { var row = db.query(sql); } finally { lock.unlock(); }
    // ^ virtual-thread aware: unmounts correctly. (JEP 491 in JDK 24 fixes the
    //   synchronized case too — but NATIVE frames still pin on every version.)

    // ── THE LIMITER MOVED. The step migrations skip. ────────────────────
    private final Semaphore dbLimit = new Semaphore(200);
    //                                              ^^^ the 200 that used to be the
    //   POOL SIZE. It was rate-limiting the database all along, and nobody wrote
    //   that down. Remove the pool without this and the database receives 10,000
    //   concurrent queries.
    dbLimit.acquire();
    try { return db.query(sql); } finally { dbLimit.release(); }

    // ── STRUCTURED CONCURRENCY: lifetimes bounded by syntax ─────────────
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        var user  = scope.fork(() -> userService.find(id));
        var order = scope.fork(() -> orderService.recent(id));
        scope.join().throwIfFailed();
    //  ^ NEITHER TASK CAN OUTLIVE THIS BLOCK. If one fails, the other is cancelled
    //    automatically, and the child's stack trace is attached to this one's.
        return new Page(user.get(), order.get());
    }

    // ── WHAT DOES NOT CHANGE ────────────────────────────────────────────
    var cpu = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
    // ^ CPU-bound work. Same cores, same answer as before virtual threads existed.""",

"""9. THE TRACE — one carrier, three virtual threads, and then a pin

EIGHT CARRIERS ON AN 8-CORE MACHINE. Follow ONE of them while three virtual threads run on it:

    time  carrier-1 is running   what happened                          carrier state
    ------------------------------------------------------------------------------------
    t0    VT-1                   calls db.query()                       —
    t1    —                      VT-1's frames COPIED TO THE HEAP,      FREE, instantly
                                 unmounted, socket read registered
    t2    VT-2                   mounted on carrier-1, starts running   busy
    t3    —                      VT-2 calls http.send(), unmounts       FREE
    t4    VT-3                   mounted, runs, computes for 2 ms       busy
    t5    VT-1                   DB responded → frames copied BACK,     busy
                                 possibly onto a DIFFERENT carrier,
                                 and `query()` simply returns
    ------------------------------------------------------------------------------------
    ONE OS THREAD SERVED THREE REQUESTS AND WAS NEVER IDLE. No callbacks were written. VT-1's stack at
    t5 still contains `handle()` and everything that called it, because those frames were preserved
    verbatim — that is what makes the debugger and the stack trace work.

NOW THE SAME TRACE WITH `synchronized` AROUND THE QUERY (JDK 21):

    t0    VT-1                   enters synchronized, calls db.query()  —
    t1    VT-1 (BLOCKED)         CANNOT UNMOUNT — a monitor is held.    PINNED, 40 ms
                                 The carrier is stuck waiting on I/O.
    t2    VT-1 (BLOCKED)         VT-2 and VT-3 are runnable and CANNOT  still pinned
                                 be scheduled here.
    ------------------------------------------------------------------------------------
    MULTIPLY BY 8 CARRIERS: your concurrency is 8, not a million. NOTHING THROWS. No warning, no
    exception, no log line — only a throughput number that is lower than expected and a profile that
    shows everything waiting. This is the single most common disappointment in a virtual-thread
    migration, and it is invisible unless you enable `jdk.VirtualThreadPinned`.

AND THE THIRD TRACE — the one that takes down the database:

    before                                    after
    ------------------------------------------------------------------------------------
    200-thread pool                           unbounded virtual threads
    → at most 200 concurrent DB queries       → 10,000 concurrent DB queries
    → the pool was LOAD SHEDDING              → nothing is shedding load
    → excess requests queued in the pool      → excess requests hit the database
    → latency rose, the system survived       → connections exhausted, timeouts,
                                                 cascading failure upstream

    NOTHING IN THE JVM WENT WRONG. The application did exactly what it was now permitted to do. The
    200 was never a thread-count decision; it was a concurrency budget for a downstream resource,
    expressed in the only unit the old model had. THE FIX IS TO SAY IT OUT LOUD — a Semaphore of 200
    around the database — which is both the correct behaviour and the first time it has ever been
    written down.

WHAT EACH TRACE PROVED:
    TRACE 1   the stack-on-heap mechanism, and why blocking code keeps its stack trace.
    TRACE 2   pinning: a correctness-preserving, silent, order-of-magnitude throughput loss.
    TRACE 3   that a thread pool is TWO things — a resource pool and a rate limiter — and virtual
              threads remove the first while leaving you responsible for the second.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Platform thread: ~1 MB reserved stack, an OS scheduling entity, a few thousand per process.
    Virtual thread: hundreds of bytes initially, growing with real stack depth; millions per process.
    Mount/unmount: user-space, roughly a method call plus stack copying. No kernel transition.
    Carrier pool: a dedicated ForkJoinPool, parallelism = availableProcessors by default. It caps how
    many run AT ONCE, which is correct; what is uncapped is how many WAIT.
    CPU-bound throughput: UNCHANGED. Identical core count, identical result.
    Pinned carrier: concurrency silently drops to the carrier count, with no error of any kind.

THE #1 MISTAKE: pooling virtual threads. The pool was the workaround for expensive threads; keeping it
keeps the limit. `newVirtualThreadPerTaskExecutor()`.

THE #2 MISTAKE: expecting CPU-bound work to speed up. Same cores. Virtual threads address waiting only.

THE #3 MISTAKE: `synchronized` across a blocking call on JDK 21–23. Pins the carrier, silently.
`ReentrantLock`, or JDK 24+.

THE #4 MISTAKE: forgetting native frames still pin, on every version.

THE #5 MISTAKE — AND THE ONE THAT CAUSES OUTAGES: removing the pool without replacing the rate limit it
was silently providing. Put a `Semaphore` around every downstream resource.

THE #6 MISTAKE: leaving the connection pool at twenty. Ten thousand threads queueing for twenty
connections is the same queue, relocated and larger.

THE #7 MISTAKE: ThreadLocal at a million-thread scale. Multiply its size by the concurrency.
`ScopedValue` instead.

THE #8 MISTAKE: long CPU-bound sections inside a virtual thread. Nothing preempts them; a virtual
thread yields only at a blocking point.

THE #9 MISTAKE: monitoring thread count. It is no longer a signal. Count in-flight tasks.

THE #10 MISTAKE: believing they replace reactive entirely. They replace it for SCALABILITY; reactive
still wins where you need real stream semantics — backpressure, windowing, merging.

THE #11 MISTAKE: assuming a framework running handlers on virtual threads is ready. Its internals may
still hold monitors across I/O, giving you the migration and none of the benefit.

ONE-SENTENCE TAKEAWAY: a virtual thread is scheduled by the JVM with its stack on the HEAP, so blocking
means copying frames aside and freeing the carrier rather than occupying an OS thread — which makes
millions of concurrent waiting tasks affordable and hands back plain blocking code with working stack
traces, debuggers and try/finally, at the cost of exactly zero improvement to CPU-bound work; do not
pool them, watch for pinning on `synchronized` (pre-JDK 24) and native frames where throughput
collapses to the carrier count with no error at all, and above all replace the rate limit your old
thread pool was silently enforcing on every downstream resource, because that limit is the reason the
database survived.""",
]


DEEP["ArrayList vs LinkedList — and why the textbook answer is usually wrong"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the answer everyone gives, and why it is wrong

THE TEXTBOOK ANSWER: an ArrayList is an array, so reading by index is instant but inserting in the
middle means shifting everything after it. A LinkedList is a chain of nodes each pointing at the next,
so inserting is just rewiring two pointers, but reading the thousandth element means walking a
thousand links. Therefore: ArrayList for reading, LinkedList for inserting.

    THAT ANSWER IS ALGORITHMICALLY CORRECT AND PRACTICALLY WRONG. On real hardware, for essentially
    every workload you will meet, ArrayList wins — INCLUDING at inserting and removing in the middle,
    which is precisely the case LinkedList is supposed to own.

    THE REASON IS NOT IN THE BIG-O. Big-O counts OPERATIONS and assumes every memory access costs the
    same. On a modern CPU that assumption is false by a factor of about a hundred: a value already in
    cache arrives in roughly a nanosecond, and one that must come from main memory takes closer to a
    hundred. An algorithm that touches memory PREDICTABLY beats one that touches less memory
    UNPREDICTABLY, and it beats it by more than the operation count suggests.

THE EVERYDAY VERSION: two ways to store a hundred documents. One is a single stack on your desk — to
insert in the middle you lift half the stack, which is real work, but it is one smooth motion. The
other scatters the hundred documents across a hundred rooms in a building, each with a note saying
which room the next one is in. Inserting is trivial: change two notes. Getting to document fifty means
walking to fifty rooms. AND THE WALKING IS THE ENTIRE COST — the fact that you did less "work" at the
insertion point is irrelevant next to it.

TERMS AS THEY APPEAR:
- CACHE LINE: memory is fetched in blocks, typically 64 bytes. Reading one byte fetches all 64.
- LOCALITY: whether the things you access next are near the things you accessed last.
- PREFETCHER: hardware that notices sequential access and fetches ahead of you, for free.
- POINTER CHASING: following a reference to find the address of the next reference. Unpredictable
  by construction, so the prefetcher cannot help.""",

"""2. THE INTUITION — why contiguity beats operation count

AN ARRAYLIST IS ONE CONTIGUOUS ARRAY OF REFERENCES. Walking it, the CPU reads 64 bytes at a time and
gets sixteen references per fetch (with compressed pointers). The prefetcher sees the pattern
immediately and loads the NEXT block while you are still using this one. In steady state you wait for
memory almost never.

A LINKEDLIST IS N SEPARATE NODE OBJECTS, each holding a previous pointer, a next pointer, and the item.
They are allocated at different times and land at different addresses.

    TO REACH THE NEXT ELEMENT YOU MUST FIRST READ THE CURRENT NODE — because the address of the next
    one IS THE DATA IN THIS ONE. The CPU cannot fetch ahead, because it does not know where ahead is
    until the current fetch returns. THAT IS A SERIALISED DEPENDENCY CHAIN OF MEMORY LOADS, and it is
    the worst pattern modern hardware has.

NOW COUNT THE MEMORY, which is the second half of the story:

    ARRAYLIST, per element: one 4-byte reference, plus up to 50% slack capacity. Call it 4–6 bytes.
    LINKEDLIST, per element: a Node object — 12-byte header, prev, next, item = 24 bytes, plus the
    element itself. Call it 24 bytes.

    THAT IS ROUGHLY FIVE TIMES THE MEMORY, and memory bandwidth is the scarce resource. A list that
    fits in L2 cache as an ArrayList may not fit as a LinkedList, and the difference between "in cache"
    and "not in cache" is the hundred-fold one.

AND THE INSERT CASE — the one LinkedList is supposed to win — has a hidden step:

    `list.add(5000, x)` ON A LINKEDLIST IS NOT O(1). The rewiring is O(1); FINDING position 5000 is
    O(n), and it is O(n) of the worst possible kind — five thousand dependent cache misses. The O(1)
    only exists if you ALREADY HOLD the node, and Java's `List` interface never gives you one.

    `list.add(5000, x)` ON AN ARRAYLIST IS O(n) SHIFTING — via `System.arraycopy`, which is a JVM
    INTRINSIC compiled to a vectorised block move. It moves many bytes per instruction, sequentially,
    at memory bandwidth. Moving ten thousand references costs a few microseconds.

    SO THE COMPARISON IS: a vectorised sequential block move, versus five thousand serialised pointer
    dereferences. The one with the better Big-O loses, and it loses badly.

THE HONEST SUMMARY, which is what makes this a good interview answer: LINKEDLIST'S ADVANTAGE IS REAL
ONLY WHEN YOU ALREADY HAVE A REFERENCE TO THE POSITION — which in Java means you are iterating and
using `Iterator.remove()`. Every other case, ArrayList.""",

"""3. THE MECHANISM — growth, arraycopy, and what each class actually is

ARRAYLIST INTERNALS:

    Object[] elementData;   // the backing array. Note: Object[], because of erasure.
    int size;               // how many are USED. capacity is elementData.length.

    GROWTH. When full, a new array of `oldCapacity + (oldCapacity >> 1)` — 1.5x — is allocated and the
    contents copied. The default starting capacity is 10, and it is allocated LAZILY on first add.
    Growth is O(n) but AMORTISED O(1): doubling-ish growth means the total copying across n additions
    is O(n), so each addition averages constant.
    `ensureCapacity(n)` up front skips all of it, and matters when n is large and known.

    add(i, x)        System.arraycopy shifts [i, size) right by one, then writes. O(n) but VECTORISED.
    remove(i)        System.arraycopy shifts left, then nulls the last slot (so it can be collected).
    get(i)           one bounds check, one array read. Genuinely O(1).

    THE SLACK IS A REAL COST. After growth an ArrayList can be up to 50% empty, and `trimToSize()`
    exists for the case where that matters. `remove` never shrinks the array.

LINKEDLIST INTERNALS: a doubly-linked list with head and tail pointers.

    private static class Node<E> { E item; Node<E> next; Node<E> prev; }

    get(i)           walks from the NEARER END — so index 0 and index size-1 are fast, and the middle
                     is the worst case at n/2 dependent loads. Still O(n).
    add(i, x)        walks to i, then rewires. O(n) walk + O(1) rewire.
    addFirst/addLast O(1) genuinely, and this is the only operation where it is competitive.
    Iterator.remove  O(1) genuinely, because the iterator holds the node.

    IT ALSO IMPLEMENTS Deque. Which is the source of most remaining uses — and `ArrayDeque` does the
    same job on a circular array, with better locality and less memory, so it wins there too.

THE OPERATION THAT DECIDES MOST REAL CODE — removing while iterating:

    ARRAYLIST + Iterator.remove()   O(n) per removal, because it still arraycopies the tail.
                                    Removing k elements one at a time is O(nk).
    ARRAYLIST + removeIf(pred)      ONE PASS. It marks survivors in a bitset and compacts once. O(n)
                                    TOTAL regardless of how many are removed. This is the fastest
                                    option available and most people do not know it exists.
    LINKEDLIST + Iterator.remove()  O(1) per removal, O(n) total — algorithmically the best, and
                                    still typically slower in wall clock because the WALK is the
                                    dominant cost, not the removals.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `list.remove(0)` IN A LOOP TO DRAIN AN ARRAYLIST. Each removal shifts everything left, so
draining n elements is O(n²). Iterate forwards and clear, iterate BACKWARDS removing from the end, or
use `ArrayDeque` if it is really a queue.

CASE 2 — `list.remove(1)` MEANING TWO DIFFERENT THINGS. On a `List<Integer>`, `remove(int)` removes by
INDEX and `remove(Object)` removes by VALUE. `remove(1)` picks the index overload. `remove(Integer.valueOf(1))`
removes the value. The compiler chooses silently and both compile.

CASE 3 — USING LINKEDLIST AS A QUEUE. `ArrayDeque` does it with better locality, less memory, and no
per-element node allocation. LinkedList's Deque implementation is essentially legacy.

CASE 4 — GROWTH THRASH ON A KNOWN SIZE. Building a 100,000-element ArrayList from the default capacity
performs about 25 reallocations and copies. `new ArrayList<>(100_000)` performs none.

CASE 5 — MEMORY AFTER A LARGE LIST SHRINKS. `remove` never shrinks the backing array, so a list that
held a million elements still holds a million-slot array. `trimToSize()`.

CASE 6 — `Arrays.asList(...)` IS FIXED-SIZE. It is a VIEW over the array: `set` works and writes
through to the array, `add` and `remove` throw UnsupportedOperationException.

CASE 7 — `List.of(...)` IS FULLY IMMUTABLE AND REJECTS NULLS. Different failure from `Arrays.asList`,
which permits nulls.

CASE 8 — `subList` IS A VIEW, NOT A COPY. Structurally modifying the backing list invalidates it —
ConcurrentModificationException on next use — and modifying the sublist writes through to the parent.

CASE 9 — MEASURING WITH A LIST THAT FITS IN CACHE. A thousand-element benchmark shows LinkedList
looking respectable, because everything is in L1 and locality is free. At a million the gap becomes
enormous. THE SIZE AT WHICH YOU BENCHMARK DETERMINES THE ANSWER YOU GET.

CASE 10 — ASSUMING `contains` IS CHEAP. O(n) on both, with an `equals` call per element. If you are
calling it in a loop you wanted a `HashSet` and the whole comparison is beside the point.

CASE 11 — THREAD SAFETY ON NEITHER. `Collections.synchronizedList` locks every method but not
iteration; `CopyOnWriteArrayList` is right for read-mostly with rare writes.

CASE 12 — NULLS. Both permit them, so `list.get(i) == null` is ambiguous between "absent" and "stored
null" in exactly the way `Map.get` is.""",

"""5. THE ALTERNATIVES — what to reach for instead of either

ARRAYLIST is the default, and should be. Contiguous, cache-friendly, minimal per-element overhead,
`System.arraycopy` for the shifting. Reach for it unless you can name why not.

ARRAYDEQUE for anything queue- or stack-shaped. A circular array: O(1) at both ends with no node
allocation and good locality. IT BEATS BOTH `LinkedList` AND `Stack` AT THEIR OWN JOBS, and the
Javadoc says so explicitly.

HASHSET / LINKEDHASHSET the moment membership is the question. If you are calling `list.contains` in a
loop, this is the real fix and the ArrayList-versus-LinkedList question was never the bottleneck.

TREEMAP / PRIORITYQUEUE when you need ordering or a repeatedly-extracted minimum. A sorted ArrayList
that you re-sort is usually the wrong shape.

PRIMITIVE COLLECTIONS — Eclipse Collections, fastutil, HPPC — when the elements are primitives.
`ArrayList<Integer>` stores a reference to a boxed object per element: roughly 20 bytes and a pointer
dereference each, against 4 bytes contiguous for an `int[]`. FOR LARGE NUMERIC DATA THIS IS A BIGGER
WIN THAN ANY LIST CHOICE.

`int[]` OR `long[]` DIRECTLY when the size is fixed. No abstraction, no boxing, perfect locality.

COPYONWRITEARRAYLIST for read-mostly concurrent access — listener registries, configuration snapshots.
Every write copies the whole array, so it is wrong for anything write-heavy and perfect for the case
where writes are rare and iteration must never block.

`removeIf` INSTEAD OF AN ITERATOR LOOP. One compacting pass on an ArrayList, regardless of how many
elements match.

WHEN IS LINKEDLIST ACTUALLY RIGHT? Honestly: almost never in Java. The case it wins — O(1) insertion at
a position you already hold — requires node access the `List` interface does not expose, so the only
realisation is `Iterator.remove()` during a walk, and even there `removeIf` on an ArrayList usually
wins in wall-clock time. Java's own collections author has said publicly that he wrote it and does not
use it.

WHAT TO SAY: "ArrayList by default; ArrayDeque for queues and stacks; a Set if the question is
membership; primitive arrays or a primitive collection library if the elements are numbers. I would
want a measured reason to choose LinkedList, and I have not had one."

""",

"""6. HOW TO CHOOSE — numbered steps

STEP 1 — ASK WHAT THE ACCESS PATTERN ACTUALLY IS, not what the operation is called. "Insert in the
middle" via an index is a WALK plus an insert, and the walk dominates.

STEP 2 — DEFAULT TO ARRAYLIST. It is right often enough that the burden of proof is on the alternative.

STEP 3 — IF IT IS A QUEUE OR A STACK, USE ARRAYDEQUE. Not LinkedList, not `Stack`.

STEP 4 — IF THE QUESTION IS MEMBERSHIP, USE A SET. `list.contains` in a loop is O(n²) and no list
choice fixes it.

STEP 5 — IF THE ELEMENTS ARE PRIMITIVES AND THERE ARE MANY, USE AN ARRAY OR A PRIMITIVE COLLECTION.
Boxing costs more than the list structure ever will.

STEP 6 — PRE-SIZE WHEN YOU KNOW THE SIZE. `new ArrayList<>(n)` removes every reallocation and copy.

STEP 7 — USE `removeIf` FOR BULK REMOVAL. One compacting pass; an iterator loop is O(nk).

STEP 8 — NEVER `remove(0)` IN A LOOP. That is an accidental O(n²), and it is a common one.

STEP 9 — BE CAREFUL WITH `remove` ON A `List<Integer>`. Index or value, chosen silently by overload
resolution.

STEP 10 — IF YOU BENCHMARK, USE A REALISTIC SIZE. A thousand elements fit in cache and hide the entire
effect you are trying to measure.

STEP 11 — TREAT `subList` AND `Arrays.asList` AS VIEWS. They alias, and they throw on operations that
look ordinary.

STEP 12 — FOR CONCURRENT READ-MOSTLY, USE `CopyOnWriteArrayList`; otherwise a proper concurrent
structure. `Collections.synchronizedList` does not make ITERATION safe.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The textbook answer is ArrayList for reading, LinkedList for inserting — O(1) index access versus O(1)
insertion. That's algorithmically correct and practically wrong. On real hardware ArrayList wins
essentially everywhere, including at the middle-insertion case LinkedList is supposed to own.

The reason isn't in the Big-O. Big-O counts operations and assumes every memory access costs the same.
That assumption is off by about a hundred: something in cache arrives in a nanosecond, something from
main memory takes closer to a hundred. So an algorithm that touches memory PREDICTABLY beats one that
touches less memory unpredictably.

An ArrayList is one contiguous array of references. Walking it, the CPU fetches 64 bytes at a time and
gets sixteen references, and the prefetcher sees the pattern and loads the next block while you're
still using this one. You almost never wait.

A LinkedList is n separate node objects at scattered addresses, and to reach the next element you have
to read the current node FIRST — because the address of the next one is the data in this one. The CPU
can't fetch ahead because it doesn't know where ahead is until the current load returns. That's a
serialised chain of dependent cache misses, which is the worst pattern this hardware has.

Then count the memory. ArrayList: about 4 bytes per element plus some slack. LinkedList: a node object
per element — 12-byte header plus prev, next and item — call it 24 bytes. Five times the memory, and
memory bandwidth is the scarce thing.

And the insert case has a hidden step people skip. `list.add(5000, x)` on a LinkedList is NOT O(1). The
rewiring is O(1); FINDING position 5000 is O(n), and it's the worst kind of O(n) — five thousand
dependent cache misses. The O(1) only exists if you already hold the node, and Java's List interface
never gives you one. Meanwhile the ArrayList version is System.arraycopy, which is a JVM intrinsic
compiled to a vectorised block move — many bytes per instruction, sequential, at memory bandwidth.
Shifting ten thousand references takes microseconds.

So the real comparison is a vectorised block move versus five thousand serialised pointer
dereferences. The one with the better Big-O loses, badly.

Where LinkedList's advantage is genuinely real is when you ALREADY have a reference to the position —
which in Java means Iterator.remove during a walk. And even there, removeIf on an ArrayList usually
wins in wall clock, because it does one compacting pass regardless of how many you remove.

Practically: ArrayList by default, ArrayDeque for anything queue- or stack-shaped, a Set the moment the
question is membership, and a primitive array if the elements are numbers — because boxing costs more
than the list structure ever will. I'd want a measured reason to pick LinkedList, and I've never had
one.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT AN ARRAYLIST IS ────────────────────────────────────────────
    transient Object[] elementData;   // ONE contiguous array. 16 references per
    //                                   64-byte cache line with compressed oops.
    private int size;                 // used slots; capacity is elementData.length

    public void add(int index, E element) {
        System.arraycopy(elementData, index, elementData, index + 1, size - index);
    //  ^^^^^^^^^^^^^^^^ A JVM INTRINSIC. Not a loop — a vectorised block move, at
    //  memory bandwidth. Shifting 10,000 references is a few MICROSECONDS.
        elementData[index] = element;
        size++;
    }

    private Object[] grow(int minCapacity) {
        int newCapacity = oldCapacity + (oldCapacity >> 1);   // ← 1.5x
    //                                   ^^^^^^^^^^^^^^^^^ geometric growth is what
    //  makes add() AMORTISED O(1): total copying across n adds is O(n).
        return elementData = Arrays.copyOf(elementData, newCapacity);
    }

    // ── WHAT A LINKEDLIST IS ────────────────────────────────────────────
    private static class Node<E> { E item; Node<E> next; Node<E> prev; }
    //                             ^ 12-byte header + 3 refs = 24 bytes PER ELEMENT,
    //   allocated separately, at whatever address was free at the time.

    Node<E> node(int index) {
        if (index < (size >> 1)) {              // ← walks from the NEARER end
            Node<E> x = first;
            for (int i = 0; i < index; i++) x = x.next;
    //                                       ^^^^^^^^^^ EACH ITERATION MUST WAIT for
    //      the previous load: the address of x.next IS the data in x. The prefetcher
    //      cannot help. This is a serialised chain of cache misses.
            return x;
        } ...
    }

    // ── THE "O(1) INSERT" THAT ISN'T ────────────────────────────────────
    linked.add(5000, x);
    //         ^^^^ node(5000) walks 5,000 links FIRST. O(n) of the worst kind.
    //   Then the rewiring is genuinely O(1) — and irrelevant.
    array.add(5000, x);
    //         ^^^^ one arraycopy of the tail. O(n) that runs at memory bandwidth.

    // ── THE ACCIDENTAL O(n²) ────────────────────────────────────────────
    while (!list.isEmpty()) list.remove(0);
    //                           ^^^^^^^^^ shifts EVERYTHING left, every time.
    //   Draining 100,000 elements does ~5 billion element moves. Use clear(),
    //   iterate backwards, or use an ArrayDeque if it is really a queue.

    // ── THE BULK REMOVAL NOBODY USES ────────────────────────────────────
    list.removeIf(x -> x.isExpired());
    //   ^^^^^^^^ ONE compacting pass — it marks survivors and moves them once,
    //   O(n) TOTAL no matter how many match. An iterator loop calling remove() is
    //   O(n) PER REMOVAL, so O(nk). This is the fastest option available.

    // ── THE OVERLOAD THAT PICKS SILENTLY ────────────────────────────────
    List<Integer> l = new ArrayList<>(List.of(10, 20, 30));
    l.remove(1);                      // remove(int INDEX)  → removes 20
    l.remove(Integer.valueOf(10));    // remove(Object)     → removes the VALUE 10
    // ^ Both compile. The compiler prefers the primitive overload without warning.""",

"""9. THE TRACE — the same operation, two data structures, one cache

WALKING 1,000,000 ELEMENTS. Counting cache behaviour rather than operations:

    ARRAYLIST
    step  what the CPU does                                    memory stalls
    ---------------------------------------------------------------------------------
    1     fetch cache line at elementData[0]                    ONE miss
    2     elements 0..15 are already in that line               ZERO
    3     the prefetcher, having seen the pattern, has          ZERO — the line was
          ALREADY loaded the next line                          fetched during step 2
    ...   repeat
    ---------------------------------------------------------------------------------
    TOTAL ≈ 1,000,000 / 16 = 62,500 line fetches, nearly all PREFETCHED, so nearly
    all free. The loop runs at the speed of the ALU, not of memory.

    LINKEDLIST
    step  what the CPU does                                    memory stalls
    ---------------------------------------------------------------------------------
    1     fetch node[0]                                         ONE miss
    2     read node[0].next → now we know where node[1] is      —
    3     fetch node[1] — AND WE COULD NOT HAVE STARTED THIS     ONE miss, SERIALISED
          UNTIL STEP 2 RETURNED                                 behind step 1
    ...   repeat
    ---------------------------------------------------------------------------------
    TOTAL ≈ 1,000,000 dependent misses. Not "more work" — the SAME number of
    logical steps, each one waiting on the last, at ~100x the latency.

    SAME O(n). ONE RUNS AT MEMORY BANDWIDTH, THE OTHER AT MEMORY LATENCY. That distinction is invisible
    in Big-O and is the entire answer.

NOW THE INSERT AT THE MIDDLE — the case the textbook says LinkedList wins:

    operation                        LinkedList                   ArrayList
    ---------------------------------------------------------------------------------
    find position 500,000            500,000 DEPENDENT misses     0 — it is an index
    perform the insertion            rewire 2 pointers: O(1)      arraycopy 500,000
                                                                  refs: vectorised,
                                                                  sequential
    dominant cost                    THE WALK                     the copy
    which is faster in practice      —                            ARRAYLIST, by a lot
    ---------------------------------------------------------------------------------
    The O(1) that LinkedList is famous for is real. It is just attached to the half of the operation
    that costs nothing, while the half that costs everything is O(n) in the worst possible currency.

AND THE ONE CASE WHERE IT GOES THE OTHER WAY:

    removing 500,000 elements while iterating
    LinkedList + Iterator.remove()   O(1) each, O(n) total     ← algorithmically best
    ArrayList  + Iterator.remove()   O(n) each, O(nk) total    ← genuinely bad, avoid
    ArrayList  + removeIf(pred)      ONE compacting pass       ← usually fastest of all

    THE MIDDLE ROW IS THE REAL TRAP. It is the one people write, it is quadratic, and it is why
    "ArrayList is always faster" is not quite the right lesson. The right lesson is: match the API to
    the access pattern, and on an ArrayList that means `removeIf`.

WHAT PRODUCED WHAT:
    CONTIGUITY          produced the prefetching in trace 1 and the vectorised copy in trace 2.
    POINTER CHASING     produced the serialised miss chain — the single fact behind every row.
    THE List INTERFACE  produced "the O(1) you cannot reach", because it exposes indices, not nodes.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

                          ArrayList              LinkedList
    get(i)                O(1)                   O(n), from the nearer end
    add(x) at the end     amortised O(1)         O(1)
    add(i, x)             O(n) VECTORISED copy   O(n) WALK + O(1) rewire
    remove(i)             O(n) vectorised copy   O(n) walk + O(1) rewire
    Iterator.remove()     O(n) each              O(1) each
    removeIf(pred)        O(n) TOTAL, one pass   O(n)
    contains(x)           O(n)                   O(n)
    memory per element    ~4 bytes + ≤50% slack  ~24 bytes (a Node object)
    locality              contiguous, prefetched pointer chasing, unpredictable

THE #1 MISTAKE: choosing from the Big-O alone. It counts operations and assumes uniform memory cost;
the real spread between cache and main memory is about a hundred to one.

THE #2 MISTAKE: believing LinkedList's middle insert is O(1). Only the rewiring is; finding the
position is O(n) of dependent cache misses, and the List interface gives you no way to skip it.

THE #3 MISTAKE: `remove(0)` in a loop. Accidental O(n²) and very common.

THE #4 MISTAKE: an iterator-remove loop on an ArrayList. O(n) per removal. Use `removeIf`.

THE #5 MISTAKE: LinkedList as a queue. `ArrayDeque` is better on every axis.

THE #6 MISTAKE: not pre-sizing a list whose size you know. About 25 reallocations to reach 100,000.

THE #7 MISTAKE: `ArrayList<Integer>` for large numeric data. A boxed object and a pointer dereference
per element — a bigger cost than the list choice.

THE #8 MISTAKE: `list.contains` in a loop. You wanted a `HashSet`, and no list choice will save it.

THE #9 MISTAKE: benchmarking at a thousand elements. Everything fits in cache and the effect you are
measuring does not exist yet.

THE #10 MISTAKE: treating `Arrays.asList` and `subList` as copies. They are VIEWS that alias the
original and throw on structural modification.

THE #11 MISTAKE: assuming a large list frees memory when emptied. `remove` never shrinks the array;
`trimToSize()` does.

ONE-SENTENCE TAKEAWAY: the textbook comparison is algorithmically correct and practically wrong,
because an ArrayList is ONE CONTIGUOUS BLOCK that the prefetcher can run ahead of and that
`System.arraycopy` shifts as a vectorised block move, while a LinkedList is a chain of 24-byte nodes
whose next address IS the data in the current one — a serialised chain of dependent cache misses at
roughly a hundred times the latency — so even the middle-insertion case LinkedList supposedly owns is
an O(n) walk in the worst currency attached to an O(1) rewire that costs nothing; default to
ArrayList, use ArrayDeque for queues, `removeIf` for bulk removal, a Set for membership and a primitive
array for numbers, and require a measured reason before choosing LinkedList.""",
]


DEEP["0.1 + 0.2 != 0.3 — floating point, and when to use BigDecimal"] = [
"""1. THE GOAL IN PLAIN ENGLISH — why the computer gets simple arithmetic wrong

    System.out.println(0.1 + 0.2);   →   0.30000000000000004

This is not a bug in Java. Every language using standard hardware floating point prints the same thing:
Python, JavaScript, C, Go, Rust. It is not imprecision in the addition either. THE ADDITION IS EXACTLY
CORRECT — it is the two inputs that are not the numbers you wrote.

    A `double` STORES A NUMBER IN BINARY, as a sum of halves, quarters, eighths, sixteenths. Some
    decimal fractions simply do not fit that form, no matter how many bits you allow.

    0.1 IS ONE TENTH. Ten is 2 × 5. The 5 is the problem: binary can only build fractions out of powers
    of two, so one fifth — and therefore one tenth — is a REPEATING binary fraction, exactly as one
    third is a repeating decimal fraction.

    SO WHEN YOU WRITE `0.1`, JAVA STORES THE NEAREST DOUBLE, which is
    0.1000000000000000055511151231257827021181583404541015625 — close, and not equal. Same for 0.2.
    Add those two exact values and you get something that is not the nearest double to 0.3. The result
    prints its true value, and it looks absurd.

    AND HERE IS WHY IT AMBUSHES PEOPLE RATHER THAN BEING OBVIOUS: `System.out.println(0.1)` prints
    "0.1". Java prints the SHORTEST decimal that would round-trip back to the same double. So the error
    is invisible in every single value, and becomes visible only when two of them are combined. The
    representation was wrong from the moment you typed the literal; the arithmetic just revealed it.

THE EVERYDAY VERSION: you write one third as 0.333. Correct to three places. Add three of them and you
get 0.999, not 1. Nothing went wrong in the addition — the *writing down* was lossy, and adding made
the loss visible. Binary has the same problem, just with a different set of unlucky fractions, and one
tenth happens to be one of them.

TERMS AS THEY APPEAR:
- IEEE 754: the standard every CPU implements for floating point.
- MANTISSA (significand): the digits. EXPONENT: where the point goes.
- PRECISION: how many significant digits survive. For a double, about 15–17 decimal digits.
- ULP: "unit in the last place" — the gap between one representable double and the next.""",

"""2. THE INTUITION — a sliding window of significant digits

A `double` IS 64 BITS: 1 sign, 11 exponent, 52 mantissa. Read it as scientific notation in base two —
a fixed number of significant BINARY digits, times two to some power.

    THE CONSEQUENCE THAT EXPLAINS EVERYTHING ELSE: YOU ALWAYS HAVE ABOUT 15–17 SIGNIFICANT DECIMAL
    DIGITS, AND THEY SLIDE. Near 1.0 the gap between representable values is about 2.2e-16. Near
    1,000,000 it is about 1.2e-10. Near 1e17 the gap is larger than 1, so CONSECUTIVE INTEGERS STOP
    BEING REPRESENTABLE.

    THAT LAST POINT IS A REAL PRODUCTION BUG AND NOT A CURIOSITY. Above 2^53 (about 9.007e15) a double
    cannot represent every integer. Put a 19-digit database ID or a nanosecond timestamp through a
    double — which happens the moment JSON is parsed by JavaScript, where every number IS a double —
    and it comes back changed. Two distinct IDs can become equal.

WHICH FRACTIONS ARE EXACT? Exactly those whose denominator is a power of two. 0.5, 0.25, 0.75, 0.125.
Everything else — 0.1, 0.2, 0.3, 1/3 — is stored as the nearest representable neighbour.

    SO SOME "IMPOSSIBLE" RESULTS ARE ACTUALLY CORRECT: `0.5 + 0.25 == 0.75` is true, exactly, always.
    The rule is not "floating point is random". It is "the inputs were rounded on the way in".

THE THREE WAYS ERROR ACTUALLY HURTS, in increasing order of nastiness:

    ROUNDING, once. Half an ulp per operation. Almost always harmless.

    ACCUMULATION. Add 0.1 to a running total ten million times and the errors compound. The result
    drifts visibly — this is the one that turns up in financial batch jobs and in physics simulations.

    CATASTROPHIC CANCELLATION, the dangerous one. Subtract two nearly-equal numbers and the leading
    digits — the ones that were CORRECT — cancel out, promoting the trailing error digits to the front.
    1.0000000001 minus 1.0 keeps almost no significant digits at all. A calculation that was accurate
    to fifteen digits can become accurate to two in a single subtraction, and NOTHING SIGNALS IT.

AND THE PROPERTY YOU LOSE THAT MATTERS MOST TO PROGRAMMERS: FLOATING-POINT ADDITION IS NOT ASSOCIATIVE.
`(a + b) + c` and `a + (b + c)` can differ. Which is why summing an array in parallel gives a different
answer from summing it sequentially, and why a "flaky" test comparing sums may be reporting something
real.""",

"""3. THE MECHANISM — the bits, the special values, and BigDecimal

THE LAYOUT of a double:

    ┌─┬───────────┬────────────────────────────────────────────────────┐
    │S│  exponent │                  mantissa (52 bits)                │
    └─┴───────────┴────────────────────────────────────────────────────┘
     1     11                            52

    value = (-1)^S × 1.mantissa × 2^(exponent - 1023)

    THE LEADING 1 IS IMPLIED and not stored, which buys one free bit of precision — and it is why
    zero, which has no leading 1, needs a special encoding, and why there are TWO of them.

THE SPECIAL VALUES, all of which are representable and none of which behave normally:

    +0.0 and -0.0   Equal by `==`, and DISTINGUISHABLE: 1/0.0 is +Infinity, 1/-0.0 is -Infinity.
                    `Double.compare(-0.0, 0.0)` is -1 while `-0.0 == 0.0` is true. This split is
                    why a TreeMap and a HashMap can disagree about a key.
    Infinity        Overflow does not throw; it saturates. `1.0/0.0` is Infinity, not an exception.
                    Integer division by zero throws; floating point does not.
    NaN             `0.0/0.0`. NOT EQUAL TO ITSELF: `Double.NaN == Double.NaN` is FALSE. But
                    `Double.valueOf(NaN).equals(Double.valueOf(NaN))` is TRUE, and
                    `Double.compare(NaN, NaN)` is 0 — because collections need a total order.
                    THREE DIFFERENT ANSWERS TO "ARE THESE EQUAL", all deliberate.
    SUBNORMALS      Very small values near zero, with reduced precision, and on some hardware
                    dramatically slower to compute with.

`float` IS 32 BITS — 24 bits of significand, about 7 decimal digits. It is almost never the right
choice on a modern CPU: doubles are the same speed, and float's precision runs out fast. Use it for
memory-bound bulk data (graphics, ML tensors), not for scalar arithmetic.

BIGDECIMAL is a completely different machine: an arbitrary-precision INTEGER (`unscaledValue`) plus an
`int scale`, where the value is unscaledValue × 10^-scale.

    IT IS BASE TEN, so 0.1 is exact. It has no fixed precision, so it grows as needed. And it is
    roughly a hundred times slower than a double, with an object allocation per operation.

    THREE THINGS ABOUT IT THAT CATCH EVERYONE:

    `new BigDecimal(0.1)` IS WRONG. It faithfully converts the ALREADY-WRONG double, giving
    0.1000000000000000055511151231257827021181583404541015625. Use `new BigDecimal("0.1")` or
    `BigDecimal.valueOf(0.1)` (which routes through `Double.toString`).

    `equals` COMPARES SCALE. `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` is FALSE. Use
    `compareTo(...) == 0`. This breaks HashSet and HashMap membership in a way that looks insane.

    DIVISION CAN THROW. `ONE.divide(new BigDecimal("3"))` throws ArithmeticException, because the exact
    result is non-terminating. You MUST supply a scale and a RoundingMode.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `if (a == b)` ON DOUBLES. Almost always wrong. Two paths to the same mathematical value can
produce different doubles.

CASE 2 — A FIXED EPSILON. `Math.abs(a - b) < 0.0001` is fine near 1.0 and meaningless near 1e12, where
the gap between ADJACENT doubles already exceeds it. Comparison must be RELATIVE to magnitude, or in
ulps.

CASE 3 — MONEY IN A DOUBLE. The single most expensive instance of this whole topic. 0.1 is not
representable, so cents drift, and a reconciliation report is off by a few pennies across a million
rows with no single wrong transaction to point at.

CASE 4 — ACCUMULATING IN A LOOP. Summing 0.1 ten million times drifts measurably. Kahan (compensated)
summation recovers most of it by tracking the lost low-order part explicitly.

CASE 5 — CATASTROPHIC CANCELLATION. Subtracting nearly-equal values destroys significant digits
silently. The classic instance is the naive variance formula `E[x²] - E[x]²`, which can even return a
NEGATIVE variance; use Welford's algorithm.

CASE 6 — INTEGERS ABOVE 2^53. Not all representable. IDs, nanosecond timestamps, and anything that
passed through JSON parsed by JavaScript. Two distinct IDs can compare equal.

CASE 7 — `NaN` IN A SORT. `NaN == NaN` is false, so a comparator written with `<` and `>` violates
its own contract and `Arrays.sort` can throw "Comparison method violates its general contract" — or
silently produce garbage. `Double.compare` handles it.

CASE 8 — `NaN` IN A COLLECTION. `list.contains(Double.NaN)` is TRUE, because `contains` uses `equals`,
not `==`. The opposite of the `==` result, and both are correct.

CASE 9 — `-0.0` AS A KEY. `HashMap` distinguishes it from `0.0` (different bits, different hash);
`==` does not. Two structures, two answers.

CASE 10 — OVERFLOW TO INFINITY, SILENTLY. No exception, and `Infinity - Infinity` is NaN, which then
propagates through every subsequent operation and poisons the whole result.

CASE 11 — `new BigDecimal(double)`. Preserves the error you switched to BigDecimal to escape.

CASE 12 — `BigDecimal.equals` VS `compareTo`. 2.0 and 2.00 are not `equals`. Sets and map keys behave
bizarrely as a result.

CASE 13 — `float` FOR ACCUMULATION. About 7 digits. A float running total is visibly wrong after a few
million additions.

CASE 14 — ASSUMING ASSOCIATIVITY. `(a+b)+c != a+(b+c)`, so a parallel sum and a sequential sum legally
differ. Reordering an expression can change the result.""",

"""5. THE ALTERNATIVES — pick by domain, not by taste

FOR MONEY, TWO CORRECT ANSWERS AND ONE WRONG ONE:

    `long` OF MINOR UNITS — cents, or hundredths of a cent. Exact, fast, and it is what most payment
    systems actually do. The costs are that you must track the currency's scale yourself and watch for
    overflow, and that division still needs an explicit rounding decision.
    `BigDecimal` with an EXPLICIT scale and RoundingMode. Exact in base ten, handles arbitrary
    precision, self-documenting. About 100x slower, which is irrelevant for transactions and relevant
    for a billion-row aggregation.
    `double` — WRONG. Not "risky": wrong. The values you need are not representable.

FOR SCIENTIFIC AND STATISTICAL WORK, `double` is right, and the discipline is in the algorithms:
    KAHAN / NEUMAIER SUMMATION for long sums.
    WELFORD'S ALGORITHM for variance, instead of `E[x²] - E[x]²`.
    `Math.fma(a, b, c)` — a fused multiply-add, computed with a single rounding instead of two.
    `Math.hypot(x, y)` instead of `sqrt(x*x + y*y)`, which overflows for large inputs.
    `Math.log1p(x)` and `Math.expm1(x)` near zero, where `log(1+x)` loses everything to cancellation.
    REORDER SUMS SMALLEST-FIRST when you can; it materially reduces accumulated error.

FOR COMPARISON:
    `Double.compare(a, b)` for a total order that handles NaN and -0.0 correctly. Use it in every
    comparator, always.
    RELATIVE tolerance: `Math.abs(a-b) <= eps * Math.max(Math.abs(a), Math.abs(b))`.
    ULP-based: `Math.ulp(x)` for a tolerance expressed in representable steps.

FOR EXACT RATIONALS — `BigInteger` numerator and denominator, or `BigFraction` from Apache Commons
Numbers. Exact for everything expressible as a ratio, and the denominators grow without bound.

FOR REPRODUCIBILITY ACROSS PLATFORMS — `strictfp`, which forced strict IEEE semantics. As of Java 17 it
is the DEFAULT and the keyword is a no-op, because the x87 hardware quirk it existed for is gone.

WHAT TO SAY: "Doubles for measurement, `long` of minor units or BigDecimal for money, and `Double.compare`
in every comparator. And I would ask what the number MEANS before choosing — 'money' and 'a sensor
reading' want opposite answers, and the mistake is treating them the same."

""",

"""6. HOW TO WORK WITH FLOATING POINT — numbered steps

STEP 1 — ASK WHAT THE NUMBER IS. A measurement, or a COUNT of exact units? Money, invoice quantities
and share counts are counts and belong in `long` or BigDecimal. Temperatures, weights and durations are
measurements and belong in `double`.

STEP 2 — NEVER USE `==` ON DOUBLES. Compare with a tolerance, and make the tolerance RELATIVE to
magnitude.

STEP 3 — USE `Double.compare` IN EVERY COMPARATOR. It gives a total order over NaN and -0.0; hand-rolled
`<`/`>` comparators violate their contract and `Arrays.sort` will eventually tell you so.

STEP 4 — FOR MONEY, DECIDE THE UNIT ONCE AND WRITE IT DOWN. Minor units in a `long`, or BigDecimal with
a fixed scale. Never mix representations across a boundary.

STEP 5 — CONSTRUCT BIGDECIMAL FROM A STRING. `new BigDecimal("0.1")`, or `BigDecimal.valueOf(x)`. Never
`new BigDecimal(0.1)`.

STEP 6 — ALWAYS GIVE `divide` A SCALE AND A RoundingMode. Otherwise it throws on any non-terminating
result, usually in production, usually on a divide by three.

STEP 7 — COMPARE BIGDECIMALS WITH `compareTo(...) == 0`. `equals` includes the scale, so 2.0 and 2.00
are not equal and set membership behaves absurdly.

STEP 8 — FOR LONG SUMS, USE COMPENSATED SUMMATION or sum smallest-first. Naive accumulation drifts.

STEP 9 — WATCH FOR SUBTRACTION OF NEARLY-EQUAL VALUES. That is where accuracy dies, and nothing warns.
Look for a mathematically equivalent formula that avoids it.

STEP 10 — CHECK FOR OVERFLOW AND NaN AT BOUNDARIES. They propagate silently through everything
downstream. `Double.isFinite` at the edges of a computation.

STEP 11 — KEEP LARGE IDS OUT OF DOUBLES. Above 2^53 not every integer exists. Serialise them as
strings, especially across JSON.

STEP 12 — WHEN A TEST IS FLAKY ON A SUM, SUSPECT ORDERING BEFORE SUSPECTING THE TEST. Addition is not
associative; a parallel sum legitimately differs from a sequential one.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'0.1 + 0.2 gives 0.30000000000000004, and it's not a Java bug — every language on standard hardware
prints that. And the addition isn't imprecise either. The addition is exactly correct. It's the two
INPUTS that aren't the numbers I wrote.

A double stores a number in binary — as a sum of halves, quarters, eighths. One tenth is 1/10, and 10
is 2 times 5. The 5 is the problem: binary can only build fractions from powers of two, so one tenth is
a repeating binary fraction, exactly the way one third is a repeating decimal. So when I write 0.1,
what gets stored is the nearest double, which is 0.1000000000000000055 and change.

The reason it ambushes people rather than being obvious is that println(0.1) prints "0.1". Java prints
the shortest decimal that round-trips back to the same double, so the error is invisible in every
individual value and only shows up when you combine two. The representation was already wrong when I
typed the literal — the arithmetic just revealed it.

The way I'd frame the whole topic: a double gives you about 15 to 17 significant decimal digits, and
they SLIDE with magnitude. Near 1.0 the gap between representable values is about 2e-16. Near 1e17 the
gap is bigger than 1 — so consecutive integers stop existing. That's a real production bug, not a
curiosity: above 2^53 you can't represent every integer, so a 19-digit database ID or a nanosecond
timestamp through a double comes back changed. Two distinct IDs can become equal. It happens every time
JSON gets parsed by JavaScript, where every number IS a double.

Error hurts in three escalating ways. Rounding once, half an ulp, harmless. Accumulation — add 0.1 ten
million times and it visibly drifts. And the dangerous one, catastrophic cancellation: subtract two
nearly-equal numbers and the leading digits, the CORRECT ones, cancel, which promotes the trailing
error digits to the front. A calculation accurate to fifteen digits can drop to two in one subtraction,
and nothing signals it. The classic case is the naive variance formula, E[x²] minus E[x]², which can
return a negative variance.

Also worth knowing: floating-point addition is not ASSOCIATIVE. (a+b)+c can differ from a+(b+c). Which
is why a parallel sum and a sequential sum legitimately disagree, and why a flaky test on a sum might
be telling you something real.

Practically, I'd decide by asking what the number IS. A measurement, or a count of exact units? Money
is a count — it belongs in a long of minor units, or BigDecimal with an explicit scale and RoundingMode.
Not a double; that's not risky, it's wrong, because the values aren't representable. Measurements
belong in doubles, and then the discipline is in the algorithms — Kahan summation, Welford for
variance, hypot instead of sqrt of squares.

And two BigDecimal traps: `new BigDecimal(0.1)` faithfully preserves the wrong double, so always
construct from a string. And `equals` compares SCALE, so 2.0 and 2.00 aren't equal and set membership
goes strange — use compareTo == 0.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT IS ACTUALLY STORED ─────────────────────────────────────────
    System.out.println(0.1);
    // prints: 0.1
    // ^ A LIE OF OMISSION. Java prints the SHORTEST decimal that round-trips
    //   back to this double, which is why the error is invisible per-value.
    System.out.println(new BigDecimal(0.1));
    // prints: 0.1000000000000000055511151231257827021181583404541015625
    // ^ THE TRUTH. new BigDecimal(double) converts the double faithfully, so it
    //   is the wrong constructor for input AND the perfect one for inspection.

    System.out.println(0.1 + 0.2);        // 0.30000000000000004
    System.out.println(0.1 + 0.2 == 0.3); // false
    System.out.println(0.5 + 0.25 == 0.75); // TRUE — denominators are powers of 2

    // ── THE COMPARISON THAT IS ALSO WRONG ───────────────────────────────
    if (Math.abs(a - b) < 0.0001) { ... }
    //                     ^^^^^^ fine near 1.0. MEANINGLESS near 1e12, where the
    //   gap between ADJACENT doubles already exceeds it — so this is always true.
    if (Math.abs(a - b) <= 1e-9 * Math.max(Math.abs(a), Math.abs(b))) { ... }
    //                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ RELATIVE to
    //   magnitude. Scales correctly across the whole range.

    // ── ABOVE 2^53, INTEGERS STOP EXISTING ──────────────────────────────
    long id = 9007199254740993L;          // 2^53 + 1
    System.out.println((long)(double) id);// 9007199254740992  ← CHANGED
    // ^ The double simply has no bit pattern for that integer. This is why IDs
    //   must be serialised as STRINGS in JSON: JavaScript numbers ARE doubles.

    // ── CATASTROPHIC CANCELLATION: 15 digits down to 2 ──────────────────
    double a = 1.0000000001, b = 1.0;
    System.out.println(a - b);            // 1.000000082740371E-10
    // ^ The correct answer is 1e-10. We kept about TWO significant digits, because
    //   the leading digits — the accurate ones — cancelled, promoting the error.
    //   Nothing warned. This is how a good calculation quietly becomes a bad one.

    // ── ACCUMULATION, AND THE FIX ───────────────────────────────────────
    double sum = 0;
    for (int i = 0; i < 10_000_000; i++) sum += 0.1;
    // sum ≈ 999999.9998389754, not 1000000.0
    double s = 0, c = 0;                  // Kahan: track the lost low-order part
    for (int i = 0; i < 10_000_000; i++) {
        double y = 0.1 - c, t = s + y;
        c = (t - s) - y;                  // ← what the addition DROPPED
        s = t;
    }                                     // s is correct to the last digit

    // ── NaN: THREE ANSWERS TO ONE QUESTION, ALL CORRECT ─────────────────
    double n = 0.0 / 0.0;
    System.out.println(n == n);                       // false — IEEE 754 says so
    System.out.println(Double.valueOf(n).equals(n));  // true  — collections need
    System.out.println(Double.compare(n, n));         // 0     — a total order
    System.out.println(List.of(n).contains(n));       // TRUE — contains uses equals

    // ── MONEY ───────────────────────────────────────────────────────────
    // double  total = 0.1 + 0.2;                     ← WRONG. Not risky. Wrong.
    long cents = 10 + 20;                             // exact, fast, what payment
    //                                                   systems actually do
    var big = new BigDecimal("0.1").add(new BigDecimal("0.2"));  // exactly 0.3
    // new BigDecimal(0.1)  ← keeps the error you switched to BigDecimal to escape
    new BigDecimal("2.0").equals(new BigDecimal("2.00"));   // FALSE — scale differs
    new BigDecimal("2.0").compareTo(new BigDecimal("2.00")); // 0 — use THIS
    BigDecimal.ONE.divide(new BigDecimal("3"));       // THROWS ArithmeticException
    BigDecimal.ONE.divide(new BigDecimal("3"), 10, RoundingMode.HALF_UP);  // fine""",

"""9. THE TRACE — following 0.1 + 0.2 through the hardware

STEP 1 — THE LITERAL `0.1` IS PARSED. The compiler finds the nearest double to one tenth:

    exact value wanted:  0.1
    nearest double:      0.1000000000000000055511151231257827021181583404541015625
    error introduced:    +5.55e-18            ← ALREADY WRONG, BEFORE ANY ARITHMETIC

STEP 2 — THE LITERAL `0.2` IS PARSED:

    nearest double:      0.200000000000000011102230246251565404236316680908203125
    error introduced:    +1.11e-17

STEP 3 — THE ADDITION. The CPU adds the two stored values EXACTLY, then rounds the exact sum to the
nearest double:

    exact sum of the two stored values:  0.3000000000000000166533453693773481063544750213623046875
    nearest double to that:              0.3000000000000000444089209850062616169452667236328125
    the double nearest to 0.3:           0.299999999999999988897769753748434595763683319091796875

    THE TWO ARE DIFFERENT DOUBLES. So `==` is false, correctly.

STEP 4 — PRINTING. `Double.toString` emits the shortest decimal that round-trips:

    for 0.1 alone       → "0.1"                    ← the error is HIDDEN
    for the sum         → "0.30000000000000004"    ← the error is now large enough
                                                      that "0.3" would round-trip to
                                                      a DIFFERENT double, so it must
                                                      be shown

    THAT IS THE WHOLE MYSTERY. Nothing changed about how wrong the values were. The printer simply
    stopped being able to hide it. Every double you have ever printed had this error; you only see it
    when it crosses the round-trip threshold.

NOW ACCUMULATION — adding 0.1 ten million times:

    additions        running sum                     absolute error
    ---------------------------------------------------------------------------------
    10               0.9999999999999999              1.1e-16
    1,000            99.9999999999986                1.4e-12
    1,000,000        100000.00000133288              1.3e-6
    10,000,000       999999.9998389754               1.6e-4      ← visible in a report

    THE ERROR GROWS FASTER THAN THE NUMBER OF ADDITIONS, because each partial sum is larger, so each
    rounding is coarser — an ulp near 100,000 is much bigger than an ulp near 1. Kahan summation
    tracks the dropped low-order part explicitly and recovers essentially all of it.

AND CANCELLATION — the failure that produces no symptom at all:

    operation                        significant digits remaining
    ---------------------------------------------------------------------------------
    a = 1.0000000001                 ~16, correct
    b = 1.0                          exact
    a - b                            ~2 correct digits out of 16
    (a - b) * 1e10                   still ~2 — the loss is PERMANENT

    NOTHING THREW. NOTHING WARNED. The subtraction was performed exactly as specified; it is the
    INFORMATION that was lost, and no runtime check can detect that. This is the reason numerical code
    is rewritten around cancellation — `log1p`, `expm1`, `hypot`, Welford — rather than checked for it.

WHAT PRODUCED WHAT:
    BINARY FRACTIONS         produced steps 1 and 2 — the error exists before any arithmetic runs.
    ROUND-TO-NEAREST         produced step 3, which is the only step that is genuinely "the hardware".
    SHORTEST ROUND-TRIP      produced step 4, and therefore produced the surprise.
    SLIDING PRECISION        produced the accumulation table: the same operation costs more as the
                             magnitude grows.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    double: 64 bits, 52-bit mantissa, ~15–17 significant decimal digits, range ~±1.8e308.
    float:  32 bits, 23-bit mantissa, ~7 digits. Rarely the right scalar choice.
    Exactly representable: fractions whose denominator is a power of two. 0.5, 0.25, 0.125.
    Every integer up to 2^53 (~9.007e15) is exact; above that, they are not.
    ULP near 1.0: ~2.2e-16. Near 1e6: ~1.2e-10. Near 1e17: greater than 1.
    BigDecimal: exact in base ten, arbitrary precision, roughly 100x slower with an allocation per
    operation.
    Arithmetic is COMMUTATIVE but NOT ASSOCIATIVE and NOT DISTRIBUTIVE.

THE #1 MISTAKE: `==` on doubles. Use a RELATIVE tolerance, or `Double.compare` for ordering.

THE #2 MISTAKE: money in a double. Not risky — wrong. `long` of minor units, or BigDecimal.

THE #3 MISTAKE: a FIXED epsilon. Meaningless once the magnitude exceeds it; comparison must scale.

THE #4 MISTAKE: `new BigDecimal(0.1)`. Faithfully preserves the error you were escaping. Use the String
constructor or `BigDecimal.valueOf`.

THE #5 MISTAKE: `BigDecimal.equals` for value comparison. It includes SCALE, so 2.0 and 2.00 differ and
set membership behaves absurdly. `compareTo(...) == 0`.

THE #6 MISTAKE: `divide` with no scale and RoundingMode. Throws on any non-terminating result.

THE #7 MISTAKE: hand-rolled `<`/`>` comparators on doubles. They violate the comparator contract on
NaN, and `Arrays.sort` will eventually say so out loud.

THE #8 MISTAKE: large IDs through a double. Above 2^53 not every integer exists; two distinct IDs can
become equal. Serialise as strings.

THE #9 MISTAKE: naive accumulation over millions of values. Use compensated summation, or sum
smallest-first.

THE #10 MISTAKE: subtracting nearly-equal values without noticing. Catastrophic cancellation destroys
significant digits with no signal whatsoever.

THE #11 MISTAKE: assuming overflow throws. It saturates to Infinity, `Infinity - Infinity` is NaN, and
the NaN then poisons everything downstream in silence.

THE #12 MISTAKE: assuming associativity. A parallel sum and a sequential sum legally differ, so this
can present as a flaky test that is actually reporting something true.

ONE-SENTENCE TAKEAWAY: a double stores binary fractions, so any decimal whose denominator is not a
power of two — 0.1 included — is rounded THE MOMENT YOU TYPE THE LITERAL, and `Double.toString` hides
that by printing the shortest round-tripping decimal until an addition makes it too large to hide;
the practical consequences are that `==` is unusable, that a fixed epsilon is wrong at scale, that
integers above 2^53 do not all exist, that long accumulations drift and near-equal subtractions destroy
accuracy with no signal at all, and that money — being a COUNT of exact units rather than a measurement
— belongs in a `long` of minor units or a BigDecimal built from a String and compared with `compareTo`,
never in a double.""",
]


DEEP["ExecutorService — the four ways a thread pool bites you"] = [
"""1. THE GOAL IN PLAIN ENGLISH — why nobody writes `new Thread()` anymore

Creating a thread is a system call. The OS allocates a stack, registers a scheduling entity, and hands
it back. It costs on the order of a hundred microseconds and about a megabyte of reserved address
space. Do it per request and two things happen: you pay that cost on every request, and — far worse —
NOTHING BOUNDS HOW MANY EXIST. A traffic spike creates ten thousand threads, the machine spends all its
time context-switching, and the failure looks like the machine died rather than like you were busy.

    AN ExecutorService IS A FIXED CREW PLUS A QUEUE. You hand it tasks; a bounded set of threads takes
    them one at a time; and when they are all busy, the work WAITS instead of spawning more workers.

    THE QUEUE IS THE POINT, NOT THE THREADS. Reusing threads saves creation cost, which is nice. But
    the reason a pool exists is that it gives you a place to put excess work and a decision about what
    to do when that place is full. THAT DECISION IS YOUR OVERLOAD BEHAVIOUR, and most outages involving
    thread pools are really outages of that decision being made by default.

THE EVERYDAY VERSION: a coffee shop with four baristas. When fifty people arrive, you do not hire
forty-six baristas — you form a queue. And the interesting design question is not how fast the baristas
work; it is what happens when the queue reaches the door. Do you let it grow into the street? Turn
people away? Ask the person at the till to make their own coffee? EVERY ONE OF THOSE IS A CONFIGURED
POLICY, and picking none means picking one by accident.

TERMS AS THEY APPEAR:
- CORE POOL SIZE: threads kept alive even when idle.
- MAXIMUM POOL SIZE: the ceiling — but see section 2, because it does not mean what you think.
- WORK QUEUE: where tasks wait.
- REJECTION POLICY: what happens when the queue is full AND the pool is at maximum.
- `execute` vs `submit`: the difference decides whether your exceptions are visible or invisible.""",

"""2. THE INTUITION — the sizing rule that surprises everyone

`ThreadPoolExecutor` HAS SEVEN CONSTRUCTOR PARAMETERS, and the interaction between three of them is the
thing to actually understand:

    corePoolSize, maximumPoolSize, keepAliveTime, unit, workQueue, threadFactory, rejectionHandler

THE ALGORITHM WHEN A TASK ARRIVES, in this exact order:

    1. FEWER THAN corePoolSize THREADS?  → create a new thread. Even if others are idle.
    2. OTHERWISE, TRY TO QUEUE IT.        → if the queue accepts it, done.
    3. QUEUE FULL?                        → create a thread, up to maximumPoolSize.
    4. AT MAXIMUM TOO?                    → REJECT, via the rejection policy.

    NOW READ STEP 2 AND STEP 3 TOGETHER. THREADS BEYOND THE CORE ARE ONLY CREATED WHEN THE QUEUE IS
    FULL. Which means:

    WITH AN UNBOUNDED QUEUE, maximumPoolSize IS NEVER REACHED. Never. The queue never fills, so step 3
    never happens, so the pool never grows past core. You can set maximum to a thousand and it is
    decoration.

    THIS IS EXACTLY WHAT `Executors.newFixedThreadPool(n)` DOES. It uses a `LinkedBlockingQueue` with
    no capacity limit. So under sustained overload the pool does not grow, does not reject, and does
    not fail — IT QUEUES, FOREVER, until the heap is gone. The OutOfMemoryError names the queue, and
    the actual cause was that the system had no way to say "no".

    AND `Executors.newCachedThreadPool()` FAILS THE OPPOSITE WAY: a `SynchronousQueue`, which has zero
    capacity, so step 2 always fails and step 3 always fires — with a maximum of `Integer.MAX_VALUE`.
    Unbounded THREADS instead of an unbounded queue.

    BOTH CONVENIENCE FACTORIES ARE UNBOUNDED IN ONE DIRECTION. That is why serious codebases construct
    `ThreadPoolExecutor` explicitly, and why Google's Java style guide bans the `Executors` factories
    outright.

HOW MANY THREADS, then? Two regimes, and confusing them is the second most common mistake:

    CPU-BOUND WORK: threads ≈ number of cores. More threads do not create more cores; they add context
    switching and cache pressure to the same amount of work.
    I/O-BOUND WORK: threads ≈ cores × (1 + waitTime/computeTime). A task that waits 90% of the time
    supports about ten threads per core. THE RATIO IS THE THING TO MEASURE, and it is usually easier to
    measure than people expect: it is just the fraction of time the thread is not runnable.

AND THE REJECTION POLICY IS YOUR BACKPRESSURE DESIGN:

    AbortPolicy (default)  throws RejectedExecutionException. Honest, and requires the caller to cope.
    CallerRunsPolicy       THE CALLING THREAD RUNS THE TASK ITSELF. Which means the producer stops
                           producing while it does so. This is elegant: overload automatically slows
                           the source, with no signalling protocol at all.
    DiscardPolicy          silently drops. Right for metrics samples, catastrophic for orders.
    DiscardOldestPolicy    drops the oldest queued task. Right for "latest value wins" feeds.""",

"""3. THE MECHANISM — execute vs submit, shutdown, and the scheduled trap

THE EXCEPTION DIFFERENCE, which is the single most under-known thing here:

    execute(Runnable)          an uncaught exception KILLS THE THREAD, the pool quietly replaces it,
                               and the exception goes to the thread's UncaughtExceptionHandler — which
                               by default prints to stderr. VISIBLE, if anyone is reading stderr.
    submit(Runnable|Callable)  the exception is CAUGHT AND STORED IN THE Future. Nothing is printed.
                               Nothing is logged. The thread survives. IF YOU NEVER CALL `get()`, THE
                               EXCEPTION SIMPLY DOES NOT EXIST as far as your system is concerned.

    THAT IS WHY WORK "SILENTLY STOPS HAPPENING". Everyone writes `submit`, nobody keeps the Future, and
    every failure is swallowed by design. THE FIX IS A try/catch AROUND THE WHOLE TASK BODY, or a
    subclass overriding `afterExecute`, or `CompletableFuture` with `whenComplete`.

SHUTDOWN, and the three methods that get confused:

    shutdown()               stop accepting new tasks; finish everything already submitted. Returns
                             IMMEDIATELY — it does not wait.
    shutdownNow()            stop accepting, INTERRUPT running threads, and RETURN the queued tasks
                             that never started. Interruption only works if the task checks for it.
    awaitTermination(t, u)   the actual wait. Returns false on timeout.
    THE CORRECT SEQUENCE IS ALL THREE: shutdown, await, and if that times out, shutdownNow and await
    again.

    AND THE DEFAULT THREADS ARE NON-DAEMON, so a pool you forget to shut down KEEPS THE JVM ALIVE. The
    program finishes `main` and simply does not exit. On Java 19+, `ExecutorService` is `AutoCloseable`,
    so try-with-resources does the whole dance for you.

THE SCHEDULED-EXECUTOR TRAP, which deserves its own paragraph because it is silent and total:

    IF A TASK SUBMITTED TO `scheduleAtFixedRate` THROWS, THE SCHEDULE IS CANCELLED. Not skipped — 
    CANCELLED. It never runs again, for the life of the process, and nothing is logged. A health check,
    a cache refresh, a metrics flush: one transient exception at 3am and the job is dead until the next
    deploy. ALWAYS WRAP A SCHEDULED TASK BODY IN try/catch(Throwable).

    `scheduleAtFixedRate` vs `scheduleWithFixedDelay`: the first measures from START to start, so if a
    run takes longer than the period, runs bunch up back to back. The second measures from END to
    start, so there is always a real gap. FOR ANYTHING THAT TALKS TO A STRUGGLING DOWNSTREAM SERVICE,
    fixed DELAY is the safer default.

THREAD FACTORY. Default thread names are `pool-1-thread-3`, which tells you nothing in a thread dump at
2am. A three-line factory that names threads after their purpose is the cheapest observability
improvement available in Java.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `newFixedThreadPool` UNDER SUSTAINED OVERLOAD. Unbounded queue, so it never rejects; the heap
fills with queued Runnables and the OOM names the queue rather than the cause.

CASE 2 — `newCachedThreadPool` UNDER SUSTAINED OVERLOAD. Unbounded threads. Same outcome by the
opposite route.

CASE 3 — MAXIMUM POOL SIZE THAT DOES NOTHING. Any unbounded queue makes it unreachable. People set it,
watch it never be used, and conclude the pool is broken.

CASE 4 — `submit` WITH AN IGNORED FUTURE. Every exception silently captured. The task stops working and
nothing anywhere records it.

CASE 5 — A THROWING TASK ON `scheduleAtFixedRate`. The schedule is cancelled permanently and silently.

CASE 6 — FORGETTING TO SHUT DOWN. Non-daemon threads keep the JVM alive; the process hangs after `main`
returns with no error at all.

CASE 7 — THREAD-POOL DEADLOCK. A task submits another task to the SAME bounded pool and blocks on its
`Future.get()`. With a single-threaded pool this deadlocks on the first try, guaranteed. With a
ten-thread pool it deadlocks under load, which is worse because it passes testing.

CASE 8 — BLOCKING WORK ON THE COMMON ForkJoinPool. Parallel streams and no-executor `CompletableFuture`
calls share `ForkJoinPool.commonPool()`, sized to cores minus one. One blocking call there stalls
unrelated code across the whole JVM.

CASE 9 — ThreadLocal LEAKS IN A POOLED THREAD. The thread never dies, so the value is never cleared,
and it holds whatever it references forever. Always `remove()` in a finally.

CASE 10 — INTERRUPTION SWALLOWED. `catch (InterruptedException e) { }` destroys the interrupt flag, so
`shutdownNow` cannot stop the task. Either rethrow, or restore with
`Thread.currentThread().interrupt()`.

CASE 11 — `invokeAll` BLOCKS UNTIL EVERY TASK COMPLETES, including the slow one. There is a timeout
overload and it is nearly always the one you want.

CASE 12 — DEFAULT THREAD NAMES. `pool-2-thread-7` in a thread dump identifies nothing.

CASE 13 — ONE POOL FOR EVERYTHING. Slow database calls and fast cache lookups sharing a pool means the
slow work starves the fast work. Separate pools are BULKHEADS, and they are how you stop one dependency
from taking down every endpoint.""",

"""5. THE ALTERNATIVES — and which pool for which job

CONSTRUCT `ThreadPoolExecutor` DIRECTLY. The recommended default, because it forces you to state the
queue bound and the rejection policy — which are the two decisions that matter and the two the
convenience factories make for you badly:

    new ThreadPoolExecutor(8, 8, 0L, MILLISECONDS,
        new ArrayBlockingQueue<>(1000),          // BOUNDED. This is the whole point.
        namedFactory("http-worker"),
        new ThreadPoolExecutor.CallerRunsPolicy())

`Executors` FACTORIES — know what each really is:
    newFixedThreadPool(n)          fixed threads, UNBOUNDED queue
    newCachedThreadPool()          UNBOUNDED threads, zero-capacity queue, 60s idle timeout
    newSingleThreadExecutor()      one thread, unbounded queue — genuinely useful for serialising
                                   access to something non-thread-safe
    newScheduledThreadPool(n)      timers, with the cancel-on-throw trap above
    newWorkStealingPool()          a ForkJoinPool. Good for recursive divide-and-conquer, not for
                                   independent blocking I/O
    newVirtualThreadPerTaskExecutor()  Java 21. Not a pool at all — see below.

VIRTUAL THREADS (Java 21) for I/O-BOUND work. They change the answer to this whole topic: threads
become cheap, so you stop pooling. BUT THE POOL WAS ALSO YOUR RATE LIMITER — that `ArrayBlockingQueue`
of 1000 and those 8 threads were bounding how much load reached your database. Replace them with
unbounded virtual threads and you must add a `Semaphore` explicitly, or the limit simply disappears.

`CompletableFuture` FOR COMPOSITION — chaining, combining, timeouts, error recovery. ALWAYS PASS AN
EXECUTOR; the no-executor overloads use the common pool.

FORKJOINPOOL for recursive splitting, where work-stealing genuinely helps. Not for independent blocking
tasks.

A MESSAGE QUEUE — Kafka, SQS, RabbitMQ — when the work must survive a restart. An in-memory queue is a
thread pool's queue; a broker's queue is durable, observable, and rate-limitable from outside the
process. THE MOMENT "we lost the queued work when the pod restarted" MATTERS, you wanted a broker.

A SEMAPHORE, when what you actually need is a CONCURRENCY LIMIT rather than a set of threads. Often
clearer than a pool, and it composes with virtual threads.

WHAT TO SAY: "I would construct ThreadPoolExecutor explicitly with a bounded queue and CallerRunsPolicy
so overload becomes backpressure rather than an OOM, size it from the wait-to-compute ratio, name the
threads, and use separate pools as bulkheads so a slow dependency cannot starve a fast one."

""",

"""6. HOW TO CONFIGURE A POOL — numbered steps

STEP 1 — CLASSIFY THE WORK. CPU-bound or I/O-bound? The sizing rules are completely different and
everything else follows from this.

STEP 2 — SIZE IT. CPU-bound: about the core count. I/O-bound: cores × (1 + wait/compute). Measure the
ratio rather than guessing it.

STEP 3 — BOUND THE QUEUE. Always. An unbounded queue converts overload into an OutOfMemoryError, and it
removes maximumPoolSize from the design at the same time.

STEP 4 — CHOOSE THE REJECTION POLICY DELIBERATELY. `CallerRunsPolicy` for natural backpressure,
`AbortPolicy` when the caller can shed load properly, `DiscardOldest` for latest-value-wins feeds.

STEP 5 — NAME THE THREADS. A three-line ThreadFactory, and every future thread dump becomes readable.

STEP 6 — WRAP EVERY TASK BODY IN try/catch(Throwable). Especially scheduled tasks, where an exception
cancels the schedule forever.

STEP 7 — DO NOT IGNORE FUTURES FROM `submit`. Either handle them, or use `execute`, or use
`CompletableFuture` with `whenComplete`.

STEP 8 — SHUT DOWN PROPERLY: `shutdown`, `awaitTermination`, then `shutdownNow` and await again. Or
try-with-resources on Java 19+.

STEP 9 — USE SEPARATE POOLS AS BULKHEADS. One per downstream dependency, so a slow one cannot starve
the rest.

STEP 10 — NEVER BLOCK ON A TASK IN THE SAME BOUNDED POOL. That is the thread-pool deadlock, and it
passes testing before it fails in production.

STEP 11 — CLEAR ThreadLocals IN A FINALLY. Pooled threads never die, so nothing else will.

STEP 12 — MONITOR QUEUE DEPTH, ACTIVE COUNT AND REJECTION COUNT. `ThreadPoolExecutor` exposes all
three. Queue depth trending upward is the earliest warning you will get, and it arrives long before
latency moves.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Creating a thread is a syscall — about a megabyte of reserved stack and a hundred microseconds. Doing
it per request costs that every time, and worse, nothing bounds how many exist. A spike creates ten
thousand threads and the machine spends all its time context-switching, so the failure looks like the
box died rather than like you were busy.

A pool is a fixed crew plus a queue. But I'd say the QUEUE is the point, not the threads. Reusing
threads saves creation cost, which is nice. The reason a pool exists is that it gives you somewhere to
put excess work and a decision about what to do when that place is full — and that decision IS your
overload behaviour. Most thread-pool outages are really that decision being made by default.

The thing that surprises everyone is the sizing algorithm. When a task arrives: under core size, make
a thread. Otherwise try to QUEUE it. Only if the queue is FULL do you create threads up to the maximum.
Read those together and it follows that with an unbounded queue, maximumPoolSize is never reached. Ever.
You can set it to a thousand and it's decoration.

Which is exactly what newFixedThreadPool does — a LinkedBlockingQueue with no capacity. So under
sustained overload it doesn't grow, doesn't reject, doesn't fail. It queues until the heap is gone, and
the OOM names the queue while the actual cause was that the system had no way to say no. And
newCachedThreadPool fails the opposite way: a zero-capacity SynchronousQueue with a maximum of
Integer.MAX_VALUE, so unbounded THREADS instead of an unbounded queue. Both convenience factories are
unbounded in one direction, which is why I'd construct ThreadPoolExecutor explicitly.

For sizing: CPU-bound is roughly the core count — more threads don't create more cores. I/O-bound is
cores times one plus the wait-to-compute ratio, so a task waiting 90% of the time supports about ten
threads per core.

And the rejection policy is where the backpressure design lives. CallerRunsPolicy is the elegant one:
the CALLING thread runs the task itself, so the producer stops producing while it does. Overload
automatically slows the source with no signalling protocol at all.

Two things I'd flag that bite people constantly. First, submit versus execute: submit CAPTURES the
exception in the Future. Nothing is printed, nothing is logged, and if you never call get() the
exception effectively doesn't exist. That's why work "silently stops happening" — everyone writes
submit and nobody keeps the Future.

Second, scheduleAtFixedRate: if the task throws, the schedule is CANCELLED. Not skipped — cancelled
permanently, silently, for the life of the process. One transient exception at 3am and your cache
refresh is dead until the next deploy. Always wrap a scheduled body in catch Throwable.

Then: bound the queue, name the threads so a thread dump is readable, use separate pools as bulkheads
so a slow dependency can't starve a fast one, and never block on a Future from the same bounded pool —
that one deadlocks under load after passing every test.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHY maximumPoolSize IS OFTEN DECORATION ─────────────────────────
    new ThreadPoolExecutor(2, 100, 60L, SECONDS, new LinkedBlockingQueue<>());
    //                        ^^^ NEVER REACHED. The queue is unbounded, so it always
    //   accepts, so the "queue is full" branch that creates threads 3..100 never runs.
    //   This is a 2-thread pool with a 100 written on it.

    Executors.newFixedThreadPool(8);
    // ^ EXACTLY THE ABOVE. LinkedBlockingQueue with no capacity. Under sustained
    //   overload: no growth, no rejection, no failure — it queues until the heap is
    //   gone, and the OOM stack trace names the queue rather than the cause.

    Executors.newCachedThreadPool();
    // ^ SynchronousQueue (capacity ZERO) + maximumPoolSize = Integer.MAX_VALUE.
    //   Every task fails to queue, so every task creates a thread. Unbounded THREADS.

    // ── THE POOL YOU SHOULD ACTUALLY WRITE ──────────────────────────────
    var pool = new ThreadPoolExecutor(
        8, 8,                              // core == max: predictable
        0L, TimeUnit.MILLISECONDS,
        new ArrayBlockingQueue<>(1000),    // ← BOUNDED. The single most important line.
        r -> { var t = new Thread(r, "http-worker"); t.setDaemon(true); return t; },
    //       ^^^^^^^^^^^^^^^^^^^^^^^^^ named threads. Three lines, and every future
    //       thread dump becomes readable at 2am.
        new ThreadPoolExecutor.CallerRunsPolicy());
    //      ^^^^^^^^^^^^^^^^^ THE CALLER RUNS IT. So the producer stops producing while
    //      it does. Overload throttles the source automatically — backpressure with no
    //      signalling protocol.

    // ── THE EXCEPTION THAT DOES NOT EXIST ───────────────────────────────
    pool.submit(() -> { throw new IllegalStateException("boom"); });
    //   ^^^^^^ CAUGHT AND STORED IN THE Future. Nothing printed, nothing logged, the
    //   thread survives. If nobody calls get(), this failure never happened.
    pool.execute(() -> { throw new IllegalStateException("boom"); });
    //   ^^^^^^^ goes to the thread's UncaughtExceptionHandler → stderr. VISIBLE.
    pool.submit(() -> { try { work(); } catch (Throwable t) { log.error("task", t); } });
    //                  ^^^ the actual fix: catch inside the task, always.

    // ── THE SCHEDULE THAT DIES SILENTLY ─────────────────────────────────
    sched.scheduleAtFixedRate(this::refreshCache, 0, 1, MINUTES);
    // ^ ONE exception → the schedule is CANCELLED. Permanently. Silently. The cache
    //   is stale until the next deploy and no log line marks the moment it stopped.
    sched.scheduleAtFixedRate(() -> {
        try { refreshCache(); } catch (Throwable t) { log.error("refresh", t); }
    }, 0, 1, MINUTES);                      // ← mandatory, not defensive

    // ── THE DEADLOCK THAT PASSES TESTING ────────────────────────────────
    var single = Executors.newSingleThreadExecutor();
    single.submit(() -> {
        var inner = single.submit(() -> 42);
        return inner.get();          // ← the only thread is BLOCKED waiting for a task
    });                              //   that needs the only thread. Deadlock, always.
    // With 10 threads this deadlocks only under load — which is worse, because it ships.

    // ── SHUTTING DOWN CORRECTLY ─────────────────────────────────────────
    pool.shutdown();                                   // stop accepting; returns at once
    if (!pool.awaitTermination(30, SECONDS)) {         // the actual wait
        pool.shutdownNow();                            // interrupt the stragglers
        pool.awaitTermination(10, SECONDS);
    }
    // Java 19+: try (var pool = Executors.newFixedThreadPool(8)) { ... }  does all of it.
    // Forget this and NON-DAEMON threads keep the JVM alive: main returns, nothing exits.""",

"""9. THE TRACE — one pool, four load levels

CONFIGURATION: core 4, max 8, `ArrayBlockingQueue(10)`, `CallerRunsPolicy`. Watch what each arriving
task does:

    task#  threads  queue  what happens                                  which rule fired
    ------------------------------------------------------------------------------------------
    1–4    0→4      0      a NEW THREAD each time — even though thread 1  rule 1: below core,
                           may already be idle                            always create
    5–14   4        0→10   QUEUED. No new threads, even though 4 more     rule 2: queue first
                           are permitted.                                 ← THE SURPRISING ONE
    15–18  4→8      10     queue is full → create threads 5..8            rule 3: only now
    19+    8        10     at max AND queue full → REJECTION POLICY →     rule 4
                           THE CALLING THREAD RUNS THE TASK ITSELF

    LOOK AT ROWS 5–14 AGAIN. Four threads are working, four more are ALLOWED, and ten tasks are sitting
    in a queue waiting. That is not a bug; it is the documented order. And it is why people report
    "my pool won't scale up" — it will, but only after the queue fills.

NOW REPLACE THE BOUNDED QUEUE WITH AN UNBOUNDED ONE — `newFixedThreadPool(4)`:

    task#      threads  queue      what happens
    ------------------------------------------------------------------------------------------
    1–4        0→4      0          create up to core
    5–1,000    4        →996       queued
    5–100,000  4        →99,996    STILL QUEUED. maximumPoolSize is unreachable.
    ...        4        growing    the heap fills with Runnables and their captured state
    eventually —        —          OutOfMemoryError, with a stack trace pointing at the queue

    NO REJECTION EVER HAPPENED. The system had no mechanism to say "no", so it said "yes" until it
    died. The pool behaved exactly as configured.

AND THE `CallerRunsPolicy` VERSION, which is the interesting one:

    time  producer thread                    pool                  effective rate
    ------------------------------------------------------------------------------------------
    t0    submitting 1000/sec                8 busy, queue 10      1000/sec accepted
    t1    submit REJECTED → CALLER RUNS IT   8 busy, queue 10      producer is now BUSY
    t2    producer still executing the task  8 busy, draining      producer submits NOTHING
    t3    producer finishes, submits again   queue has space       accepted
    ------------------------------------------------------------------------------------------
    THE PRODUCER THROTTLED ITSELF. No signal was sent, no rate limiter was configured, no exception was
    thrown. The system simply cannot outrun itself, because the thing generating work is the thing that
    absorbs the overflow. That is why this policy is worth knowing by name.

AND THE FAILURE THAT LOOKS LIKE NOTHING AT ALL:

    scheduleAtFixedRate(refresh, 0, 1, MINUTES)
    t=0min    runs, ok
    t=1min    runs, ok
    t=2min    THROWS — a transient network blip
    t=3min    ... nothing
    t=4min    ... nothing
    forever   ... nothing. No log line. No metric. The Future is cancelled and no one holds it.

    THE ONLY SYMPTOM IS DATA GETTING OLDER. Which is why the try/catch inside a scheduled task is not
    defensive programming; it is the difference between a job that exists and one that does not.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Thread creation: ~100 μs and ~1 MB reserved stack. Pool submission: sub-microsecond.
    Task arrival order: below core → CREATE; else → QUEUE; queue full → create up to max; else → REJECT.
    Unbounded queue ⇒ maximumPoolSize is unreachable, by construction.
    CPU-bound sizing ≈ cores. I/O-bound ≈ cores × (1 + wait/compute).
    `newFixedThreadPool`: unbounded QUEUE. `newCachedThreadPool`: unbounded THREADS.
    `submit` stores exceptions in the Future; `execute` routes them to the uncaught handler.
    A throwing `scheduleAtFixedRate` task cancels its schedule permanently.

THE #1 MISTAKE: an unbounded queue. Overload becomes an OutOfMemoryError instead of backpressure, and
maximumPoolSize silently stops meaning anything.

THE #2 MISTAKE: `submit` with an ignored Future. Every exception invisible; work stops and nothing
records it.

THE #3 MISTAKE: not wrapping scheduled tasks in try/catch. One throw cancels the schedule forever.

THE #4 MISTAKE: expecting maximumPoolSize to be reached with a `LinkedBlockingQueue`. It cannot be.

THE #5 MISTAKE: `newCachedThreadPool` for untrusted or bursty load. Unbounded thread creation.

THE #6 MISTAKE: blocking on a Future from the same bounded pool. Deadlock — guaranteed on a
single-thread pool, load-dependent on a larger one, which is worse because it ships.

THE #7 MISTAKE: forgetting to shut down. Non-daemon threads keep the JVM alive after `main` returns.

THE #8 MISTAKE: swallowing `InterruptedException`. Destroys the flag, so `shutdownNow` cannot stop the
task. Rethrow, or restore the flag.

THE #9 MISTAKE: default thread names. `pool-2-thread-7` identifies nothing in a thread dump.

THE #10 MISTAKE: ThreadLocals never removed. Pooled threads never die, so the values never go.

THE #11 MISTAKE: one pool for every kind of work. Slow calls starve fast ones; separate pools are
bulkheads.

THE #12 MISTAKE: blocking on `ForkJoinPool.commonPool()` via parallel streams or executor-less
`CompletableFuture`. It is shared by the entire JVM.

ONE-SENTENCE TAKEAWAY: a thread pool's threads are the boring half — the QUEUE and the REJECTION POLICY
are the design, because tasks only create threads beyond the core once the queue is FULL, which makes
`maximumPoolSize` unreachable behind an unbounded queue and turns `newFixedThreadPool` into a system
that queues until the heap is gone rather than ever saying no; construct `ThreadPoolExecutor` yourself
with a bounded queue and `CallerRunsPolicy` so overload throttles the producer, size from the
wait-to-compute ratio, name the threads, catch `Throwable` inside every task — especially scheduled
ones, where a single throw cancels the schedule permanently and silently — and never block on a Future
from the pool you are running in.""",
]


DEEP["Deadlock — the four conditions, and the one-line fix"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two threads, each waiting for the other

Two threads need the same two locks. Thread A takes lock 1 and reaches for lock 2. Thread B, at the
same moment, holds lock 2 and reaches for lock 1. Neither will release what it holds until it gets what
it wants, and neither will ever get what it wants.

    THEY WAIT FOREVER. Not slowly — FOREVER. No exception, no timeout, no log line. The threads simply
    stop existing as far as your monitoring is concerned: CPU usage falls, memory sits still, and
    requests hang until the load balancer times them out.

    THE SYMPTOM IS SILENCE. Which is why deadlock is disproportionately painful for its frequency: a
    crash tells you where it happened, a slow query shows up in a profile, but a deadlock produces an
    application that looks healthy on every dashboard except the one nobody is watching.

    AND IT IS NOT A RACE CONDITION. That distinction matters. A race is non-deterministic in its
    OUTCOME — sometimes right, sometimes wrong. A deadlock is fully deterministic: given that exact
    interleaving, it happens 100% of the time. It is the INTERLEAVING that is rare. So it survives
    testing, survives staging, and appears at peak traffic — because peak traffic is simply more
    attempts at the rare ordering.

THE EVERYDAY VERSION: a narrow corridor, two people carrying a table each. One is halfway through
holding the left rail; the other is halfway through holding the right. Each needs the other's rail to
continue and neither will put theirs down. They will stand there indefinitely, and both are behaving
perfectly reasonably.

TERMS AS THEY APPEAR:
- LOCK / MONITOR: the thing only one thread may hold at a time.
- LOCK ORDERING: the discipline of always acquiring locks in the same global order.
- LIVELOCK: threads that are running and responding but making no progress.
- STARVATION: a thread that could progress but is never scheduled to.""",

"""2. THE INTUITION — the four conditions, and the fact that you only have to break one

COFFMAN'S FOUR CONDITIONS. Deadlock requires ALL FOUR simultaneously. That is the useful part: to make
deadlock impossible you only have to make ONE of them impossible.

    1. MUTUAL EXCLUSION — a resource can be held by only one thread at a time.
    2. HOLD AND WAIT — a thread holding one resource may request another.
    3. NO PREEMPTION — a resource cannot be forcibly taken from the thread holding it.
    4. CIRCULAR WAIT — there is a cycle of threads, each waiting on one held by the next.

NOW ASK WHICH ONE YOU CAN ACTUALLY BREAK IN JAVA:

    MUTUAL EXCLUSION — usually not. It is the point of the lock. Though sometimes you can: an immutable
    object, a copy-on-write structure, or a `ConcurrentHashMap` needs no exclusive lock at all, and
    "make it immutable" is a real and underused answer.

    HOLD AND WAIT — you can, by acquiring everything at once or nothing. Awkward, and it requires
    knowing the full set up front, which you often do not.

    NO PREEMPTION — you can, with `tryLock(timeout)`: if you cannot get the second lock, RELEASE THE
    FIRST, back off, and retry. This works, and it is essential when the ordering genuinely cannot be
    predetermined. But it needs a backoff or you get livelock, and it needs retry logic.

    CIRCULAR WAIT — THIS IS THE ONE. If every thread in the system acquires locks in the SAME GLOBAL
    ORDER, a cycle is arithmetically impossible: to have a cycle, some thread must hold a higher-ranked
    lock while waiting for a lower-ranked one, and the rule forbids that. NO COORDINATION, NO TIMEOUTS,
    NO RETRIES — just a rule everyone follows.

THE ONE-LINE FIX, THEREFORE, IS A CONSISTENT ORDER:

    IF THE OBJECTS HAVE A NATURAL ID — account number, user id, primary key — order by that. It is
    stable, meaningful, and readable.
    IF THEY DO NOT, ORDER BY `System.identityHashCode`. It is arbitrary but consistent within a run.
    AND HANDLE THE TIE: identity hash codes can collide, so take a third "tie-break" lock first in
    that rare case. Skipping the tie-break leaves a deadlock that fires roughly once in four billion
    pairs — which on a busy system is not never.

THE DEEPER LESSON, and the one worth saying in an interview: DEADLOCK IS A PROPERTY OF THE SYSTEM, NOT
OF A METHOD. Two methods that are each individually correct deadlock when combined. Which means you
cannot find it by reviewing a function; you find it by writing down the lock order for the whole
codebase and enforcing it.""",

"""3. THE MECHANISM — where deadlocks actually come from, and how to see one

THE TEXTBOOK EXAMPLE — two explicit locks in two orders — almost never appears in real code, because it
is too visible. THE REAL CAUSES ARE ALL FORMS OF "A LOCK YOU DID NOT KNOW YOU WERE HOLDING":

    THE ALIEN METHOD, the single biggest cause. You hold a lock and call code you do not control — a
    listener, a callback, an overridable method, a plugin. That code takes its own locks, in its own
    order, and you have just merged two lock hierarchies without meaning to. THE RULE THAT PREVENTS IT
    IS "OPEN CALLS": never hold a lock while calling something you do not own.

    LOCK ORDER DETERMINED BY ARGUMENTS. `transfer(from, to)` locks `from` then `to`. Perfectly
    reasonable, and the reversed call `transfer(b, a)` running concurrently is the deadlock. THE ORDER
    IS DATA-DEPENDENT, so no amount of reading the method reveals it.

    RE-ENTRANT-LOOKING CODE THAT IS NOT. `synchronized` is re-entrant on the SAME lock, so a recursive
    call is fine. Two DIFFERENT locks around the same logical operation are not.

    THE THREAD POOL. A task holds a lock and waits on a Future for another task that needs the same
    lock, in a pool with no free threads. The locks are fine; the RESOURCE is the thread.

    THE DATABASE, which is the same shape one level down. Two transactions updating the same rows in
    different orders deadlock in the engine — and unlike Java, the database DETECTS it, picks a victim,
    and throws. That is why the fix there is a retry loop, and why the underlying discipline is
    identical: update rows in a consistent order.

HOW TO SEE ONE — and this is the part that makes deadlock much less frightening than it sounds:

    `jstack <pid>` (or `jcmd <pid> Thread.print`) DETECTS JAVA DEADLOCKS AUTOMATICALLY. It prints
    "Found one Java-level deadlock:" followed by exactly which threads, which locks, and which lines.
    NOT AN INFERENCE — A DIAGNOSIS. It works for both `synchronized` monitors and
    `java.util.concurrent` locks.

    `ThreadMXBean.findDeadlockedThreads()` does the same programmatically, which lets a health check
    report it.

    WHAT NEITHER DETECTS: deadlocks that are not lock cycles. Waiting on a `CountDownLatch` nobody
    counts down, a `SynchronousQueue` handoff nobody takes, a `Future` that will never complete, a
    thread-pool exhaustion. Those look identical from the outside and require reading the thread dump
    yourself — every thread's stack, looking for what each is waiting on.

TWO PROPERTIES OF `synchronized` THAT MATTER HERE: it has NO TIMEOUT and it is NOT INTERRUPTIBLE. Once
a thread is blocked on a monitor there is no way to get it out, which is one of the strongest arguments
for `ReentrantLock` in code where deadlock is a real risk.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — DATA-DEPENDENT LOCK ORDER. `transfer(a, b)` and `transfer(b, a)`. The method is correct; the
PAIR is not. This is the canonical real deadlock.

CASE 2 — THE ALIEN METHOD. Holding a lock while calling a listener, callback, or overridable method.
You have merged an unknown lock hierarchy into yours.

CASE 3 — NESTED SYNCHRONIZED ACROSS LAYERS. A synchronized service method calls a synchronized
repository method which calls back into a synchronized cache. Nobody wrote a nested lock; the call
graph did.

CASE 4 — THREAD POOL DEADLOCK. Tasks waiting on other tasks in a bounded pool. Guaranteed on a
single-thread pool; load-dependent on a larger one, which is worse.

CASE 5 — IDENTITY HASH COLLISION IN AN ORDERING SCHEME. Two objects with the same
`System.identityHashCode` defeat the ordering. Rare, and requires an explicit tie-break lock.

CASE 6 — LIVELOCK. Both threads detect contention, both back off, both retry at the same interval,
forever. Running, responsive, making no progress. The fix is RANDOMISED backoff — deterministic backoff
reproduces the collision.

CASE 7 — LOCK-ORDER INVERSION VIA CLASS INITIALISATION. Class loading takes an internal lock. Two
classes whose static initialisers reference each other from different threads deadlock inside the JVM
itself, and the stack traces are baffling.

CASE 8 — DEADLOCK WITH A NON-LOCK. `CountDownLatch` never counted down, a `Future` never completed, a
`SynchronousQueue` handoff with no partner. `jstack` will NOT report these as deadlocks.

CASE 9 — `synchronized` ON A `String` OR A BOXED `Integer`. Interned literals and cached Integers are
SHARED GLOBALLY, so unrelated code can be holding "your" lock. Always lock a private final Object.

CASE 10 — LOCKING ON `this` IN A PUBLIC CLASS. Anyone can `synchronized (yourObject)` and participate
in your lock protocol without you knowing.

CASE 11 — RE-ENTRANCY ASSUMED ACROSS DIFFERENT LOCKS. `synchronized` is re-entrant on the SAME monitor
only.

CASE 12 — `tryLock` WITHOUT RELEASING WHAT YOU HOLD. If you fail to get the second lock and keep the
first while retrying, you have preserved hold-and-wait and gained nothing.

CASE 13 — DEADLOCK THAT ONLY APPEARS UNDER LOAD. It is not intermittent behaviour; it is a rare
interleaving. More traffic means more attempts, which is why it debuts at peak.""",

"""5. THE ALTERNATIVES — designing so the question does not arise

DO NOT SHARE MUTABLE STATE. The strongest fix, and it removes condition 1 entirely:
    IMMUTABLE OBJECTS need no locks at all. `record`, final fields, defensive copies.
    CONFINEMENT — give each thread its own copy and merge at the end. This is what a map-reduce does,
    and what a per-request object graph does.
    MESSAGE PASSING — an actor or a queue, where state is owned by one thread and others send
    requests. The lock discipline becomes structural rather than remembered.

USE A CONCURRENT COLLECTION INSTEAD OF LOCKING ONE. `ConcurrentHashMap.compute` performs a read-modify-
write atomically without you holding anything across the operation. `AtomicLong`, `LongAdder`,
`CopyOnWriteArrayList`. MOST "I NEED TWO LOCKS" SITUATIONS ARE ACTUALLY "I AM USING THE WRONG DATA
STRUCTURE".

`ReentrantLock` OVER `synchronized` WHERE DEADLOCK IS A REAL RISK, for three capabilities `synchronized`
does not have:
    `tryLock()` and `tryLock(timeout)` — breaks the no-preemption condition;
    `lockInterruptibly()` — lets you cancel a blocked thread;
    fairness, and multiple `Condition` objects per lock.
    The cost is that you must `unlock()` in a `finally`, every time, without exception.

A SINGLE COARSER LOCK. Genuinely underrated. Two fine-grained locks that deadlock are worse than one
coarse lock that serialises. MEASURE BEFORE ASSUMING THE COARSE LOCK IS TOO SLOW — most contention
concerns are imagined, and correctness is not.

STAMPEDLOCK for read-heavy structures — an optimistic read mode that takes no lock at all and validates
afterwards. Not re-entrant, which is a real trap.

DATABASE-LEVEL: consistent update order, short transactions, and a RETRY loop, because the engine
detects the deadlock and throws rather than hanging. `SELECT ... FOR UPDATE` in a defined order.

THE ONE-LINE FIX ITSELF — a global lock ordering. Not a library, not a framework: a rule, written down,
applied everywhere:

    Object first  = a.id() < b.id() ? a : b;
    Object second = a.id() < b.id() ? b : a;
    synchronized (first) { synchronized (second) { ... } }

WHAT TO SAY: "First I would try to remove the shared mutable state or use a concurrent collection so no
second lock exists. If two locks are genuinely needed, a global acquisition order breaks circular wait
with no coordination at all. And `tryLock` with a timeout and randomised backoff where the order
genuinely cannot be predetermined."

""",

"""6. HOW TO PREVENT AND DIAGNOSE — numbered steps

STEP 1 — TRY TO NEED ONLY ONE LOCK. Immutability, confinement, or a concurrent collection removes the
problem rather than managing it.

STEP 2 — WRITE DOWN A GLOBAL LOCK ORDER for the whole codebase, and put it somewhere people read.
Deadlock is a system property; it cannot be prevented one method at a time.

STEP 3 — WHEN LOCKING TWO OBJECTS OF THE SAME TYPE, ORDER BY A STABLE KEY. An id where one exists,
`System.identityHashCode` otherwise, plus a tie-break lock for the collision case.

STEP 4 — NEVER HOLD A LOCK WHILE CALLING CODE YOU DO NOT OWN. Callbacks, listeners, overridable
methods, plugins. Compute under the lock, release, then call out.

STEP 5 — PREFER `tryLock(timeout)` WHERE ORDERING IS IMPOSSIBLE, and RELEASE EVERYTHING on failure.
Keeping the first lock while retrying preserves hold-and-wait.

STEP 6 — RANDOMISE THE BACKOFF. Fixed backoff turns a deadlock into a livelock.

STEP 7 — LOCK PRIVATE FINAL OBJECTS. Never a `String`, never a boxed `Integer`, and never `this` in a
public class — all of those are locks other code can hold.

STEP 8 — KEEP CRITICAL SECTIONS SHORT AND FREE OF I/O. A lock held across a network call converts a
downstream slowdown into a total stall.

STEP 9 — WHEN IT HANGS, TAKE A THREAD DUMP FIRST. `jstack <pid>` or `jcmd <pid> Thread.print`. It
detects lock cycles automatically and names the threads, the locks and the lines.

STEP 10 — IF THE DUMP SHOWS NO DEADLOCK BUT NOTHING PROGRESSES, LOOK FOR THE NON-LOCK VERSIONS. A
latch, a Future, an empty pool. `jstack` cannot see those, so read every thread's WAITING state
yourself.

STEP 11 — ADD `ThreadMXBean.findDeadlockedThreads()` TO A HEALTH CHECK. Turning silence into an alert
is most of the battle.

STEP 12 — USE SEPARATE POOLS FOR DEPENDENT WORK, and never block on a Future from the pool you are
running in.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Two threads need the same two locks in opposite orders. A takes lock 1 and reaches for 2; B holds 2
and reaches for 1. Neither releases what it has until it gets what it wants, so they wait forever.

And the symptom is SILENCE. No exception, no timeout, no log line. CPU drops, memory sits still,
requests hang until the load balancer gives up. Which is why it hurts more than its frequency suggests
— a crash tells you where it happened, a slow query shows up in a profile, but a deadlock leaves an
application that looks healthy on every dashboard.

The thing I'd separate out early: it's NOT a race condition. A race is non-deterministic in its
outcome. A deadlock is fully deterministic — given that interleaving it happens 100% of the time. It's
the INTERLEAVING that's rare. So it survives testing and staging and appears at peak traffic, because
peak traffic is just more attempts at the rare ordering.

The framework is Coffman's four conditions — mutual exclusion, hold and wait, no preemption, and
circular wait. You need all four simultaneously, which is the useful part: you only have to break ONE.

Mutual exclusion you usually can't break, though sometimes you can, and "make it immutable" is a real
answer people skip. Hold-and-wait means acquiring everything or nothing, which needs the full set up
front. No-preemption you break with tryLock and a timeout — release what you hold, back off, retry.
That works, but it needs retry logic and RANDOMISED backoff, because deterministic backoff turns the
deadlock into a livelock.

But the one to break is CIRCULAR WAIT, and that's the one-line fix. If everyone acquires locks in the
same global order, a cycle is arithmetically impossible — a cycle requires someone holding a
higher-ranked lock while waiting for a lower one, and the rule forbids it. No coordination, no
timeouts, no retries. Order by a natural id if there is one, System.identityHashCode if there isn't,
and take a third tie-break lock when the hashes collide — otherwise you've left a deadlock that fires
once in four billion pairs, which on a busy system isn't never.

Where they actually come from is worth saying, because the textbook two-locks-two-orders example almost
never appears in real code — it's too visible. The real cause is a lock you didn't know you were
holding. Number one is the ALIEN METHOD: you hold a lock and call a listener or an overridable method,
that code takes its own locks in its own order, and you've merged two lock hierarchies without meaning
to. The rule is open calls — never hold a lock while calling code you don't own. Number two is
data-dependent order: transfer(from, to) locks from then to, which is perfectly reasonable, and the
reversed call is the deadlock. Reading the method never reveals it.

And the encouraging part: jstack detects Java deadlocks automatically. It prints "Found one Java-level
deadlock" with the threads, the locks, and the lines. It's a diagnosis, not an inference. What it can't
see is deadlock that isn't a lock cycle — a latch nobody counts down, a Future that never completes, an
exhausted thread pool. Those look identical from outside and you have to read the dump yourself.

The framing I'd end on: deadlock is a property of the SYSTEM, not of a method. Two individually correct
methods deadlock when combined, so you can't find it in code review of a function — you find it by
writing down the lock order for the codebase and enforcing it.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE REAL DEADLOCK: the order comes from the ARGUMENTS ───────────
    void transfer(Account from, Account to, long amount) {
        synchronized (from) {              // ← thread A: locks acct1
            synchronized (to) {            // ← thread A: wants acct2
                from.debit(amount); to.credit(amount);
            }
        }
    }
    // transfer(acct1, acct2) and transfer(acct2, acct1) running concurrently:
    //   A holds acct1, wants acct2   |   B holds acct2, wants acct1
    // THE METHOD IS CORRECT. THE PAIR IS NOT. Nothing you can see by reading it.

    // ── THE ONE-LINE FIX: break CIRCULAR WAIT with a global order ───────
    void transfer(Account from, Account to, long amount) {
        Account first  = from.id() < to.id() ? from : to;
        Account second = from.id() < to.id() ? to   : from;
    //  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ EVERY thread now acquires
    //  in ascending id order, so a cycle is arithmetically impossible: a cycle needs
    //  someone holding a higher lock while waiting for a lower one.
        synchronized (first) { synchronized (second) { ... } }
    }
    // No timeouts. No retries. No coordination. Just a rule everyone follows.

    // ── AND THE TIE-BREAK PEOPLE SKIP ───────────────────────────────────
    private static final Object TIE = new Object();
    int ha = System.identityHashCode(a), hb = System.identityHashCode(b);
    if (ha == hb) {                        // ← ~1 in 4 billion. Not never.
        synchronized (TIE) { synchronized (a) { synchronized (b) { ... } } }
    } else if (ha < hb) { synchronized (a) { synchronized (b) { ... } } }
    else                { synchronized (b) { synchronized (a) { ... } } }

    // ── BREAKING "NO PREEMPTION" INSTEAD, when order is impossible ──────
    while (true) {
        if (lockA.tryLock()) {
            try {
                if (lockB.tryLock(50, MILLISECONDS)) {
                    try { doWork(); return; } finally { lockB.unlock(); }
                }
            } finally { lockA.unlock(); }
    //                 ^^^^^^^^^^^^^^ RELEASE WHAT YOU HOLD. Retrying while still
    //                 holding lockA preserves hold-and-wait and fixes nothing.
        }
        Thread.sleep(ThreadLocalRandom.current().nextInt(1, 50));
    //                ^^^^^^^^^^^^^^^^^^ RANDOMISED. A fixed backoff makes both
    //                threads retry in lockstep forever — that is LIVELOCK.
    }

    // ── THE BIGGEST REAL CAUSE: the alien method ────────────────────────
    synchronized void addItem(Item i) {
        items.add(i);
        for (Listener l : listeners) l.onItemAdded(i);
    //                                ^^^^^^^^^^^^^^ CODE YOU DO NOT OWN, called
    //   while holding YOUR lock. It takes its own locks in its own order, and you
    //   have just merged two lock hierarchies without knowing it.
    }
    void addItem(Item i) {                     // ← the "open call" fix
        List<Listener> snapshot;
        synchronized (this) { items.add(i); snapshot = List.copyOf(listeners); }
        for (Listener l : snapshot) l.onItemAdded(i);   // OUTSIDE the lock
    }

    // ── LOCKS THAT ARE SECRETLY GLOBAL ──────────────────────────────────
    synchronized ("lock") { ... }     // interned literal — SHARED PROCESS-WIDE
    synchronized (Integer.valueOf(1)) { ... }  // cached box — SHARED
    private final Object lock = new Object();  // ← the only correct form

    // ── SEEING IT ───────────────────────────────────────────────────────
    // jstack <pid>   →   "Found one Java-level deadlock:"
    //                    "Thread-1 waiting to lock monitor 0x... which is held by Thread-0"
    //                    "Thread-0 waiting to lock monitor 0x... which is held by Thread-1"
    // A DIAGNOSIS, not an inference. Works for synchronized AND j.u.c locks.""",

"""9. THE TRACE — the interleaving, and why it passed every test

TWO THREADS, `transfer(acct1, acct2)` AND `transfer(acct2, acct1)`, starting at the same moment:

    time  Thread A                          Thread B                     state
    ------------------------------------------------------------------------------------
    t0    enters transfer(acct1, acct2)     enters transfer(acct2, acct1)  —
    t1    ACQUIRES acct1                    —                              A holds acct1
    t2    —                                 ACQUIRES acct2                 B holds acct2
    t3    requests acct2 → BLOCKED          —                              A waiting on B
    t4    —                                 requests acct1 → BLOCKED       B waiting on A
    t5    blocked                           blocked                        CYCLE. FOREVER.
    ------------------------------------------------------------------------------------
    NOTHING IS THROWN. Both threads are in state BLOCKED, which looks identical to "waiting for a busy
    lock". CPU usage falls to zero for these threads. The heap does not grow. Every health check that
    does not touch this code path passes.

WHY IT PASSED TESTING — the timing window, made explicit:

    A must acquire acct1 in the gap between B starting and B acquiring acct2. That window is on the
    order of NANOSECONDS. Run the pair a thousand times in a test and you may never hit it. Run it a
    million times a day in production and you hit it daily.

    THE DEADLOCK IS NOT INTERMITTENT. Given rows t1–t4 in that order, it happens every single time,
    deterministically. What is rare is the ORDER, not the outcome. Which is exactly why "we couldn't
    reproduce it" is the normal state of affairs and why the fix must be structural rather than
    empirical.

NOW THE ORDERED VERSION, with acct1.id = 100 and acct2.id = 200:

    time  Thread A                          Thread B                     state
    ------------------------------------------------------------------------------------
    t0    first=acct1(100), second=acct2    first=acct1(100), second=acct2  SAME ORDER
    t1    ACQUIRES acct1                    —                              A holds acct1
    t2    —                                 requests acct1 → BLOCKED       B waits (fine)
    t3    ACQUIRES acct2, does the work     —                              A holds both
    t4    releases both                     —                              —
    t5    —                                 ACQUIRES acct1, then acct2     B proceeds
    ------------------------------------------------------------------------------------
    B WAITED. That is not a deadlock, that is a lock doing its job. B blocked for microseconds and then
    made progress. NO CYCLE IS POSSIBLE, because both threads want the low id first, so whoever gets it
    can always complete.

AND THE LIVELOCK VERSION — what `tryLock` gives you if you forget to randomise:

    time   Thread A                      Thread B                    progress
    ------------------------------------------------------------------------------------
    t0     tryLock(A) ✓, tryLock(B) ✗    tryLock(B) ✓, tryLock(A) ✗   none
    t1     release, sleep 50ms           release, sleep 50ms          none
    t2     tryLock(A) ✓, tryLock(B) ✗    tryLock(B) ✓, tryLock(A) ✗   none
    ...    identical forever             identical forever            NONE
    ------------------------------------------------------------------------------------
    BOTH THREADS ARE RUNNING. CPU is busy. Thread dumps show RUNNABLE. Every health check passes and no
    work is done. A FIXED BACKOFF REPRODUCES THE COLLISION EXACTLY, every cycle; randomising it breaks
    the symmetry on the first or second attempt.

WHAT PRODUCED WHAT:
    CIRCULAR WAIT      produced trace 1, and removing it produced trace 2. That is the whole fix.
    THE NANOSECOND WINDOW  produced "it passed testing" — a statement about probability, not about
                       whether the bug exists.
    SYMMETRY           produced trace 3. Randomness is the cure for symmetry, which is why the sleep
                       is random and not tidy.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Deadlock needs ALL FOUR Coffman conditions; breaking any one makes it impossible.
    Global lock ordering breaks circular wait at ZERO runtime cost — no timeouts, retries, or
    coordination. It is the cheapest correct fix available.
    `tryLock(timeout)` breaks no-preemption, at the cost of retry logic and a randomised backoff.
    `synchronized`: no timeout, not interruptible, re-entrant on the same monitor.
    `ReentrantLock`: timeout, interruptible, fair mode, multiple conditions — and `unlock()` in a
    `finally` is mandatory.
    `jstack` / `jcmd Thread.print` detect lock-cycle deadlocks automatically and name the lines.
    They do NOT detect latch, Future, queue-handoff or pool-exhaustion hangs.

THE #1 MISTAKE: data-dependent lock order. `transfer(from, to)` is correct and the reversed pair is not.

THE #2 MISTAKE: holding a lock while calling code you do not own. The alien method merges lock
hierarchies invisibly. Make it an open call.

THE #3 MISTAKE: assuming testing would have caught it. The interleaving window is nanoseconds; the
deadlock itself is 100% deterministic once it occurs.

THE #4 MISTAKE: `tryLock` that keeps the first lock while retrying. Hold-and-wait preserved, nothing
fixed.

THE #5 MISTAKE: a fixed backoff. Converts deadlock into livelock, which looks healthier and is not.

THE #6 MISTAKE: ordering by identity hash with no tie-break. One in four billion is not never at scale.

THE #7 MISTAKE: `synchronized` on a String literal, a boxed Integer, or `this` in a public class. Those
locks are reachable — and holdable — by code you have never seen.

THE #8 MISTAKE: blocking on a Future from the pool you are running in. Thread-pool deadlock, guaranteed
on one thread and load-dependent on many.

THE #9 MISTAKE: holding a lock across I/O. A slow downstream call becomes a total stall.

THE #10 MISTAKE: expecting `jstack` to explain every hang. A latch nobody counts down produces the same
silence and is not a lock cycle.

THE #11 MISTAKE: fine-grained locks adopted for performance without measurement. Two locks that
deadlock are worse than one that serialises, and most contention worries are imagined.

ONE-SENTENCE TAKEAWAY: deadlock needs mutual exclusion, hold-and-wait, no preemption AND circular wait
all at once — so you only have to break one, and the cheapest is circular wait via a GLOBAL LOCK
ORDERING (by natural id, or `System.identityHashCode` with a tie-break lock), which costs nothing at
runtime; the real causes are almost never the textbook two-locks-two-orders but rather data-dependent
ordering and holding a lock while calling code you do not own, the symptom is total silence rather than
an error, and `jstack` will name the threads and lines for you — but only when the hang is an actual
lock cycle, not a latch, a Future, or an exhausted pool.""",
]


DEEP["Why == sometimes works on Strings, and why you must never rely on it"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the comparison that works until it doesn't

    String a = "hello";
    String b = "hello";
    a == b                          →  true

    String c = new String("hello");
    a == c                          →  false

    String d = "hel";
    String e = d + "lo";
    a == e                          →  false

    THREE STRINGS THAT ALL CONTAIN "hello", AND `==` GIVES A DIFFERENT ANSWER EACH TIME.

`==` ON OBJECTS ASKS "ARE THESE THE SAME OBJECT?" — the same address, the same identity. It has never
asked about content. `equals` asks "do these hold the same characters?" and for a String that is
almost always the question you meant.

    SO WHY DOES THE FIRST ONE WORK? Because Java keeps a POOL of string literals. When the class is
    loaded, `"hello"` is placed in that pool once, and every literal `"hello"` anywhere in the program
    refers to THE SAME OBJECT. So `a == b` is true — not because the contents match, but because there
    is genuinely only one object.

    AND THAT IS EXACTLY WHY IT IS DANGEROUS. The comparison appears to work. It works in your unit
    test, where the strings are literals. It fails in production, where the string came from a request
    parameter, a database row, a JSON parser, or a concatenation — none of which are pooled. THE BUG IS
    INVISIBLE UNTIL THE DATA STOPS BEING A LITERAL, and by then the code has been reviewed and shipped.

THE EVERYDAY VERSION: two people both holding a copy of the same book. "Is it the same book?" and "does
it say the same thing?" are different questions. If the library only ever lends one physical copy, both
questions happen to give the same answer — and someone will conclude the first question is a fine way
to ask the second. Then a photocopier arrives.

TERMS AS THEY APPEAR:
- STRING POOL (string constant pool): a JVM-wide table of unique string instances.
- INTERNING: putting a string into that pool, or looking up the pooled instance.
- CONSTANT EXPRESSION: something javac can fully evaluate at compile time.
- IMMUTABLE: the contents can never change after construction — which is what makes all this safe.""",

"""2. THE INTUITION — why a pool exists at all, and what it buys

STRINGS ARE THE MOST COMMON OBJECT IN ALMOST EVERY JAVA PROGRAM. Class names, field names, map keys,
configuration values, log messages, HTTP headers. Heap dumps of real applications routinely show
strings and their backing arrays as 20–40% of live memory, and a large fraction of them are duplicates.

    SO THE JVM KEEPS A TABLE OF UNIQUE STRINGS. Every literal in every class file is interned when the
    class is loaded. Ten thousand classes containing the literal `"UTF-8"` share ONE object.

    THE SAVING IS REAL. And there is a second one people miss: comparing two pooled strings for
    equality can short-circuit on reference identity, so `equals` starts with `if (this == other)
    return true` and that check succeeds constantly on pooled data.

BUT THE POOL ONLY CONTAINS WHAT WAS PUT THERE:

    LITERALS IN SOURCE CODE                    → pooled, automatically
    COMPILE-TIME CONSTANT EXPRESSIONS          → FOLDED by javac into a literal, then pooled.
                                                 `"hel" + "lo"` becomes `"hello"` in the class file.
                                                 So does `"a" + FINAL_CONSTANT`, if the constant is a
                                                 `static final String` initialised with a literal.
    ANYTHING COMPUTED AT RUNTIME               → a NEW object, not pooled. Concatenation with a
                                                 variable, `substring`, `toUpperCase`, `split`,
                                                 `StringBuilder.toString`, a JSON parser, a JDBC driver.
    `new String("x")`                          → EXPLICITLY a new object, always. The literal is pooled;
                                                 the `new` makes a second, unpooled copy of it. This is
                                                 why the constructor is essentially never useful.
    `.intern()`                                → asks the pool for the canonical instance, adding it
                                                 if absent.

    NOW THE THREE RESULTS FROM SECTION 1 EXPLAIN THEMSELVES: `a == b` is true because both are the same
    pooled literal. `a == c` is false because `new` forced a second object. `a == e` is false because
    `d + "lo"` was computed at runtime from a VARIABLE, so the folding could not happen.

WHY THE POOL IS EVEN POSSIBLE — and this is the fact underneath the whole topic:

    STRINGS ARE IMMUTABLE. If one class could modify a shared `"hello"`, sharing it across ten thousand
    call sites would be catastrophic. IMMUTABILITY IS WHAT MAKES SHARING SAFE, and it is also what
    makes strings safe as HashMap keys, safe to pass between threads with no synchronisation, and safe
    to cache their hashCode — which `String` does, in a field, computing it once.

    IT IS ALSO A SECURITY PROPERTY. A `String` passed to a file-open or a SQL call cannot be changed by
    another thread between the security check and the use. That class of attack — time-of-check to
    time-of-use — is simply unavailable.""",

"""3. THE MECHANISM — where the pool lives, what a String is made of, and interning

WHERE THE POOL LIVES. Before Java 7 it was in PermGen, a fixed-size region, so aggressive `intern()`
could throw `OutOfMemoryError: PermGen space`. SINCE JAVA 7 IT IS IN THE NORMAL HEAP, so pooled strings
are garbage-collectable when nothing references them, and the size limit is the heap. The table itself
is a fixed-bucket hash table sized by `-XX:StringTableSize` (default 65536 in recent JDKs), and a
badly-oversubscribed table degrades `intern()` from constant time to a list walk.

WHAT A STRING IS MADE OF — and it changed in Java 9:

    BEFORE JAVA 9:   private final char[] value;      // 2 bytes per character, ALWAYS
    JAVA 9 ONWARDS:  private final byte[] value;
                     private final byte coder;        // LATIN1 or UTF16

    COMPACT STRINGS. If every character fits in one byte — which is true of essentially all ASCII text,
    so most identifiers, headers, JSON keys and English content — the string is stored one byte per
    character. THAT HALVED STRING MEMORY FOR MOST APPLICATIONS, and it was one of the largest
    across-the-board wins in a JDK release. It is invisible in the API and shows up only as a
    fifteen-percent heap reduction after upgrading.

    Also: `private int hash;` — the cached hashCode, computed on first use. A value of 0 means "not yet
    computed", so a string that genuinely hashes to 0 (including `""`) recomputed every time until
    Java 13 added a `hashIsZero` flag.

`intern()` — what it actually does and when it helps:

    Returns the canonical pooled instance, adding this string if the pool does not have it. The point
    is DEDUPLICATION: if you are parsing a million records with a hundred distinct category names, the
    naive result is a million String objects; interning gives you a hundred.
    THE COSTS ARE REAL: a native call, a hash-table lookup under contention, and pool growth you cannot
    easily observe. A `HashMap<String,String>` used as your own canonicalisation map is often faster
    and always more controllable.

`-XX:+UseStringDeduplication` — a G1 feature that does something related but different: a background GC
thread finds Strings with identical contents and points them at ONE SHARED BYTE ARRAY. The String
objects stay distinct — so `==` is unaffected and no semantics change — but the arrays, which are the
bulk of the memory, are shared. IT REQUIRES NO CODE CHANGES AT ALL, which makes it strictly easier than
interning for the memory problem.

`switch` ON A STRING, since Java 7, compiles to a `hashCode()` lookup followed by an `equals()` check —
never `==`. Which is why switching on a runtime-computed string works correctly and switching with `==`
would not.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `==` THAT PASSES EVERY TEST. Literals in tests, runtime data in production. The classic shape:
`if (status == "ACTIVE")` works until the status arrives from JSON.

CASE 2 — `"hel" + "lo" == "hello"` IS TRUE. Both are compile-time constants, folded by javac into the
same literal. Which makes the rule look inconsistent and encourages exactly the wrong conclusion.

CASE 3 — `final String X = "hel"; X + "lo" == "hello"` IS ALSO TRUE, because a `final` local initialised
with a literal is a compile-time constant. Remove the `final` and it becomes false. A ONE-KEYWORD
CHANGE FLIPS THE RESULT.

CASE 4 — `new String("hello")` IS ALWAYS A DISTINCT OBJECT. There is no reason to write it except to
demonstrate this, or to force a copy of a substring in very old JDKs.

CASE 5 — `s1.equals(s2)` WITH `s1` NULL throws. `Objects.equals(s1, s2)` is null-safe both ways, and
`"literal".equals(variable)` is the Yoda form that avoids it.

CASE 6 — `equalsIgnoreCase` VS `toLowerCase().equals(...)`. The second allocates and is LOCALE
SENSITIVE — see the next case.

CASE 7 — THE TURKISH I. `"TITLE".toLowerCase()` in a Turkish default locale gives `"tıtle"` with a
dotless ı, so `"TITLE".toLowerCase().equals("title")` is FALSE on a machine in Istanbul. This has broken
real authentication and routing code. USE `toLowerCase(Locale.ROOT)` for anything that is a protocol
token rather than human text.

CASE 8 — SUBSTRING AND MEMORY, historically. Before Java 7u6, `substring` SHARED the backing array, so
a two-character substring of a ten-megabyte string retained all ten megabytes. Since 7u6 it copies —
O(n) instead of O(1), and no leak.

CASE 9 — `String.valueOf(null)` IS AMBIGUOUS. It binds to the `char[]` overload and throws NPE, while
`String.valueOf((Object) null)` returns `"null"`.

CASE 10 — `synchronized` ON A STRING LITERAL. Interned, therefore SHARED PROCESS-WIDE. Unrelated code
can hold "your" lock.

CASE 11 — PASSWORDS IN A `String`. Immutable, so you cannot zero it, and it may be interned, so it
lingers in the heap until collected — and shows up in a heap dump. `char[]` exists so you can wipe it.

CASE 12 — `split("")` AND TRAILING EMPTIES. `"a,b,,".split(",")` gives 2 elements, not 4; the trailing
empties are dropped unless you pass a negative limit.

CASE 13 — `==` ON A `Character` OR BOXED TYPE FOR THE SAME REASON. The Integer cache from −128 to 127
is the same phenomenon wearing a different hat.""",

"""5. THE ALTERNATIVES — comparing, canonicalising, and saving memory

FOR COMPARISON:
    `equals`                     content, exact. The default answer.
    `Objects.equals(a, b)`       null-safe on both sides. Use it whenever either might be null.
    `equalsIgnoreCase`           case-insensitive without allocating, and without the locale trap.
    `compareTo`                  lexicographic ordering by UTF-16 code unit — note that this is NOT
                                 alphabetical for non-English text.
    `Collator`                   locale-correct comparison and sorting for HUMAN-FACING text. "ö" sorts
                                 differently in German and Swedish, and `compareTo` knows nothing about
                                 that.
    `String.CASE_INSENSITIVE_ORDER`  a ready-made comparator.
    `contentEquals(CharSequence)`    compare a String to a StringBuilder without materialising it.

FOR CANONICALISATION — deduplicating repeated values:
    `intern()`                   simple, JVM-wide, but a native call with a shared table.
    YOUR OWN `HashMap<String,String>` or a Guava `Interner`. Usually faster, bounded, observable, and
    discardable when the parse finishes. THE PREFERRED ANSWER IN MOST REAL SYSTEMS.
    `-XX:+UseStringDeduplication` with G1. Shares the backing ARRAYS in the background with no code
    change at all. The right first move for a memory problem.
    AN ENUM. If the set of values is closed — statuses, types, currencies — then it was never really a
    string. `==` becomes correct, exhaustive `switch` becomes available, and typos become compile
    errors.

FOR BUILDING:
    `StringBuilder` for loops, `String.join` and `Collectors.joining` for delimited output,
    `StringJoiner` when you need a prefix and suffix, text blocks for multi-line literals, and
    `String.format` / `formatted` when readability matters more than the parsing cost.

FOR SECRETS: `char[]`, so it can be zeroed. A `String` cannot be cleared and may be interned.

FOR CASE AND NORMALISATION: `toLowerCase(Locale.ROOT)` for protocol tokens; `Normalizer.normalize(s,
Form.NFC)` before comparing user-entered text, because "é" has two distinct Unicode encodings that look
identical and are not `equals`.

WHAT TO SAY: "`equals` always, `Objects.equals` when null is possible, and an enum the moment the value
set is closed. `==` on strings is a bug that passes its own tests, so I would treat any instance of it
as a defect regardless of whether it currently works."

""",

"""6. HOW TO WORK WITH STRING EQUALITY — numbered steps

STEP 1 — USE `equals`, ALWAYS. There is no case where `==` on strings is the right expression of
intent, even when it happens to return the right answer.

STEP 2 — USE `Objects.equals(a, b)` WHEN EITHER SIDE MIGHT BE NULL. Null-safe in both directions.

STEP 3 — PUT THE LITERAL FIRST when you do use `equals` directly: `"ACTIVE".equals(status)` cannot NPE.

STEP 4 — IF THE VALUE SET IS CLOSED, USE AN ENUM. Statuses, types, currencies. It converts a runtime
string comparison into a compile-time check and makes `==` genuinely correct.

STEP 5 — TURN ON A STATIC ANALYSIS RULE FOR REFERENCE COMPARISON OF STRINGS. SpotBugs `ES_COMPARING_STRINGS_WITH_EQ`,
ErrorProne `ReferenceEquality`. This is a bug class a tool can eliminate entirely.

STEP 6 — USE `equalsIgnoreCase` RATHER THAN LOWERCASING BOTH SIDES. No allocation, no locale trap.

STEP 7 — WHEN YOU MUST CHANGE CASE FOR A PROTOCOL TOKEN, PASS `Locale.ROOT`. The Turkish dotless ı is a
real production bug, not a curiosity.

STEP 8 — NORMALISE USER-ENTERED TEXT BEFORE COMPARING. `Normalizer.normalize(s, Form.NFC)`; identical-
looking accented characters have multiple encodings.

STEP 9 — DO NOT REACH FOR `intern()` AS A MEMORY FIX. Try `-XX:+UseStringDeduplication` first — no code
change — and your own map if you need control.

STEP 10 — NEVER `synchronized` ON A STRING. Interned literals are shared process-wide.

STEP 11 — KEEP SECRETS IN `char[]`. A String cannot be wiped and may outlive its use in the pool and in
heap dumps.

STEP 12 — WHEN A COMPARISON "WORKS ON MY MACHINE", CHECK WHETHER BOTH SIDES ARE LITERALS. That is
almost always the explanation, and it is a warning rather than a result.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'`==` on objects asks "are these the same object" — same address, same identity. It has never asked
about content. `equals` asks about the characters, which is what you meant.

So why does it seem to work? Because Java keeps a POOL of string literals. Every literal in every class
file is interned when the class loads, so ten thousand classes containing "UTF-8" share one object.
Two literals with the same text ARE the same object, so `==` returns true — not because the contents
match, but because there genuinely is only one object.

And that's exactly what makes it dangerous. The comparison appears to work. It works in the unit test,
where the strings are literals. It fails in production, where the string came from a request parameter,
a database row, or a JSON parser — none of which are pooled. The bug is invisible until the data stops
being a literal, and by then it's been reviewed and shipped.

The pool only contains what was put there. Literals, and compile-time CONSTANT expressions, because
javac folds those — "hel" + "lo" is literally the string "hello" in the class file. Anything computed
at runtime is a fresh object: concatenation with a variable, substring, toUpperCase, a parser. And
`new String("hello")` is always a distinct object by definition, which is why that constructor is
essentially never useful.

There's a detail that shows how brittle this is. `final String x = "hel"; x + "lo" == "hello"` is TRUE,
because a final local initialised with a literal is a compile-time constant and gets folded. Drop the
`final` and it becomes false. A one-keyword change flips the result — which is a good argument that no
one should be reasoning about this at all.

The reason a pool is even possible is that strings are IMMUTABLE. If one class could modify a shared
"hello", sharing it across ten thousand call sites would be catastrophic. Immutability is what makes
sharing safe — and it's also what makes strings safe as HashMap keys, safe to pass between threads with
no synchronisation, and safe to cache the hashCode, which String does in a field.

Two things worth knowing beyond the basics. Java 9 changed the internal representation from char[] to
byte[] plus a coder flag — compact strings — so ASCII text is one byte per character instead of two.
That halved string memory for most applications and it's invisible in the API; it just shows up as a
heap reduction after upgrading. And if you have a duplicate-strings memory problem, the first move is
-XX:+UseStringDeduplication under G1, which shares the backing ARRAYS in the background with no code
change. Not intern(), which is a native call into a shared table.

Practically: equals always, Objects.equals when null is possible, literal first so it can't NPE, and an
ENUM the moment the value set is closed — statuses, types, currencies. If it's an enum, `==` becomes
correct, switch becomes exhaustive, and typos become compile errors. I'd treat any `==` on strings as a
defect even when it currently returns the right answer, because it's a bug that passes its own tests.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE THREE ANSWERS ───────────────────────────────────────────────
    String a = "hello";                 // pooled at class load
    String b = "hello";                 // THE SAME OBJECT. Not a copy.
    System.out.println(a == b);         // true  ← identity, not content

    String c = new String("hello");     // the literal is pooled; `new` makes a
    System.out.println(a == c);         // false    SECOND, unpooled copy of it
    System.out.println(a.equals(c));    // true  ← the question you meant

    String d = "hel";
    String e = d + "lo";                // computed at RUNTIME from a variable
    System.out.println(a == e);         // false
    System.out.println(a == e.intern());// true  ← intern() returns the pooled one

    // ── THE ONE-KEYWORD FLIP ────────────────────────────────────────────
    final String F = "hel";
    System.out.println("hello" == F + "lo");   // TRUE
    //                            ^ a `final` local initialised with a literal is a
    //   COMPILE-TIME CONSTANT, so javac folds the whole expression into "hello".
    String G = "hel";                          // remove `final` ...
    System.out.println("hello" == G + "lo");   // FALSE
    //   ... and it is a runtime concatenation. SAME CODE, OPPOSITE ANSWER.

    // ── THE BUG THAT PASSES ITS OWN TESTS ───────────────────────────────
    if (status == "ACTIVE") { ... }
    // ^ In the unit test, `status` is the literal "ACTIVE" → the same pooled object
    //   → TRUE → the test passes. In production `status` came from Jackson, JDBC or
    //   a request parameter → a fresh object → FALSE → the branch never runs and
    //   nothing throws. The test suite actively certified the bug.
    if ("ACTIVE".equals(status)) { ... }       // correct, and null-safe
    if (status == Status.ACTIVE) { ... }       // better: it was never a string

    // ── THE LOCALE TRAP ─────────────────────────────────────────────────
    "TITLE".toLowerCase().equals("title")
    // ^ FALSE on a machine with a Turkish default locale: the uppercase I lowercases
    //   to a DOTLESS ı. This has broken real authentication code.
    "TITLE".toLowerCase(Locale.ROOT).equals("title")   // correct for protocol tokens
    "TITLE".equalsIgnoreCase("title")                  // better: no allocation either

    // ── WHAT A STRING IS, SINCE JAVA 9 ──────────────────────────────────
    private final byte[] value;        // was char[] — 2 bytes per char, ALWAYS
    private final byte coder;          // LATIN1 (1 byte/char) or UTF16
    private int hash;                  // cached. 0 means "not computed yet", which
    //                                    is why "" recomputed forever until Java 13
    //                                    added a hashIsZero flag.
    // COMPACT STRINGS halved string memory for most applications, invisibly.

    // ── DEDUPLICATION: three tools, different trade-offs ────────────────
    s.intern();                        // JVM-wide pool. Native call, shared table.
    myMap.computeIfAbsent(s, x -> x);  // your own canonical map: faster, bounded,
    //                                    observable, discardable. Usually better.
    // -XX:+UseStringDeduplication     // G1 shares the backing byte[] in the
    //                                    background. NO CODE CHANGE. `==` unaffected
    //                                    because the String objects stay distinct.

    // ── AND THE LOCK THAT IS SECRETLY GLOBAL ────────────────────────────
    synchronized ("lock") { ... }      // interned → SHARED PROCESS-WIDE → unrelated
    //                                    code can be holding it. Never do this.""",

"""9. THE TRACE — following four "hello"s through the JVM

CLASS LOAD. The class file's constant pool contains the literal `"hello"` once. On loading, the JVM
interns it:

    string pool:  { ... , "hello" @0x1000 }

RUNTIME, statement by statement:

    statement                    what is created                  reference     == a ?
    ------------------------------------------------------------------------------------
    String a = "hello";          nothing new — POOL LOOKUP        @0x1000       —
    String b = "hello";          nothing new — the same lookup    @0x1000       TRUE
    String c = new String("h..") pool lookup, THEN a new object   @0x2000       false
                                 copying its contents
    String d = "hel";            pool lookup                      @0x3000       —
    String e = d + "lo";         StringBuilder → new String       @0x4000       false
    e.intern()                   pool lookup: contents match      @0x1000       TRUE
                                 the existing entry, so the
                                 POOLED reference is returned
    ------------------------------------------------------------------------------------
    FOUR DISTINCT OBJECTS. All containing 'h','e','l','l','o'. `equals` is true for every pair;
    `==` is true for exactly two of them, for reasons that have nothing to do with the text.

WHAT javac DID BEFORE ANY OF THIS RAN — the compile-time half:

    source                       class file contains            why
    ------------------------------------------------------------------------------------
    "hel" + "lo"                 the single literal "hello"     both operands are
                                                                compile-time constants
    final String F = "hel";      the literal "hello"            a final local with a
    F + "lo"                                                    constant initialiser IS
                                                                a constant expression
    String G = "hel";            invokedynamic makeConcat...    G is a VARIABLE, so the
    G + "lo"                                                    value is unknown until
                                                                runtime
    ------------------------------------------------------------------------------------
    THE FOLDING IS WHY THE RULE LOOKS INCONSISTENT. Two expressions that are textually identical
    compile to completely different things, and the difference is one `final` keyword.

AND THE PRODUCTION TRACE — the same code in two environments:

    environment    where `status` came from             identity      `status == "ACTIVE"`
    ------------------------------------------------------------------------------------
    unit test      the literal "ACTIVE" in the test     pooled        TRUE  → test passes
    integration    an enum's name(), also folded        pooled        TRUE  → still passes
    production     Jackson parsed it from a byte[]      fresh object  FALSE → branch never
                                                                              runs, silently
    ------------------------------------------------------------------------------------
    THE TEST SUITE CERTIFIED THE BUG. Not by accident — by construction. Test data is written as
    literals, and literals are exactly the case where the broken comparison works. This is the reason
    the rule is "never use `==` on strings" rather than "understand when `==` is safe": the
    understanding does not survive contact with a different data source.

WHAT PRODUCED WHAT:
    THE POOL                produced `a == b`, and therefore produced the false confidence.
    CONSTANT FOLDING        produced the `final` flip — a compile-time decision showing up as a
                            runtime identity.
    RUNTIME CONCATENATION   produced every `false`, and it is what production data always is.
    IMMUTABILITY            is why the pool is safe to exist at all, and why none of these four
                            objects can be corrupted by sharing.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `==` is one reference comparison. `equals` is O(n) in the worst case, with a `this == other`
    fast path first — which succeeds constantly on pooled data.
    `hashCode` is O(n) once, then cached in a field.
    Literals and compile-time constant expressions: pooled. Everything computed at runtime: not.
    `intern()`: a native call plus a hash lookup on a shared table (`-XX:StringTableSize`, default
    65536).
    Compact strings (Java 9+): 1 byte per character for Latin-1 content, halving string memory for
    most applications.
    Since Java 7 the pool lives in the heap, so pooled strings can be collected.
    `substring` copies since Java 7u6: O(n) rather than O(1), and no retained-array leak.

THE #1 MISTAKE: `==` on strings. It passes its own tests, because test data is literals, and fails on
production data, which is not.

THE #2 MISTAKE: concluding from `"hel" + "lo" == "hello"` that concatenation is safe. That is constant
FOLDING, and adding or removing one `final` reverses it.

THE #3 MISTAKE: `new String("x")`. Always a distinct object; essentially never useful.

THE #4 MISTAKE: `variable.equals(literal)` when the variable can be null. Put the literal first, or use
`Objects.equals`.

THE #5 MISTAKE: `toLowerCase()` with no locale on a protocol token. The Turkish dotless ı breaks real
comparisons.

THE #6 MISTAKE: comparing user-entered text without Unicode normalisation. Identical-looking accented
characters have multiple encodings and are not `equals`.

THE #7 MISTAKE: `intern()` as the first response to a memory problem. `-XX:+UseStringDeduplication`
needs no code change and shares the arrays, which is where the memory actually is.

THE #8 MISTAKE: `synchronized` on a String. Interned literals are process-wide locks.

THE #9 MISTAKE: passwords in a `String`. Immutable, so unwipeable, and visible in a heap dump.

THE #10 MISTAKE: leaving a closed set of values as strings. An enum makes `==` correct, `switch`
exhaustive, and typos compile errors.

THE #11 MISTAKE: assuming `compareTo` sorts alphabetically. It orders by UTF-16 code unit; human
ordering needs a `Collator`.

ONE-SENTENCE TAKEAWAY: `==` asks whether two references point at the SAME OBJECT, and it returns true
for string literals only because the JVM interns every literal into a shared pool — a fact that has
nothing to do with the characters, that constant folding extends to expressions like `"hel" + "lo"` and
even to `final` locals, and that evaporates the moment the value is computed at runtime, which is what
all production data is; so the comparison passes every test written with literals and silently fails on
the first request parameter, and the rule is `equals` (or `Objects.equals`, or better an enum when the
value set is closed) with no exceptions, because the understanding of when `==` is safe does not survive
a change of data source.""",
]


DEEP["String concatenation in a loop — why it is O(n²) and what to use instead"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the one-line change that is 10,000x

    String result = "";
    for (String row : rows) {
        result += row;        // ← this line
    }

That loop looks linear. It is quadratic, and at any real size it is catastrophic — not "a bit slow", but
minutes instead of milliseconds.

    THE REASON IS THAT STRINGS ARE IMMUTABLE. `result += row` cannot append to `result`, because
    nothing can modify a String. What it actually does is: ALLOCATE A NEW STRING BIG ENOUGH FOR BOTH,
    COPY EVERYTHING ALREADY IN `result` INTO IT, copy `row` on the end, and point `result` at the new
    object. The old one becomes garbage.

    SO EVERY ITERATION COPIES THE ENTIRE ACCUMULATED RESULT. Iteration 1 copies 10 characters,
    iteration 1,000 copies 10,000, iteration 100,000 copies a million. Add those up and you have copied
    roughly n²/2 characters to build a string of length n.

THE ARITHMETIC, because it is more persuasive than any adjective. Appending a 10-character row 100,000
times produces a 1,000,000-character string:

    `+=` in a loop        about 50,000,000,000 characters copied   (and that is the optimistic count)
    StringBuilder         about       2,000,000 characters copied
    ratio                 roughly 25,000 to 1

    THAT IS NOT AN OPTIMISATION. Changing one line takes an operation from "the request times out" to
    "the request completes", and it is probably the single most common genuine performance defect in
    production Java.

THE EVERYDAY VERSION: writing a shopping list where the pen cannot add to an existing sheet. To add one
item you must copy the whole list onto a fresh sheet and then write the new item. Ten items is fine.
Ten thousand items means you have written about fifty million lines to produce a list of ten thousand.

TERMS AS THEY APPEAR:
- IMMUTABLE: cannot be changed after creation. The property that causes all of this.
- StringBuilder: a MUTABLE character buffer. Appending writes into spare capacity in place.
- AMORTISED: the average cost per operation once you spread out the occasional expensive one.""",

"""2. THE INTUITION — why the compiler's help stops at the loop boundary

HERE IS THE PART THAT CONFUSES PEOPLE, AND IT IS WORTH GETTING EXACTLY RIGHT: `javac` DOES OPTIMISE
STRING CONCATENATION. It has since Java 1.0. `"a" + b + "c"` does not create two intermediate strings —
the compiler rewrites it into a single buffered build.

    ON JAVA 8 AND EARLIER it becomes `new StringBuilder().append("a").append(b).append("c").toString()`.
    ON JAVA 9 AND LATER it becomes a single `invokedynamic` to `StringConcatFactory`, which generates a
    method handle chain on first execution — one that can compute the exact final length up front and
    allocate the result array ONCE. For a fixed set of operands this often BEATS hand-written
    StringBuilder code.

    SO WHY IS THE LOOP STILL QUADRATIC? BECAUSE THE OPTIMISATION IS PER-EXPRESSION, AND THE EXPRESSION
    IS INSIDE THE LOOP.

    Each iteration is its own `result + row` expression, so each iteration gets its own fresh builder,
    which starts EMPTY, which means the entire accumulated `result` must be copied into it before `row`
    can be appended. Then `toString()` copies the whole thing out again into the new String.

    TWO FULL COPIES OF THE ACCUMULATED TEXT, PER ITERATION. The compiler cannot hoist the builder out
    of the loop, because between iterations `result` is an ordinary String that other code could
    legally read.

THE FIX IS THEREFORE STRUCTURAL, NOT A TRICK: HOIST THE BUFFER OUT OF THE LOOP YOURSELF.

    StringBuilder sb = new StringBuilder();
    for (String row : rows) sb.append(row);
    String result = sb.toString();

    NOW THERE IS ONE BUFFER FOR THE WHOLE LOOP. Appending writes into spare capacity in place — no copy
    at all in the common case. When capacity runs out the buffer GROWS by roughly doubling, which
    copies, but doubling means the total copying across all growths is O(n), not O(n²). One final copy
    in `toString()`.

WHY DOUBLING MAKES IT LINEAR — the argument worth being able to give:

    growing to 16, 34, 70, 142, ... each growth copies what is currently there. The total copied is
    16 + 34 + 70 + ... which is a geometric series summing to less than 2n. SO THE WHOLE BUILD COPIES
    UNDER 2n CHARACTERS regardless of how many appends there were. Geometric growth is the reason
    `ArrayList.add` is amortised O(1) too — it is the same trick.

AND THE ONE-LINE IMPROVEMENT ON TOP: `new StringBuilder(expectedSize)` removes every growth and every
copy but the final one. When you know the size, this is free.""",

"""3. THE MECHANISM — what StringBuilder is, and what indy concat does

StringBuilder IS A MUTABLE CHARACTER BUFFER — since Java 9 a `byte[]` plus a `coder` flag, exactly like
String, but with the array NOT final and a `count` of how much is used:

    byte[] value;      // the buffer, with SPARE CAPACITY at the end
    int count;         // how much is actually used
    byte coder;        // LATIN1 or UTF16

    append(x)          copies x's characters into value[count..], bumps count. NO other copying.
    ensureCapacity     when the buffer is full, allocate `value.length * 2 + 2` and copy once.
    toString()         ONE copy of the used region into a new String's array.

    NOTE THE `* 2 + 2`. The `+2` exists so that growth still works from a zero-length buffer. Default
    capacity is 16 characters, or 16 + the length of the string if you use the `StringBuilder(String)`
    constructor.

StringBuffer IS THE SAME CLASS WITH `synchronized` ON EVERY METHOD. It predates `StringBuilder`
(which arrived in Java 5) and it is essentially always the wrong choice: a builder is a local variable
in almost every program that exists, so the locking protects nothing. AND EVEN WHEN SHARED IT IS
USUALLY NOT ENOUGH — `sb.append(a).append(b)` is two separate locks, so another thread can interleave
between them. Per-method synchronisation rarely gives you the atomicity you actually wanted.

INVOKEDYNAMIC CONCATENATION (Java 9+), because it explains why the modern answer is subtler:

    `"user=" + name + " id=" + id` compiles to ONE `invokedynamic` instruction naming
    `StringConcatFactory.makeConcatWithConstants`. On first execution, that bootstrap builds a
    MethodHandle chain specialised to those exact operand types, and the JIT then inlines the whole
    thing.

    WHAT THAT BUYS: the length of every operand can be computed FIRST, so the result array is allocated
    exactly once at exactly the right size — no builder, no growth, no intermediate copy. For a fixed
    list of operands this beats writing StringBuilder by hand, which is why "always use StringBuilder"
    is outdated advice for straight-line code.

    WHAT IT CANNOT DO: span a loop. The instruction is inside the loop body, so it runs afresh every
    iteration on the whole accumulated string. THE QUADRATIC PROBLEM IS UNAFFECTED, and it is the only
    problem that matters.

`String.format` AND `formatted` PARSE THE FORMAT STRING ON EVERY CALL — a scan, a `Formatter` object,
and boxing of every argument. Roughly an order of magnitude slower than concatenation. That is
irrelevant in a log line and very relevant in a loop.

`String.concat(s)` is a plain two-way copy with no builder at all. Marginally faster than `+` for
exactly two strings on old JDKs, and it NPEs rather than printing "null".""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `+=` IN A LOOP. The headline. Quadratic, and it is usually written by someone who knows about
StringBuilder but did not notice the loop.

CASE 2 — CONCATENATION INSIDE `append`. `sb.append("a" + x + "b")` builds a temporary string and then
copies it in. Use three appends; the chained form allocates nothing extra.

CASE 3 — UNGUARDED CONCATENATION IN A LOG CALL. `log.debug("state " + expensive())` builds the string
and calls `expensive()` EVEN WHEN DEBUG IS OFF, because arguments are evaluated before the call. Use
parameterised logging: `log.debug("state {}", value)`. THIS IS A REAL HOT-PATH COST IN PRODUCTION
SYSTEMS and it hides behind a disabled log level.

CASE 4 — `String.format` IN A HOT LOOP. Parses the format string every call. Fine for messages, wrong
for bulk output.

CASE 5 — NOT PRE-SIZING WHEN THE SIZE IS KNOWN. Building a 1 MB string from the default 16-character
capacity performs about 17 growth-and-copy cycles.

CASE 6 — SHARING A `StringBuilder` ACROSS THREADS. Not thread-safe; you get interleaved or corrupted
output, or an `ArrayIndexOutOfBoundsException` from `count` and `value` disagreeing.

CASE 7 — `StringBuffer` "FOR SAFETY". Per-method locking that protects nothing in a local variable,
and does not give atomicity across chained appends even when shared.

CASE 8 — `sb.append(null)` APPENDS THE TEXT "null" — four characters — rather than throwing. So does
`+`. `String.concat(null)` throws instead. Three different behaviours for the same idea.

CASE 9 — `sb + ""` OR `"" + x` TO CONVERT TO A STRING. Works, allocates, and obscures intent.
`String.valueOf(x)` is clearer and handles null.

CASE 10 — REUSING A BUILDER WITH `setLength(0)` AND EXPECTING THE MEMORY BACK. The backing array stays
at its high-water mark. Usually that is what you want (no regrowth); occasionally it is a leak.

CASE 11 — BUILDING A DELIMITED LIST WITH A TRAILING-SEPARATOR FIX-UP. The `sb.setLength(sb.length()-1)`
pattern. `String.join` or `Collectors.joining` does it correctly and reads better.

CASE 12 — ASSUMING "ALWAYS USE StringBuilder". For straight-line concatenation on Java 9+, invokedynamic
concat is usually FASTER than a hand-written builder, because it can size the result exactly. The rule
is about LOOPS, not about `+`.

CASE 13 — CONCATENATING IN A `Stream.reduce`. `reduce("", String::concat)` is the same quadratic
behaviour wearing a functional hat. `Collectors.joining()` is linear.""",

"""5. THE ALTERNATIVES — pick by shape, not by habit

STRAIGHT-LINE CONCATENATION OF A FIXED SET OF OPERANDS — just use `+`. On Java 9+ it compiles to
invokedynamic and sizes the result exactly. It is the most readable option AND usually the fastest.
Writing StringBuilder by hand here makes the code worse for no gain.

A LOOP — `StringBuilder`, hoisted out of the loop, pre-sized when you know the size. This is the case
the whole entry exists for.

A DELIMITED LIST — never build it by hand:
    `String.join(", ", list)`                        simplest, for a collection of strings
    `list.stream().map(...).collect(joining(", "))`  when elements need transforming
    `new StringJoiner(", ", "[", "]")`               when you need a prefix, suffix, and an
                                                     "empty value" for the zero-element case
    ALL THREE HANDLE THE SEPARATOR CORRECTLY, which is where the hand-rolled version usually has a
    trailing-comma fix-up bug.

MULTI-LINE LITERAL TEXT — TEXT BLOCKS (Java 15+), delimited by three double-quotes, with the
    incidental indentation stripped for you.
Replaces the `"line\\n" + "line\\n"` pattern entirely, and `.formatted(...)` fills in placeholders.

STREAMING OUTPUT — if the result goes to a file, a socket, or an HTTP response, DO NOT BUILD THE STRING
AT ALL. Write to a `BufferedWriter` or an `OutputStream` as you go. A 500 MB report built in memory is
an OutOfMemoryError; the same report streamed is a constant-memory operation. THE BEST FIX FOR A LARGE
CONCATENATION IS OFTEN TO NOT CONCATENATE.

FORMATTING — `String.format` / `"...".formatted(...)` when readability matters, `MessageFormat` for
localised text with plurals and ordering, and PARAMETERISED LOGGING (`log.debug("x {}", v)`) always, so
disabled levels cost nothing.

CHARACTER-LEVEL WORK — `char[]` or a pre-sized `StringBuilder` with `setCharAt`, when you are doing
transformations rather than appends.

`StringBuffer` — legacy. If you genuinely need a shared mutable buffer you need external
synchronisation for atomicity anyway, so the per-method locking buys nothing.

WHAT TO SAY: "`+` for straight-line concatenation, because on Java 9+ invokedynamic sizes the result
exactly and beats a hand-written builder. StringBuilder the moment there is a LOOP, pre-sized when I
know the size. `String.join` or `Collectors.joining` for delimited output. And if the result is going
to a stream, I would not build the string at all."

""",

"""6. HOW TO GET THIS RIGHT — numbered steps

STEP 1 — LOOK FOR `+=` ON A STRING INSIDE A LOOP. That single pattern is the defect. Everything else in
this entry is refinement.

STEP 2 — HOIST A `StringBuilder` OUT OF THE LOOP. One buffer for the whole loop, `toString()` once at
the end.

STEP 3 — PRE-SIZE IT WHEN YOU KNOW ROUGHLY HOW BIG THE RESULT IS. `new StringBuilder(rows.size() * 40)`
removes every growth and copy but the last.

STEP 4 — DO NOT REWRITE STRAIGHT-LINE `+` INTO A BUILDER. On Java 9+ that makes it slower and less
readable. The rule is about loops.

STEP 5 — USE `String.join` OR `Collectors.joining` FOR DELIMITED OUTPUT. It removes the trailing-
separator bug class entirely.

STEP 6 — USE PARAMETERISED LOGGING, ALWAYS. `log.debug("x {}", v)` costs nothing when the level is off;
`log.debug("x " + v)` builds the string and evaluates the arguments regardless.

STEP 7 — CHAIN `append` CALLS INSTEAD OF CONCATENATING INSIDE ONE. `append(a).append(b)`, not
`append(a + b)`.

STEP 8 — KEEP `String.format` OUT OF HOT LOOPS. It parses the format string on every call.

STEP 9 — IF THE OUTPUT IS GOING SOMEWHERE, STREAM IT. A `BufferedWriter` turns an unbounded memory
requirement into a constant one.

STEP 10 — USE A TEXT BLOCK FOR MULTI-LINE LITERALS. It is both faster (one constant) and far more
readable than a chain of `+ "\n"`.

STEP 11 — NEVER SHARE A `StringBuilder` BETWEEN THREADS. And do not reach for `StringBuffer` as the
fix — it does not give you atomicity across chained calls anyway.

STEP 12 — IF YOU MEASURE, MEASURE AT A REALISTIC SIZE. At 100 iterations the quadratic version looks
fine; the whole problem is that the cost grows with the square, so small tests actively mislead.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'`result += row` in a loop looks linear and is quadratic. Strings are immutable, so `+=` cannot append
to the existing string — it allocates a new one big enough for both, copies everything already there
into it, copies the new piece on the end, and rebinds the variable.

So every iteration copies the whole accumulated result. Iteration one copies 10 characters, iteration
a thousand copies ten thousand, iteration a hundred thousand copies a million. Add those up and you've
copied about n²/2 characters to build a string of length n. Concretely: appending a 10-character row
100,000 times copies roughly fifty billion characters, where a StringBuilder copies about two million.
That's four orders of magnitude, and it turns a request that completes into a request that times out.

Now the part people get wrong in both directions. javac DOES optimise concatenation — it has since 1.0.
`"a" + b + "c"` doesn't build intermediates; on Java 8 it becomes a StringBuilder chain, and on Java 9+
it becomes a single invokedynamic into StringConcatFactory, which builds a method handle chain that
computes every operand's length FIRST and allocates the result array exactly once. For straight-line
concatenation that actually beats a hand-written StringBuilder, so "always use StringBuilder" is
outdated advice.

The reason the loop is still quadratic is that the optimisation is PER-EXPRESSION and the expression is
inside the loop. Each iteration gets its own fresh builder, starting empty, so the whole accumulated
result has to be copied into it before the new piece can be appended — and then toString copies it all
out again. Two full copies per iteration. And the compiler can't hoist the builder out, because between
iterations `result` is an ordinary String that other code could legally read.

Which makes the fix structural rather than a trick: hoist the buffer out yourself. Then there's one
buffer for the whole loop, appends write into spare capacity in place, and when it runs out it grows by
roughly doubling. Doubling is what makes it linear — the growths copy 16, then 34, then 70, a geometric
series that sums to under 2n. Same reason ArrayList.add is amortised O(1).

So my actual rule is: `+` for straight-line concatenation, because it's the most readable AND usually
the fastest on a modern JDK. StringBuilder the moment there's a loop, pre-sized if I know the size.
String.join or Collectors.joining for anything delimited, because the hand-rolled version always has
the trailing-comma fix-up. And parameterised logging always — `log.debug("x " + v)` builds the string
and evaluates the arguments even when debug is off, which is a real hot-path cost hiding behind a
disabled log level.

One more: if the result is going to a file or an HTTP response, I'd push back on building the string at
all. Streaming to a BufferedWriter turns an unbounded memory requirement into a constant one, and a
500 MB report built in memory is an OutOfMemoryError.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE DEFECT ──────────────────────────────────────────────────────
    String result = "";
    for (String row : rows) {
        result += row;
    //  ^^^^^^^^^^^^^ Strings are IMMUTABLE, so this cannot append. It:
    //    1. allocates a StringBuilder (a fresh one, this iteration only)
    //    2. copies ALL of `result` into it              ← the whole accumulated text
    //    3. appends `row`
    //    4. toString() — copies it ALL out again        ← a second full copy
    //    5. the previous `result` becomes garbage
    //  TWO FULL COPIES PER ITERATION, of a string that grows every time.
    }

    // ── WHY THE COMPILER CANNOT SAVE YOU ────────────────────────────────
    // javac DOES optimise concatenation — this is not a naive compiler:
    //   Java 8:  new StringBuilder().append(a).append(b).toString()
    //   Java 9+: invokedynamic → StringConcatFactory.makeConcatWithConstants
    //            which sizes the result array EXACTLY and allocates once.
    // But the optimisation is PER EXPRESSION, and the expression is INSIDE the loop.
    // Between iterations `result` is an ordinary String other code could read, so
    // the builder cannot be hoisted. THE OPTIMISATION IS REAL AND IRRELEVANT HERE.

    // ── THE FIX: hoist the buffer yourself ──────────────────────────────
    StringBuilder sb = new StringBuilder(rows.size() * 40);
    //                                   ^^^^^^^^^^^^^^^^ pre-size when you can:
    //   removes every growth-and-copy but the final toString().
    for (String row : rows) sb.append(row);
    //                         ^^^^^^ writes into SPARE CAPACITY in place. No copy.
    String result = sb.toString();      // exactly ONE copy, at the end

    // ── WHY DOUBLING MAKES IT LINEAR ────────────────────────────────────
    // ensureCapacity: newLength = value.length * 2 + 2   (the +2 lets a 0-length
    //                                                     buffer still grow)
    // growths copy 16, then 34, then 70, then 142 ... a geometric series that sums
    // to UNDER 2n. So the whole build copies < 2n characters no matter how many
    // appends. Same trick as ArrayList.add being amortised O(1).

    // ── THE STRAIGHT-LINE CASE: do NOT "fix" this ───────────────────────
    String s = "user=" + name + " id=" + id;        // ← CORRECT and usually FASTEST
    // On Java 9+ this is one invokedynamic that computes every operand's length
    // first and allocates the result once. Rewriting it as a StringBuilder chain
    // makes it slower AND less readable. The rule is about LOOPS.

    // ── CONCATENATION INSIDE AN APPEND ──────────────────────────────────
    sb.append("name=" + n + ";");     // builds a TEMPORARY string, then copies it in
    sb.append("name=").append(n).append(';');   // ← nothing extra allocated
    //                                 ^^^ note the CHAR literal: append(char) skips
    //                                 the string-length-and-copy path entirely.

    // ── THE LOG LINE THAT COSTS YOU WHEN DEBUG IS OFF ───────────────────
    log.debug("state " + expensive());
    // ^ ARGUMENTS ARE EVALUATED BEFORE THE CALL. The concatenation runs and
    //   expensive() runs, then the method returns immediately because debug is
    //   disabled. A real hot-path cost hiding behind a disabled log level.
    log.debug("state {}", value);      // ← formats ONLY if the level is enabled

    // ── DELIMITED OUTPUT: never hand-roll it ────────────────────────────
    for (String x : list) { sb.append(x).append(", "); }
    sb.setLength(sb.length() - 2);     // ← and this throws on an EMPTY list
    String.join(", ", list);                                  // correct, one line
    list.stream().map(X::name).collect(Collectors.joining(", "));  // with transform
    new StringJoiner(", ", "[", "]").setEmptyValue("[]");     // prefix/suffix/empty

    // ── AND THE FIX THAT IS BETTER THAN ANY OF THEM ─────────────────────
    try (var out = new BufferedWriter(new FileWriter(f))) {
        for (String row : rows) out.write(row);
    }   // ^ CONSTANT MEMORY. A 500 MB report built in a String is an OOM; streamed,
        //   it is a non-event. The best fix for a big concatenation is not to do it.""",

"""9. THE TRACE — the same build, three ways

APPENDING A 10-CHARACTER ROW 100,000 TIMES, producing a 1,000,000-character string. Counting characters
copied, which is arithmetic rather than a measurement:

    `+=` IN A LOOP
    iteration   accumulated length   characters copied this iteration
    ---------------------------------------------------------------------------
    1           0                    10        (copy 0 in, append 10, copy 10 out)
    1,000       10,000               ~20,000
    10,000      100,000              ~200,000
    100,000     1,000,000            ~2,000,000
    ---------------------------------------------------------------------------
    TOTAL ≈ 2 × Σ(10i) for i = 1..100,000 ≈ 100,000,000,000 characters copied,
    plus ~200,000 objects allocated, to produce 1,000,000 characters of output.

    StringBuilder, PRE-SIZED
    ---------------------------------------------------------------------------
    100,000 appends, each writing 10 characters into spare capacity   1,000,000
    one toString() copy                                               1,000,000
    TOTAL = 2,000,000 characters copied. Two objects allocated.

    StringBuilder, DEFAULT CAPACITY
    ---------------------------------------------------------------------------
    the same 1,000,000 appended, plus growth copies of
    16 + 34 + 70 + 142 + ... + ~1,048,576                            ≈ 2,000,000
    one toString() copy                                               1,000,000
    TOTAL ≈ 4,000,000. Still linear — the geometric series sums to under 2n.

    THE RATIO BETWEEN ROW 1 AND ROW 2 IS ABOUT 50,000 TO 1. And notice the shape: the quadratic version
    is not "slower per character", it is doing a fundamentally different amount of work, and the gap
    WIDENS with n. At 1,000 iterations it is 500x; at 100,000 it is 50,000x. WHICH IS WHY A SMALL
    BENCHMARK ACTIVELY MISLEADS.

WHAT THE COMPILER PRODUCED, per Java version — the part that explains why the optimisation does not
help:

    source                     Java 8 bytecode              Java 9+ bytecode
    ---------------------------------------------------------------------------------
    "a" + b + "c"              ONE StringBuilder chain      ONE invokedynamic, exact
    (straight line)            for the whole expression     size, single allocation
    result += row              a NEW StringBuilder,         a NEW invokedynamic call,
    (inside a loop)            EVERY ITERATION              EVERY ITERATION
    ---------------------------------------------------------------------------------
    BOTH ROWS ARE THE SAME OPTIMISATION. It is scoped to an expression, and the loop creates a new
    expression evaluation each time round. Nothing in either compiler can carry the buffer across
    iterations, because `result` is observable between them.

AND THE MEMORY TRACE, which is the failure people actually hit:

    approach                    peak heap for a 500 MB report
    ---------------------------------------------------------------------------------
    `+=` in a loop              ~1 GB live at the end (old + new during the last copy),
                                plus ~500 GB of cumulative garbage churned through GC
    StringBuilder               ~1 GB (the buffer plus the toString copy)
    stream to a BufferedWriter  ~8 KB
    ---------------------------------------------------------------------------------
    THE THIRD ROW IS THE REAL ANSWER FOR LARGE OUTPUT. StringBuilder fixes the time complexity and
    leaves the space complexity at O(n); writing as you go fixes both. The best version of this
    optimisation is noticing that the string never needed to exist.

WHAT PRODUCED WHAT:
    IMMUTABILITY             produced the copy-per-iteration, and therefore the whole problem.
    PER-EXPRESSION SCOPING   produced "the compiler optimises this and it does not help".
    GEOMETRIC GROWTH         produced the linear total in rows 2 and 3 — the same reason
                             `ArrayList.add` is amortised O(1).""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `+=` in a loop: O(n²) time in characters copied, O(n) garbage objects.
    `StringBuilder`: O(n) total, amortised O(1) per append; growth is `len * 2 + 2`, default
    capacity 16.
    Pre-sized `StringBuilder`: exactly one copy, in `toString()`.
    Straight-line `+` on Java 9+: one `invokedynamic`, result array sized exactly, one allocation —
    typically FASTER than a hand-written builder.
    `String.format`: parses the format string per call, roughly an order of magnitude slower than `+`.
    `String.join` / `Collectors.joining`: linear, and correct about separators.
    Streaming to a writer: O(1) space.

THE #1 MISTAKE: `+=` on a String inside a loop. Quadratic, and it is the most common genuine
performance defect in production Java.

THE #2 MISTAKE: concluding the compiler will fix it. It optimises the EXPRESSION, and the expression is
inside the loop.

THE #3 MISTAKE: over-correcting and rewriting straight-line `+` into StringBuilder. On Java 9+ that is
slower and less readable.

THE #4 MISTAKE: not pre-sizing when the size is known. About 17 growth cycles to reach a megabyte.

THE #5 MISTAKE: `sb.append(a + b)`. Builds a temporary and copies it in. Chain the appends.

THE #6 MISTAKE: unguarded concatenation in a log call. The string is built and the arguments evaluated
even when the level is disabled. Parameterised logging.

THE #7 MISTAKE: `String.format` in a hot loop.

THE #8 MISTAKE: hand-rolling delimited output and fixing up the trailing separator — which also throws
on an empty list. `String.join` or `Collectors.joining`.

THE #9 MISTAKE: `reduce("", String::concat)` in a stream. The same quadratic behaviour in functional
clothing. `Collectors.joining()`.

THE #10 MISTAKE: sharing a `StringBuilder` across threads, or reaching for `StringBuffer` as the fix —
per-method locking gives no atomicity across chained appends.

THE #11 MISTAKE: building a huge string in memory when it is going straight to a stream. Fixing the
time complexity while leaving the space complexity at O(n) is only half the fix.

THE #12 MISTAKE: benchmarking at a small n. The gap grows with n, so a small test says "it's fine" about
something that is not.

ONE-SENTENCE TAKEAWAY: strings are immutable, so `result += row` cannot append — it copies the entire
accumulated string into a fresh buffer and then out again, twice per iteration, making the loop O(n²)
and turning a hundred thousand appends into roughly a hundred billion character copies; the compiler's
concatenation optimisation is real (and on Java 9+ an `invokedynamic` that sizes the result exactly,
which is why straight-line `+` should be left alone) but it is scoped to an EXPRESSION and cannot cross
a loop boundary, so the fix is to hoist a `StringBuilder` out of the loop and pre-size it — or better,
for large output, to stream it to a writer and never build the string at all.""",
]


DEEP["ConcurrentModificationException — why removing inside a for-each throws"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the exception with the misleading name

    for (String s : list) {
        if (s.isEmpty()) list.remove(s);
    }
    →  ConcurrentModificationException

    THERE IS ONE THREAD. Nothing is concurrent. The name is about CONCURRENT MODIFICATION AND
    ITERATION — two things happening to the same collection at overlapping times — not about threads,
    and that misnaming sends people looking for a threading bug that does not exist.

WHY IT IS NOT SIMPLY ALLOWED. An iterator holds a POSITION in the collection — for an ArrayList, an
index. Remove an element and everything after it shifts down by one. The iterator's index now points
one place further along than it did logically, so the NEXT element is skipped. Add an element and
something may be visited twice, or the index may run off the end.

    THE COLLECTION COULD JUST LET THAT HAPPEN AND RETURN WRONG ANSWERS SILENTLY. Instead it keeps a
    counter of structural changes, the iterator records what that counter was when it started, and it
    checks on every step. A mismatch means "the ground moved under you", and it throws.

    SO THE EXCEPTION IS A FEATURE. It converts a silent wrong answer into a loud stack trace pointing
    at the exact line. THE ALTERNATIVE IS NOT "IT WORKS" — the alternative is a loop that quietly
    skipped half your data.

THE EVERYDAY VERSION: reading down a numbered list while someone removes rows above your finger. You
are on line 7; a row is deleted; what was line 8 is now line 7, and moving to line 8 skips it entirely.
The list is not corrupt and your finger is not wrong — the two are just no longer talking to each other.

TERMS AS THEY APPEAR:
- STRUCTURAL MODIFICATION: a change to the SIZE — adding or removing. Replacing a value is not one.
- FAIL-FAST: detect the problem immediately rather than producing wrong results.
- modCount: the collection's counter of structural modifications.
- expectedModCount: the snapshot the iterator took when it was created.""",

"""2. THE INTUITION — fail-fast is a bug detector, not a guarantee

THE MECHANISM IS FOUR LINES OF CODE, and knowing them removes all the mystery:

    IN THE COLLECTION:   `protected transient int modCount;`  incremented by every add and remove.
    IN THE ITERATOR:     `int expectedModCount = modCount;`   captured at creation.
    IN `next()`:         `if (modCount != expectedModCount) throw new ConcurrentModificationException();`
    IN `Iterator.remove()`: performs the removal AND THEN sets `expectedModCount = modCount`.

    THAT LAST LINE IS THE WHOLE REASON `Iterator.remove()` IS THE LEGAL WAY TO DO THIS. It is not a
    special case in the checking; it is the one removal path that also updates the iterator's idea of
    the world, because it is the only one that knows how to fix the cursor too.

NOW THE PART THAT MATTERS MOST AND IS ALMOST NEVER SAID: FAIL-FAST IS EXPLICITLY BEST-EFFORT.

    The Javadoc says so directly: "this behaviour cannot be guaranteed... Fail-fast iterators throw
    ConcurrentModificationException ON A BEST-EFFORT BASIS. Therefore, it would be wrong to write a
    program that depended on this exception for its correctness: IT SHOULD BE USED ONLY TO DETECT BUGS."

    SO IT IS A DEBUGGING AID, NOT A SAFETY MECHANISM. Which has a sharp consequence: there are cases
    where you modify during iteration and NOTHING THROWS, and you get the silent wrong answer after
    all.

AND HERE IS THE BEST EXAMPLE OF THAT, WHICH IS ALSO THE SINGLE MOST USEFUL FACT IN THIS ENTRY:

    REMOVING THE SECOND-TO-LAST ELEMENT OF AN ArrayList IN A FOR-EACH DOES NOT THROW.

    Because `ArrayList.Itr.hasNext()` is `return cursor != size;` — it does not call
    `checkForComodification`. Walk through a three-element list removing element index 1: after the
    removal, `size` is 2 and `cursor` is 2, so `hasNext()` returns FALSE, the loop ends normally, and
    the last element WAS NEVER VISITED. No exception. No warning. An element silently skipped.

    THAT IS THE WHOLE ARGUMENT AGAINST TREATING THE EXCEPTION AS YOUR SAFETY NET. The check runs in
    `next()`, and the loop can exit without ever calling `next()` again. `list.remove(x)` in a for-each
    is a bug whether or not it throws — and on the exact input where it does not throw, it is worse.

THE DESIGN TRADE-OFF BEHIND ALL OF THIS: a truly correct check would cost synchronisation on every
access, which is far too expensive for a collection that is usually used by one thread. So the JDK
chose a cheap heuristic that catches the common cases loudly and misses the rare ones. KNOWING WHICH
ONES IT MISSES IS WHAT SEPARATES UNDERSTANDING FROM MEMORISING.""",

"""3. THE MECHANISM — what counts as structural, and what the alternatives actually do

WHAT INCREMENTS `modCount` — the answer is narrower than people assume:

    ADDING an element                            YES
    REMOVING an element                          YES
    `clear()`                                    YES
    `list.set(i, x)` — REPLACING a value         NO. Size unchanged, no structural modification.
    `map.put(EXISTING_KEY, newValue)`            NO — in HashMap, replacing a value does not touch
                                                 modCount, so this IS legal during iteration.
    `map.put(NEW_KEY, value)`                    YES — it adds an entry.
    `entry.setValue(v)` during map iteration     NO. This is the SUPPORTED way to modify values while
                                                 iterating a map, and it is underused.

    THAT DISTINCTION IS WORTH KNOWING PRECISELY, because "you can't modify a collection while iterating
    it" is the folk version and it is wrong. You cannot STRUCTURALLY modify it. Updating values in
    place is fine and always was.

FOR-EACH IS AN ITERATOR. The syntax hides it, which is why the exception seems to come from nowhere:

    for (String s : list) { ... }
    // compiles to exactly:
    for (Iterator<String> it = list.iterator(); it.hasNext(); ) {
        String s = it.next();          // ← the check lives HERE
        ...
    }

    Once you see that, `it.remove()` stops looking like an obscure API and starts looking like the
    obvious one: you already have the iterator, you just could not see it.

THE ALTERNATIVES, and what each one really does:

    `Iterator.remove()`         removes AND resynchronises expectedModCount AND fixes the cursor. The
                                classical answer. O(n) per removal on an ArrayList.
    `removeIf(predicate)`       ONE compacting pass. It marks survivors in a bit set, then moves them
                                down once, then bumps modCount once. O(n) TOTAL regardless of how many
                                are removed — algorithmically better than an iterator loop, and
                                clearer. THE MODERN ANSWER.
    ITERATE A COPY              `for (String s : new ArrayList<>(list)) list.remove(s);` — the iterator
                                walks the copy, so no check fires. Correct, and it allocates.
    COLLECT-THEN-REMOVE         gather the doomed elements in one pass, `list.removeAll(doomed)` after.
                                Clear, and `removeAll` on a large list is O(n·m) unless the argument is
                                a Set.
    A REVERSE INDEXED LOOP      `for (int i = size-1; i >= 0; i--)`. No iterator, so no check, and going
                                backwards means removals do not disturb the indices ahead of you.
    CONCURRENT COLLECTIONS      see the next paragraph — they never throw at all.

WHY `ConcurrentHashMap` AND `CopyOnWriteArrayList` NEVER THROW THIS:

    `CopyOnWriteArrayList` iterates a SNAPSHOT of the array taken when the iterator was created. Later
    writes replace the array wholesale, so the iterator simply does not see them — and `it.remove()`
    throws `UnsupportedOperationException`, because there is nothing meaningful to remove from a
    snapshot.
    `ConcurrentHashMap` iterators are WEAKLY CONSISTENT: they never throw, they reflect the state at
    some point at or after creation, and they may or may not show changes made during iteration. YOU
    TRADE A GUARANTEE FOR THE ABSENCE OF AN EXCEPTION, which is the right trade for concurrent code and
    the wrong one for finding a bug in single-threaded code.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `list.remove(x)` INSIDE A FOR-EACH. The canonical case. Throws on the next `next()`.

CASE 2 — REMOVING THE SECOND-TO-LAST ELEMENT. DOES NOT THROW, and silently skips the last element,
because `hasNext()` is `cursor != size` and does not check. The most important edge case here.

CASE 3 — REMOVING THE LAST ELEMENT. Also does not throw, for the same reason — the loop just ends.

CASE 4 — ADDING DURING ITERATION. Throws the same exception, and `Iterator` has no `add`. `ListIterator`
does, and it is the supported route.

CASE 5 — `map.put(existingKey, v)` DURING ITERATION IS LEGAL for HashMap; `map.put(newKey, v)` is not.
Two lines that look identical behave differently based on the data.

CASE 6 — MODIFYING A `subList` OR THE LIST BEHIND IT. `subList` is a VIEW; structurally modifying the
parent invalidates the view, and the next use throws — often far from the line that caused it.

CASE 7 — `Collections.unmodifiableList(x)` DOES NOT COPY. It is a view. Someone still holding the
original can modify it, and your iteration over the "unmodifiable" wrapper will throw.

CASE 8 — TWO THREADS, ONE PLAIN COLLECTION. This is what the name suggests and it is the case the
mechanism handles WORST: `modCount` is not volatile, so the check may or may not fire, and the real
problem is that an unsynchronised `ArrayList` under concurrent write can corrupt internally in ways no
exception describes.

CASE 9 — A STREAM OVER A LIST YOU THEN MODIFY. Streams are lazy: the source is not touched until the
terminal operation, so the exception surfaces from `collect` or `forEach` and the stack trace points
nowhere near the mutation.

CASE 10 — REMOVING FROM `keySet()` OR `entrySet()` DURING ITERATION. Those are views onto the map, so
`it.remove()` on the view is legal and correct, while `map.remove(k)` in the same loop is not.

CASE 11 — NESTED ITERATION OVER THE SAME LIST, where the inner loop modifies. The outer iterator throws
later, at a line that looks innocent.

CASE 12 — RELYING ON THE EXCEPTION. The Javadoc explicitly says not to. It is for detecting bugs, never
for program logic.""",

"""5. THE ALTERNATIVES — how to actually remove things

`removeIf(predicate)` — THE DEFAULT ANSWER on Java 8+:

    list.removeIf(String::isEmpty);
    map.values().removeIf(v -> v.isExpired());
    map.entrySet().removeIf(e -> e.getKey().startsWith("tmp"));

    One pass, correct by construction, and on an `ArrayList` it compacts once rather than shifting per
    removal — so it is O(n) total where an iterator loop is O(n·k). It reads as the intent rather than
    as the mechanism.

`Iterator.remove()` — when the decision needs more than a predicate, or you need to do something else
with the removed element on the way out.

`ListIterator` — when you need to ADD or REPLACE during the walk, not just remove. It is the only
supported way to insert while iterating.

A REVERSE INDEXED LOOP — no iterator exists, so nothing can be invalidated, and removals do not disturb
the indices you have not reached yet. Ugly, and genuinely the simplest correct thing in some code.

COLLECT-THEN-ACT — two passes, and often the clearest for a complex condition:
    `var doomed = list.stream().filter(...).collect(toSet()); list.removeAll(doomed);`
    Make the argument a `Set`, or `removeAll` is O(n·m).

A NEW COLLECTION INSTEAD OF MUTATION — `list.stream().filter(...).toList()`. Often the best answer,
because the original never changes and there is nothing to invalidate. IF NOTHING ELSE HOLDS A
REFERENCE TO THE OLD LIST, THIS IS SIMPLER THAN EVERY OPTION ABOVE.

CONCURRENT COLLECTIONS, when the modification genuinely comes from another thread:
    `ConcurrentHashMap` — weakly consistent iterators, never throws, and `compute`/`merge` do
    read-modify-write atomically.
    `CopyOnWriteArrayList` — snapshot iterators. Perfect for listener lists, terrible for write-heavy
    use, since every write copies the whole array.
    `ConcurrentLinkedQueue`, `ConcurrentSkipListMap` — the same philosophy for other shapes.
    NOTE WHAT YOU GIVE UP: these do not throw because they do not promise a consistent view. If you are
    single-threaded, switching to one of these to silence the exception hides a real bug.

WHAT TO SAY: "`removeIf` in almost every case — one pass, O(n) on an ArrayList, and it states the
intent. `Iterator.remove` when the condition is more involved, and a filtered copy when nothing else
holds the original. I would not switch to a concurrent collection just to stop the exception: if it is
single-threaded, that exception was telling the truth."

""",

"""6. HOW TO HANDLE IT — numbered steps

STEP 1 — CHECK WHETHER IT IS ACTUALLY MULTI-THREADED. The name says concurrent; ninety percent of the
time there is one thread and the fix is local.

STEP 2 — USE `removeIf`. One line, one pass, and correct by construction.

STEP 3 — IF THE LOGIC IS TOO COMPLEX FOR A PREDICATE, USE `Iterator.remove()` EXPLICITLY. Write the
`while (it.hasNext())` loop rather than the for-each, so the iterator is visible.

STEP 4 — IF YOU NEED TO ADD OR REPLACE, USE A `ListIterator`. `Iterator` has no `add`.

STEP 5 — FOR MAPS, REMEMBER `entry.setValue(v)` IS LEGAL during iteration, and so is
`map.put(existingKey, v)`. Only adding a NEW key is structural.

STEP 6 — CONSIDER BUILDING A NEW COLLECTION INSTEAD. `stream().filter(...).toList()` avoids the whole
class of problem when nothing else holds the original.

STEP 7 — DO NOT SWITCH TO A CONCURRENT COLLECTION TO SILENCE IT. In single-threaded code that hides the
bug rather than fixing it.

STEP 8 — IF IT IS GENUINELY MULTI-THREADED, PICK A REAL STRATEGY: `ConcurrentHashMap`,
`CopyOnWriteArrayList`, or external synchronisation across the WHOLE iteration —
`Collections.synchronizedList` locks individual methods, NOT the loop.

STEP 9 — TREAT A NON-THROWING MODIFICATION AS EQUALLY BROKEN. Removing the second-to-last element
silently skips the last. Absence of the exception is not evidence of correctness.

STEP 10 — WATCH FOR VIEWS. `subList`, `keySet`, `values`, `unmodifiableList` all alias the original, and
the exception can surface far from the mutation.

STEP 11 — WITH STREAMS, REMEMBER LAZINESS. The exception comes from the terminal operation, so read the
whole pipeline rather than the line in the trace.

STEP 12 — NEVER WRITE LOGIC THAT DEPENDS ON THE EXCEPTION. The Javadoc says it is best-effort and for
bug detection only.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'First, the name is misleading. There's usually one thread. "Concurrent" here means concurrent
MODIFICATION AND ITERATION — two things happening to the collection at overlapping times — not
threading. People go hunting for a race that doesn't exist.

The reason it can't just be allowed: an iterator holds a POSITION. For an ArrayList that's an index.
Remove an element and everything after it shifts down one, so the iterator's index now points one
further along than it did logically, and the next element gets skipped. The collection could let that
happen and hand you wrong answers silently. Instead it keeps a counter of structural changes, the
iterator snapshots that counter when it's created, and next() compares them.

So the exception is a FEATURE. It turns a silent wrong answer into a stack trace pointing at the exact
line. The alternative isn't "it works" — it's a loop that quietly skipped half your data.

The mechanism is four lines. modCount on the collection, expectedModCount on the iterator, a comparison
in next(), and Iterator.remove() updating expectedModCount after it removes. That last one is the whole
reason Iterator.remove is the legal path — it's not special-cased in the check, it's just the only
removal that also fixes the iterator's view and the cursor.

Now the thing I'd make sure to say, because it's the difference between understanding it and having
memorised it: fail-fast is explicitly BEST-EFFORT. The Javadoc says outright that you must not write a
program depending on this exception for correctness — it exists only to detect bugs.

And the example that proves it: removing the SECOND-TO-LAST element of an ArrayList in a for-each does
NOT throw. Because hasNext() is just "cursor != size" and doesn't check anything. Remove index 1 of a
three-element list: size becomes 2, cursor is 2, hasNext returns false, the loop ends normally — and
the last element was never visited. No exception, no warning, an element silently skipped. Which means
list.remove(x) inside a for-each is a bug whether or not it throws, and on the exact input where it
doesn't throw, it's worse.

One precision point people get wrong: it's not "you can't modify while iterating", it's you can't
STRUCTURALLY modify. list.set(i, x) is fine. entry.setValue(v) during map iteration is fine and is the
supported way to update values. And map.put on an EXISTING key doesn't touch modCount, so that's legal
too — while put on a new key isn't. Two lines that look identical, differing on the data.

Practically I'd reach for removeIf. One pass, and on an ArrayList it compacts once rather than shifting
per removal, so it's O(n) total where an iterator loop is O(n·k). Iterator.remove when the condition is
more involved, ListIterator if I need to add. And I would NOT switch to ConcurrentHashMap just to make
the exception go away — those don't throw because they don't promise a consistent view, so in
single-threaded code that's hiding the bug rather than fixing it.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT FOR-EACH ACTUALLY IS ───────────────────────────────────────
    for (String s : list) { if (s.isEmpty()) list.remove(s); }
    // compiles to:
    for (Iterator<String> it = list.iterator(); it.hasNext(); ) {
        String s = it.next();        // ← THE CHECK LIVES HERE, and only here
        if (s.isEmpty()) list.remove(s);   // ← bumps modCount behind the iterator's back
    }
    // Once you see the iterator, `it.remove()` stops looking obscure.

    // ── THE ENTIRE MECHANISM, FOUR LINES ────────────────────────────────
    // In ArrayList:
    protected transient int modCount;          // ++ on every add and remove
    // In ArrayList.Itr:
    int expectedModCount = modCount;           // snapshot at iterator creation
    final void checkForComodification() {
        if (modCount != expectedModCount) throw new ConcurrentModificationException();
    }
    public void remove() {
        ArrayList.this.remove(lastRet);
        cursor = lastRet;                      // ← fix the CURSOR too
        expectedModCount = modCount;           // ← RESYNCHRONISE. This is the whole
    }                                          //   reason it.remove() is legal.

    // ── THE CASE THAT DOES NOT THROW — and is worse ─────────────────────
    public boolean hasNext() { return cursor != size; }
    //                                ^^^^^^^^^^^^^^ NO checkForComodification.
    var list = new ArrayList<>(List.of("a", "b", "c"));
    for (String s : list) { if (s.equals("b")) list.remove(s); }
    System.out.println(list);        // [a, c] — and "c" WAS NEVER VISITED
    //   after removing "b": size = 2, cursor = 2 → hasNext() is false → loop ends
    //   NO EXCEPTION. NO WARNING. An element silently skipped. This is why the
    //   absence of the exception proves nothing.

    // ── WHAT IS AND IS NOT "STRUCTURAL" ─────────────────────────────────
    for (var e : map.entrySet()) {
        e.setValue(e.getValue() + 1);        // ✓ LEGAL — updates a value in place
        map.put(e.getKey(), 99);             // ✓ LEGAL — existing key, no modCount++
        map.put("brandNewKey", 1);           // ✗ THROWS — adds an entry
        map.remove(e.getKey());              // ✗ THROWS — use it.remove()
    }
    for (int i = 0; i < list.size(); i++) list.set(i, list.get(i) + "!");  // ✓ fine
    // "You can't modify while iterating" is the folk version. STRUCTURALLY is the word.

    // ── THE FOUR CORRECT FIXES ──────────────────────────────────────────
    list.removeIf(String::isEmpty);
    // ^ ONE compacting pass: marks survivors in a bit set, moves them down once,
    //   bumps modCount once. O(n) TOTAL. An iterator loop is O(n) PER removal.

    var it = list.iterator();
    while (it.hasNext()) { if (complexCheck(it.next())) it.remove(); }

    for (int i = list.size() - 1; i >= 0; i--)      // backwards: removals never
        if (bad(list.get(i))) list.remove(i);       // disturb the indices ahead

    List<String> kept = list.stream().filter(s -> !s.isEmpty()).toList();
    // ^ often the best: the original is never mutated, so nothing can be invalidated

    // ── AND WHAT THE CONCURRENT COLLECTIONS TRADE AWAY ──────────────────
    var chm = new ConcurrentHashMap<>(map);
    for (var e : chm.entrySet()) chm.put("new", 1);   // never throws
    // ^ WEAKLY CONSISTENT: it reflects the state at SOME point at or after creation,
    //   and may or may not show your change. It does not throw because it does not
    //   PROMISE a consistent view. In single-threaded code that hides the bug.""",

"""9. THE TRACE — three removals, three different outcomes

LIST = ["a", "b", "c", "d"], for-each, removing one element. Follow `cursor`, `size` and `modCount`:

    REMOVING "a" (index 0) — the throwing case
    step  call            cursor  size  modCount  expected  outcome
    ---------------------------------------------------------------------------------
    1     hasNext()       0       4     0         0         0 != 4 → true
    2     next() → "a"    1       4     0         0         check passes
    3     list.remove     1       3     1         0         ← THE GROUND MOVED
    4     hasNext()       1       3     1         0         1 != 3 → true
    5     next()          —       —     1         0         1 != 0 → THROWS
    ---------------------------------------------------------------------------------
    LOUD, IMMEDIATE, AND POINTING AT THE RIGHT LINE. This is the mechanism working.

    REMOVING "c" (the SECOND-TO-LAST) — the silent case
    step  call            cursor  size  modCount  expected  outcome
    ---------------------------------------------------------------------------------
    1-4   ... reaches "c" 3       4     0         0         check passes
    5     list.remove     3       3     1         0         ground moved
    6     hasNext()       3       3     1         0         3 != 3 → FALSE
    7     loop EXITS      —       —     —         —         NO CHECK EVER RUNS
    ---------------------------------------------------------------------------------
    "d" WAS NEVER VISITED. No exception, no warning, the list is ["a","b","d"] and one element was
    silently skipped. `hasNext()` does not call `checkForComodification`, and the loop ended without
    calling `next()` again — so the detector never fired.

    REMOVING "d" (the LAST) — loud again, and that is the point
    ---------------------------------------------------------------------------------
    next() returns "d" and leaves cursor at 4. The removal drops size to 3. Now
    hasNext() is 4 != 3 → TRUE, so next() IS called, the check runs, and it THROWS.
    Removing the last element throws; removing the one before it does not. WHETHER
    YOU GET AN EXCEPTION DEPENDS ON WHICH ELEMENT YOU REMOVED.

    THE POINT OF THE THREE TRACES TOGETHER: the same mistake produces a loud exception, a silent skip,
    or a loud exception again, depending entirely on the position of the element. THAT IS WHY THE
    JAVADOC SAYS NOT TO DEPEND ON IT. It is a smoke alarm that works most of the time, and "the alarm
    did not go off" is not a fire safety certificate.

NOW THE CORRECT VERSIONS, traced:

    Iterator.remove() on "b"
    step  call             cursor  size  modCount  expected  outcome
    ---------------------------------------------------------------------------------
    1     next() → "b"     2       4     0         0         ok
    2     it.remove()      1       3     1         1         ← BOTH updated. cursor
                                                              moved BACK to lastRet,
                                                              expected resynchronised
    3     hasNext()        1       3     1         1         continues correctly
    4     next() → "c"     2       3     1         1         NOTHING SKIPPED
    ---------------------------------------------------------------------------------
    Two things were fixed, not one. The counter AND the cursor. That is the difference.

    removeIf(pred) over a 1,000-element list removing 500
    ---------------------------------------------------------------------------------
    pass 1   evaluate the predicate for each element, record survivors in a BitSet
    pass 2   shift survivors down in ONE arraycopy-driven compaction
    then     modCount++ ONCE
    total    O(n). An iterator loop would be O(n) per removal — 500 × O(n) = O(n·k).
    ---------------------------------------------------------------------------------
    So `removeIf` is not merely tidier. It is asymptotically better on an ArrayList, which is the part
    that usually goes unmentioned.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    The check is one integer comparison in `next()`. Effectively free.
    `Iterator.remove()` on an ArrayList: O(n) per call, so O(n·k) for k removals.
    `removeIf` on an ArrayList: O(n) TOTAL for any number of removals — one compacting pass.
    `LinkedList` + `Iterator.remove()`: O(1) per removal, though the walk still dominates.
    `CopyOnWriteArrayList`: iteration never throws; every WRITE copies the whole array.
    `ConcurrentHashMap`: weakly consistent iteration, never throws, no consistent-view promise.
    `modCount` is not volatile — so across threads the check is unreliable in both directions.

THE #1 MISTAKE: reading the name as "threading problem". Usually one thread.

THE #2 MISTAKE: believing the absence of the exception means the code is correct. Removing the
second-to-last element silently skips the last.

THE #3 MISTAKE: "you cannot modify a collection while iterating". You cannot STRUCTURALLY modify it —
`set`, `entry.setValue` and `put` on an existing key are all fine.

THE #4 MISTAKE: switching to a concurrent collection to make the exception stop. In single-threaded
code that hides a real bug behind a weaker guarantee.

THE #5 MISTAKE: an iterator-remove loop where `removeIf` belongs. O(n·k) instead of O(n).

THE #6 MISTAKE: expecting `Iterator.add`. It does not exist; `ListIterator` has it.

THE #7 MISTAKE: forgetting that `subList`, `keySet`, `values` and `unmodifiableList` are VIEWS. The
exception can appear far from the mutation.

THE #8 MISTAKE: `Collections.synchronizedList` for concurrent iteration. It locks individual methods,
not the loop; you must synchronise on the list across the whole iteration yourself.

THE #9 MISTAKE: modifying the source of a stream. Laziness means the exception surfaces from the
terminal operation, pointing away from the cause.

THE #10 MISTAKE: `map.remove(k)` inside an `entrySet()` loop. Use `it.remove()` on the view, or
`entrySet().removeIf(...)`.

THE #11 MISTAKE: writing logic that catches and depends on it. Explicitly documented as best-effort and
for bug detection only.

ONE-SENTENCE TAKEAWAY: the collection counts structural modifications and every iterator snapshots that
counter, so `next()` can refuse to continue once the ground has moved — turning a silently skipped
element into a loud stack trace — but the check runs ONLY in `next()`, which is why removing the
second-to-last element of an ArrayList ends the loop without throwing and silently skips the last one;
fail-fast is documented as best-effort and for detecting bugs, never for logic, so the fix is
`removeIf` (one compacting pass, O(n) total rather than O(n·k)), `Iterator.remove` when the condition
is complex, or building a filtered copy — and never a concurrent collection chosen merely to make the
exception stop.""",
]


DEEP["Checked vs unchecked — and why the distinction is contested"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the one thing the compiler forces you to think about

Java splits failures in two. For SOME of them the compiler will not let you ignore the possibility: you
must either catch it, or declare that your method can throw it too. For the rest, you may ignore it
entirely and the code compiles.

    CHECKED — `IOException`, `SQLException`, `InterruptedException`. The compiler enforces "catch or
    specify". These are things that can go wrong even when your code is perfect: the network is down,
    the disk is full, the file was deleted between checking and opening.

    UNCHECKED — `NullPointerException`, `IllegalArgumentException`, `IndexOutOfBoundsException` and
    everything else extending `RuntimeException`. No enforcement. These are meant to signal a BUG:
    something the caller could have prevented by not passing null, not indexing past the end, not
    calling `next()` on an exhausted iterator.

    THE INTENDED RULE IS THEREFORE ABOUT WHO IS AT FAULT AND WHAT THEY CAN DO. Checked = "the world
    misbehaved, and you might reasonably recover — retry, fall back, tell the user". Unchecked = "the
    program is wrong, and there is nothing to recover; fix the code".

    AND THE HONEST ANSWER TO THE INTERVIEW QUESTION IS THAT THIS IS A CONTESTED DESIGN, not settled
    knowledge. Java is the ONLY mainstream language that has checked exceptions. C#, Kotlin, Scala,
    Python, Go, Rust, JavaScript, Swift — every one of them looked at the idea and declined. That is
    worth being able to explain rather than recite.

THE EVERYDAY VERSION: a form with a mandatory field. It guarantees the box is filled in. It does not
guarantee it is filled in THOUGHTFULLY — and if the box is mandatory on hundreds of forms, most people
will start writing "n/a". `catch (IOException e) { }` is the "n/a" of Java, and it exists in enormous
quantities.

TERMS AS THEY APPEAR:
- CATCH OR SPECIFY: the compiler rule for checked exceptions.
- `Throwable` → `Error` (unchecked) and `Exception` → `RuntimeException` (unchecked) plus everything
  else under `Exception` (checked).
- STACK TRACE: the record of where it happened, captured at construction, not at throw.""",

"""2. THE INTUITION — the argument for, and the two arguments against

THE ARGUMENT FOR, and it is a good one: A CHECKED EXCEPTION IS COMPILER-ENFORCED DOCUMENTATION.

    `Files.readString(path)` declares `throws IOException`, so you cannot write code that forgets the
    disk might fail. The failure mode is in the TYPE, not in a comment nobody reads. Nothing else in
    Java makes a caller acknowledge a possibility. Contrast C#, where any method might throw anything
    and you find out in production.

THE FIRST ARGUMENT AGAINST — THEY DO NOT COMPOSE, and this one is decisive in modern Java:

    `Function<T, R>` declares `R apply(T t)` — no `throws`. So a lambda passed to `map` CANNOT throw a
    checked exception. Neither can one passed to `forEach`, `Optional.map`, `CompletableFuture.thenApply`,
    or any other functional interface in the JDK.

    THE RESULT IS THE UGLIEST CODE IN MODERN JAVA:
        list.stream().map(p -> { try { return Files.readString(p); }
                                 catch (IOException e) { throw new UncheckedIOException(e); } })
    A try/catch inside a lambda whose entire purpose is to convert a checked exception into an
    unchecked one so it can escape. THE LANGUAGE ADDED `UncheckedIOException` TO THE JDK SPECIFICALLY
    TO MAKE THIS POSSIBLE — which is the standard library conceding the point.

THE SECOND ARGUMENT AGAINST — VERSIONING:

    Adding a checked exception to an existing method BREAKS EVERY CALLER. It is a source-incompatible
    change. So library authors, quite rationally, never add one — and instead either use unchecked
    exceptions from the start or declare an over-broad one early "just in case". Anders Hejlsberg made
    exactly this argument when explaining why C# has none.

AND THE EMPIRICAL ARGUMENT, which is the one that actually persuades people: LOOK AT WHAT DEVELOPERS DO
WHEN FORCED.

    `catch (IOException e) { }` — the empty catch. The compiler demanded a decision; the developer did
    not want to make one; the worst possible answer satisfies the compiler. THE ENFORCEMENT PRODUCED A
    SILENTLY SWALLOWED FAILURE, which is strictly worse than no enforcement, because now the stack
    trace is gone too.
    `catch (Exception e) { throw new RuntimeException(e); }` — the reflexive wrap, which erases the
    type distinction the mechanism existed to create.
    `throws Exception` on every method — the checked-exception equivalent of `Object`.

WHERE THE CONSENSUS LANDED IN PRACTICE. Spring wraps every `SQLException` into an unchecked
`DataAccessException` hierarchy, and considers this one of its selling points. Hibernate did the same.
Kotlin has checked exceptions in the type system for interoperability but ENFORCES NOTHING. THE
ECOSYSTEM VOTED, over about twenty years, and it voted against enforcement while keeping the idea that
exception TYPES should be meaningful.""",

"""3. THE MECHANISM — the hierarchy, the rules, and what a throw actually costs

THE HIERARCHY, which is the thing to be able to draw:

    Throwable
    ├── Error                    UNCHECKED. The JVM is in trouble: OutOfMemoryError,
    │                            StackOverflowError, NoClassDefFoundError. Do not catch.
    └── Exception                CHECKED (everything except the branch below)
        ├── IOException, SQLException, InterruptedException, ClassNotFoundException...
        └── RuntimeException     UNCHECKED. NullPointerException, IllegalArgumentException,
                                 IllegalStateException, IndexOutOfBoundsException,
                                 ClassCastException, NumberFormatException, ArithmeticException

    THE RULE IS PURELY STRUCTURAL: unchecked means "is an `Error` or a `RuntimeException`". Everything
    else under `Throwable` is checked. There is no annotation and no keyword — it is inheritance.

THE COMPILER RULES:
    A method must DECLARE any checked exception it can throw, or catch it.
    An OVERRIDING method may declare FEWER or NARROWER checked exceptions than the one it overrides —
    never more. Which is why `Runnable.run()`, declaring none, cannot be implemented by anything that
    throws a checked exception.
    UNREACHABLE CATCH IS A COMPILE ERROR for checked exceptions — catching `IOException` where none can
    be thrown does not compile. Catching `Exception` or an unchecked type always does.

THREE FEATURES WORTH KNOWING BY NAME:

    MULTI-CATCH (Java 7): `catch (IOException | SQLException e)`. The variable is implicitly final and
    its static type is the least upper bound.
    MORE PRECISE RETHROW (Java 7): if you `catch (Exception e) { throw e; }` and the try block can only
    throw `IOException`, the compiler INFERS that and lets you declare `throws IOException` rather than
    `throws Exception`.
    SUPPRESSED EXCEPTIONS: in try-with-resources, if the body throws AND `close()` throws, the body's
    exception propagates and `close()`'s is attached via `addSuppressed`. Before Java 7, the manual
    finally-block version LOST the original exception entirely — this is the single most valuable thing
    try-with-resources fixed.

WHAT A THROW ACTUALLY COSTS, because "exceptions are slow" is half-true and the half matters:

    THE EXPENSIVE PART IS `fillInStackTrace()`, called by the `Throwable` CONSTRUCTOR — it walks the
    entire stack. Throwing and catching, once the object exists, is comparable to a branch.
    So an exception constructed and thrown from deep in a call stack costs microseconds; a
    pre-allocated exception, or one created with the four-argument constructor and
    `writableStackTrace = false`, costs almost nothing.
    THE JIT ALSO OPTIMISES REPEATED IMPLICIT EXCEPTIONS: after enough NullPointerExceptions from the
    same site, HotSpot may recompile it to throw a PRE-ALLOCATED exception with NO STACK TRACE AT ALL.
    That is the origin of the mystifying production log showing `java.lang.NullPointerException` with
    an empty trace — the JVM optimised the trace away because the site was hot.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — THE EMPTY CATCH BLOCK. `catch (IOException e) { }`. The failure is now invisible AND the stack
trace is destroyed. The single most damaging pattern in Java error handling, and checked exceptions are
what pressure people into it.

CASE 2 — WRAPPING WITHOUT THE CAUSE. `throw new RuntimeException("failed")` instead of
`throw new RuntimeException("failed", e)`. The original stack trace is gone and the log says only
"failed". ALWAYS PASS THE CAUSE.

CASE 3 — SWALLOWING `InterruptedException`. Catching it clears the interrupt flag, so the thread can
never be cancelled. Rethrow, or restore with `Thread.currentThread().interrupt()`. THIS ONE BREAKS
`shutdownNow` AND EVERY CANCELLATION MECHANISM IN THE JDK.

CASE 4 — `catch (Exception e)` THAT ALSO CATCHES RUNTIME EXCEPTIONS. Your handler written for I/O
failure now also swallows every NullPointerException in the block, turning a bug into a "handled error".

CASE 5 — `catch (Throwable t)`. Now you have caught `OutOfMemoryError` and `StackOverflowError` too,
and the JVM continues in an undefined state.

CASE 6 — `return` INSIDE `finally`. It DISCARDS an in-flight exception and any earlier return value.
The exception simply disappears. Compilers warn; the code still runs.

CASE 7 — A `finally` BLOCK THAT THROWS. Same effect: it replaces the original exception. This is why
try-with-resources uses `addSuppressed` rather than letting `close()` win.

CASE 8 — CHECKED EXCEPTIONS IN LAMBDAS. Not possible; the functional interfaces do not declare them. The
whole ecosystem of "unchecked function" wrappers exists because of this.

CASE 9 — `throws Exception` ON A PUBLIC API. Conveys nothing, forces every caller to catch everything,
and prevents more-precise rethrow from helping.

CASE 10 — CATCHING A SUPERCLASS BEFORE A SUBCLASS. `catch (Exception e)` before `catch (IOException e)`
is a compile error for exactly this reason — but with unchecked types the ordering mistake compiles and
the second block silently never runs.

CASE 11 — EXCEPTIONS FOR CONTROL FLOW. `catch (NumberFormatException e) { return default; }` inside a
tight loop costs a stack walk per iteration. Use a check, or a parser that returns an `Optional`.

CASE 12 — AN EMPTY STACK TRACE IN PRODUCTION. Not a logging bug — the JIT optimised a hot implicit
exception into a pre-allocated one. `-XX:-OmitStackTraceInFastThrow` restores it while diagnosing.

CASE 13 — SNEAKY THROWS. A generics trick (or Lombok's `@SneakyThrows`) lets you throw a checked
exception without declaring it, because erasure means the cast is unchecked at runtime. It compiles, it
works, and it defeats the entire mechanism — which is itself an argument about how load-bearing the
mechanism really is.""",

"""5. THE ALTERNATIVES — how other languages and modern Java handle it

WHAT EVERY OTHER LANGUAGE DID:
    C#            no checked exceptions. Hejlsberg's stated reasons: VERSIONING (adding one breaks
                  callers) and SCALABILITY (in a deep call stack, most intermediate methods can do
                  nothing but re-declare).
    KOTLIN        has the types for Java interop, ENFORCES NOTHING.
    SCALA         same. `@throws` exists only for Java callers.
    PYTHON, JS, RUBY   no static exception checking at all.
    GO            errors are RETURN VALUES: `if err != nil`. Explicit, verbose, impossible to ignore
                  silently — though the compiler does let you discard it with `_`.
    RUST          `Result<T, E>` in the type system, with `?` for propagation. THE STRONGEST VERSION OF
                  THE IDEA JAVA WAS REACHING FOR: the failure is in the return type, so it composes
                  with generics and closures, which is precisely what checked exceptions cannot do.

    THE PATTERN ACROSS ALL OF THEM: the industry kept the goal — make failure visible in the signature —
    and rejected the mechanism — a second, separate channel the type system cannot carry.

IN MODERN JAVA:
    `Optional<T>` for "absent" — a missing value is not an exceptional condition and should never have
    been an exception.
    A RESULT TYPE — a sealed interface with `Success` and `Failure` records, matched with a `switch`
    pattern. This is Rust's approach, expressible in Java 21, and it composes with streams because it
    is just a value.
    `CompletableFuture` carries failures as VALUES through `exceptionally`, `handle` and `whenComplete`,
    which is why async code sidesteps the checked/unchecked distinction almost entirely.
    `UncheckedIOException`, `UncheckedExecutionException` — the JDK's own escape hatches.
    Spring's `DataAccessException` hierarchy — unchecked, but with a meaningful TYPE per failure, which
    is arguably the design people actually wanted: informative types, no enforcement.

WHEN A CHECKED EXCEPTION IS STILL RIGHT:
    THE CALLER CAN GENUINELY DO SOMETHING DIFFERENT — retry, fall back to a cache, prompt the user —
    AND you are confident they will not just be re-declaring it for ten frames. That is a narrow set,
    and it is the set the original design had in mind.

WHAT TO SAY: "I would use unchecked exceptions by default with meaningful types, wrap
infrastructure failures with the CAUSE preserved, and reserve checked exceptions for the narrow case
where the immediate caller has a real alternative action. And I would note that this is contested
design, not settled: no other mainstream language adopted it, and the reason is that checked exceptions
do not compose with lambdas or generics."

""",

"""6. HOW TO DESIGN ERROR HANDLING — numbered steps

STEP 1 — DECIDE WHETHER THE CALLER CAN ACT. If there is a genuine alternative — retry, fall back, ask
the user — a checked exception may be right. If not, unchecked.

STEP 2 — NEVER LEAVE A CATCH BLOCK EMPTY. If you truly intend to ignore it, log it and write the reason
in a comment. Silent swallowing destroys the only evidence.

STEP 3 — ALWAYS PASS THE CAUSE WHEN WRAPPING. `new ServiceException("loading user " + id, e)`. Without
the cause the original trace is gone.

STEP 4 — ADD CONTEXT WHEN YOU WRAP. The stack trace says where; the message should say what you were
doing and with which inputs.

STEP 5 — RESTORE THE INTERRUPT FLAG. `catch (InterruptedException e) { Thread.currentThread().interrupt();
... }`. Otherwise the thread is uncancellable for the rest of its life.

STEP 6 — CATCH THE NARROWEST TYPE THAT MAKES SENSE, and never `Throwable`. `catch (Exception e)` in a
block that also does real work will swallow your own bugs.

STEP 7 — USE try-with-resources FOR EVERYTHING CLOSEABLE. It preserves the primary exception and
attaches the close failure as SUPPRESSED, which the manual version silently discards.

STEP 8 — NEVER `return` FROM A `finally`. It discards in-flight exceptions.

STEP 9 — USE `Optional` FOR ABSENCE, NOT AN EXCEPTION. "Not found" is a normal outcome.

STEP 10 — DO NOT USE EXCEPTIONS FOR CONTROL FLOW IN HOT CODE. The cost is the stack walk in the
constructor; a check is orders of magnitude cheaper.

STEP 11 — AT SYSTEM BOUNDARIES, TRANSLATE. Convert infrastructure exceptions into domain ones, so
callers depend on your vocabulary rather than on your database driver's.

STEP 12 — HAVE EXACTLY ONE TOP-LEVEL HANDLER that logs with full context and returns something sane.
Most methods should not be catching anything at all.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Java splits failures in two. Checked ones — IOException, SQLException, InterruptedException — the
compiler forces you to catch or declare. Unchecked ones — everything under RuntimeException — you can
ignore entirely.

The intended rule is about fault and recourse. Checked means the WORLD misbehaved and you might
reasonably recover: retry, fall back, tell the user. Unchecked means the PROGRAM is wrong — you passed
null, you indexed past the end — and there's nothing to recover; fix the code. The structural rule is
just inheritance: unchecked is Error or RuntimeException, everything else under Throwable is checked.

But the honest answer is that this is contested design, not settled knowledge, and I think that's the
more interesting thing to say. Java is the only mainstream language with checked exceptions. C#,
Kotlin, Scala, Python, Go, Rust — every one of them looked at the idea and declined.

The argument FOR is genuinely good: a checked exception is compiler-enforced documentation. The failure
mode is in the TYPE rather than in a comment nobody reads, and nothing else in Java makes a caller
acknowledge a possibility.

The argument against that I find decisive is that they don't COMPOSE. Function.apply doesn't declare
throws, so a lambda passed to map can't throw a checked exception. Neither can one passed to forEach,
or Optional.map, or thenApply. Which produces the ugliest code in modern Java — a try/catch inside a
lambda whose only purpose is converting a checked exception into an unchecked one so it can escape. And
the JDK added UncheckedIOException specifically to make that possible, which is the standard library
conceding the point.

The second argument is versioning: adding a checked exception to an existing method breaks every
caller, so library authors rationally never add one. That's Hejlsberg's stated reason C# has none.

And then the empirical argument, which is the one that actually persuades me — look at what people do
when forced. `catch (IOException e) { }`. The compiler demanded a decision, the developer didn't want
to make one, and the worst possible answer satisfies it. The enforcement produced a silently swallowed
failure with the stack trace destroyed, which is strictly worse than no enforcement.

Where the ecosystem landed is telling: Spring wraps every SQLException into an unchecked
DataAccessException hierarchy and considers that a selling point. So the vote was against ENFORCEMENT
while keeping the idea that exception TYPES should be meaningful. And Rust's Result type is the
strongest version of what Java was reaching for — the failure is in the RETURN type, so it composes
with generics and closures, which is exactly what checked exceptions can't do.

Practically: unchecked by default with meaningful types, always wrap with the CAUSE preserved and
context added, restore the interrupt flag on InterruptedException, try-with-resources for anything
closeable so the close failure comes back as suppressed rather than replacing the real one, and reserve
checked exceptions for the narrow case where the immediate caller has a real alternative action.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT THE COMPILER ENFORCES ──────────────────────────────────────
    void read() { Files.readString(path); }        // ✗ DOES NOT COMPILE
    //            ^ unreported exception IOException; must be caught or declared
    void read() throws IOException { Files.readString(path); }     // ✓ specify
    void read() { try { Files.readString(path); }                  // ✓ catch
                  catch (IOException e) { log.error("read", e); } }
    void oops() { Objects.requireNonNull(null); }   // ✓ compiles. Unchecked.

    // ── THE PATTERN THE ENFORCEMENT ACTUALLY PRODUCES ───────────────────
    try { save(data); } catch (IOException e) { }
    //                                       ^^^ THE COMPILER IS SATISFIED and the
    //   failure is now invisible AND the stack trace is destroyed. Strictly worse
    //   than no enforcement. This is in every large Java codebase, in quantity.

    try { save(data); } catch (IOException e) { throw new RuntimeException(e); }
    //   ^ the reflexive wrap — which erases the distinction the mechanism created.

    // ── WHY THEY DO NOT COMPOSE ─────────────────────────────────────────
    paths.stream().map(Files::readString)          // ✗ DOES NOT COMPILE
    //                 ^ Function.apply() declares NO throws, so no lambda anywhere
    //                   in the JDK's functional interfaces may throw a checked one.
    paths.stream().map(p -> {
        try { return Files.readString(p); }
        catch (IOException e) { throw new UncheckedIOException(e); }
    //                                     ^^^^^^^^^^^^^^^^^^^^ a class the JDK
    //   ADDED specifically so this workaround would be possible. The standard
    //   library conceding the point.
    })

    // ── WRAPPING: the one line that decides whether you can debug it ────
    catch (SQLException e) { throw new ServiceException("loading user " + id); }
    //                                                  ^ NO CAUSE. The original
    //   trace is gone and the log says only "loading user 42".
    catch (SQLException e) { throw new ServiceException("loading user " + id, e); }
    //                                                                       ^ ALWAYS

    // ── THE ONE THAT BREAKS CANCELLATION ────────────────────────────────
    try { queue.take(); } catch (InterruptedException e) { }
    // ^ catching it CLEARS the interrupt flag, so this thread can never be
    //   cancelled again — shutdownNow() and every JDK cancellation stops working.
    try { queue.take(); }
    catch (InterruptedException e) { Thread.currentThread().interrupt(); return; }
    //                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ restore it

    // ── finally THAT EATS THE EXCEPTION ─────────────────────────────────
    try { throw new IOException("real"); } finally { return 42; }
    // ^ returns 42. THE EXCEPTION SIMPLY DISAPPEARS — no log, no trace, no evidence.

    // ── SUPPRESSED: what try-with-resources fixed ───────────────────────
    try (var in = new FileInputStream(f)) { throw new IllegalStateException("body"); }
    // body throws AND close() throws → the BODY's exception propagates and close()'s
    // is attached via addSuppressed(). The pre-Java-7 manual finally version LOST the
    // original entirely — the close failure replaced the real cause.

    // ── WHY "EXCEPTIONS ARE SLOW" IS HALF TRUE ──────────────────────────
    new RuntimeException("x");           // ← THE EXPENSIVE PART: the CONSTRUCTOR
    //                                        calls fillInStackTrace(), walking the
    //                                        whole stack. Throwing/catching is cheap.
    super(msg, cause, false, false);     // suppression off, WRITABLE STACK TRACE OFF
    //                                      → a nearly free exception, for control flow

    // ── THE EMPTY STACK TRACE IN PRODUCTION ─────────────────────────────
    // "java.lang.NullPointerException" with NO frames is not a logging bug: after
    // enough throws from one site, HotSpot recompiles it to throw a PRE-ALLOCATED
    // exception with no trace. -XX:-OmitStackTraceInFastThrow to get it back.""",

"""9. THE TRACE — one failure, four handling strategies

A `SQLException` IS THROWN THREE LAYERS DOWN, in `UserRepository.findById`. Follow what the operator
sees in each strategy:

    STRATEGY 1 — SWALLOW
    layer                what happens                          what ops sees
    ---------------------------------------------------------------------------------
    repository           catch (SQLException e) { }            —
    service              receives null                         —
    controller           NullPointerException on user.name()   NPE at Controller:52
    ---------------------------------------------------------------------------------
    THE STACK TRACE POINTS AT THE CONTROLLER. The database was down and the report says a null
    pointer in the view layer. Two hours of the wrong investigation, and the evidence is unrecoverable
    because the original exception object no longer exists.

    STRATEGY 2 — WRAP WITHOUT THE CAUSE
    layer                what happens                          what ops sees
    ---------------------------------------------------------------------------------
    repository           throw new ServiceException("db")      —
    controller           500                                   ServiceException: db
                                                                at Repository:31
    ---------------------------------------------------------------------------------
    Better — the right LAYER is named. But "db" is the entire diagnosis: no SQL state, no vendor code,
    no indication of whether it was a timeout, a constraint violation or a dead connection.

    STRATEGY 3 — WRAP WITH THE CAUSE AND CONTEXT
    layer                what happens                          what ops sees
    ---------------------------------------------------------------------------------
    repository           throw new ServiceException(           ServiceException: loading
                           "loading user " + id, e)            user 4471
    controller           500 + log                               at Repository:31
                                                               Caused by: SQLException:
                                                                 connection timed out
                                                                 at OracleDriver:…
    ---------------------------------------------------------------------------------
    THE CAUSED-BY CHAIN IS THE WHOLE DIFFERENCE. One extra argument, `e`, and the log now contains the
    layer, the operation, the identifier, and the underlying driver-level reason.

    STRATEGY 4 — LET IT PROPAGATE AS A CHECKED EXCEPTION ALL THE WAY UP
    layer                what happens
    ---------------------------------------------------------------------------------
    repository           throws SQLException
    service              throws SQLException     ← re-declared, does nothing with it
    controller           throws SQLException     ← re-declared, does nothing with it
    framework            catch (Exception e)
    ---------------------------------------------------------------------------------
    THIS IS HEJLSBERG'S SCALABILITY ARGUMENT, made concrete. Two intermediate layers were forced to
    mention a database exception they have no opinion about, coupling the service and controller
    signatures to the persistence technology. Change to a NoSQL store and every signature changes.

NOW THE COST TRACE — where the time actually goes:

    operation                                    relative cost
    ---------------------------------------------------------------------------------
    `new RuntimeException("x")` at depth 50      ~1000x   ← fillInStackTrace walks 50 frames
    the same at depth 5                          ~100x    ← DEPTH-DEPENDENT
    `super(msg, cause, false, false)`            ~1x      ← no stack trace captured
    throw + catch, object already built          ~1x      ← comparable to a branch
    an `if` check instead                        ~0.01x
    ---------------------------------------------------------------------------------
    "EXCEPTIONS ARE SLOW" IS ABOUT THE CONSTRUCTOR, NOT THE THROW. Which is why the JIT's response to a
    hot implicit exception is to stop capturing the trace — and why you sometimes see a bare
    `NullPointerException` with no frames at all in a production log. That is an optimisation, not a
    logging failure.

WHAT PRODUCED WHAT:
    THE EMPTY CATCH        produced strategy 1's misleading trace. The compiler was satisfied.
    THE MISSING `e`        produced strategy 2's uselessness. One argument.
    RE-DECLARATION         produced strategy 4's coupling — the scalability argument.
    fillInStackTrace       produced the entire cost table, and the empty traces in production.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Unchecked = `Error` or `RuntimeException` and their subclasses. Checked = everything else under
    `Throwable`. Purely structural — inheritance, not annotation.
    An overriding method may declare fewer or narrower checked exceptions, never more.
    The cost of an exception is `fillInStackTrace()` in the CONSTRUCTOR, proportional to stack depth.
    Throwing and catching an existing object is comparable to a branch.
    `super(msg, cause, false, false)` gives a nearly free exception with no stack trace.
    try-with-resources: the body's exception wins, `close()`'s is attached via `addSuppressed`.
    HotSpot may replace a hot implicit exception with a pre-allocated, trace-less one.

THE #1 MISTAKE: the empty catch block. The compiler is satisfied, the failure is invisible, and the
evidence is destroyed. It is what enforcement pressures people into.

THE #2 MISTAKE: wrapping without the cause. One missing argument turns a diagnosable failure into a
one-word log line.

THE #3 MISTAKE: swallowing `InterruptedException`. Clears the flag and makes the thread uncancellable
for the rest of its life.

THE #4 MISTAKE: `catch (Exception e)` around code that also does real work. It swallows your own
NullPointerExceptions and reports them as handled errors.

THE #5 MISTAKE: `catch (Throwable t)`. Now you have caught `OutOfMemoryError` and continue in an
undefined state.

THE #6 MISTAKE: `return` in a `finally`. Discards the in-flight exception silently.

THE #7 MISTAKE: `throws Exception` on a public API. Conveys nothing and forces everyone to catch
everything.

THE #8 MISTAKE: exceptions for control flow in hot code. The stack walk per construction is the cost.

THE #9 MISTAKE: using an exception for "not found". That is `Optional`, and it is a normal outcome.

THE #10 MISTAKE: declaring a checked exception through layers that cannot act on it. That coupling is
the scalability argument against the whole feature.

THE #11 MISTAKE: reading a trace-less production `NullPointerException` as a logging bug. It is the JIT
optimising a hot throw site.

THE #12 MISTAKE: treating the checked/unchecked split as settled best practice. It is a design Java
alone adopted, and being able to say why the rest of the industry declined is the actual answer.

ONE-SENTENCE TAKEAWAY: checked exceptions are compiler-enforced documentation for failures the caller
might reasonably recover from, and unchecked ones signal bugs — a genuinely good idea whose mechanism
DOES NOT COMPOSE, because no functional interface in the JDK declares `throws`, so lambdas cannot carry
them and the JDK had to add `UncheckedIOException` as an escape hatch, and because adding one to an
existing method breaks every caller, which is why no other mainstream language adopted the feature and
why Java itself drifted to unchecked-with-meaningful-types (Spring's `DataAccessException`); use
unchecked by default, always wrap WITH the cause and added context, restore the interrupt flag, prefer
try-with-resources so a failing `close()` is suppressed rather than replacing the real exception, and
reserve checked exceptions for the narrow case where the immediate caller has a real alternative
action.""",
]


DEEP["Overriding vs overloading — and why static methods are not polymorphic"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two words that sound alike and are opposites

OVERLOADING is several methods with the SAME NAME and DIFFERENT PARAMETERS in the same class.
`println(int)`, `println(String)`, `println(Object)`. Which one runs is decided BY THE COMPILER, from
the DECLARED TYPES of the arguments, before the program ever starts.

OVERRIDING is a subclass replacing a method it inherited — same name, same parameters. Which one runs
is decided AT RUNTIME, from the ACTUAL OBJECT.

    THAT IS THE ENTIRE DISTINCTION, AND IT IS THE ONE THING TO SAY FIRST: OVERLOADING IS COMPILE TIME
    AND USES THE DECLARED TYPE; OVERRIDING IS RUNTIME AND USES THE REAL TYPE.

    Everything surprising about both features falls out of that sentence:

    Object o = "hello";
    print(o);            // calls print(Object). NOT print(String).

    The object IS a String at runtime. The compiler does not care — the variable is DECLARED `Object`,
    the choice among overloads was made at compile time, and nothing revisits it. Overloading has no
    runtime component at all.

    Animal a = new Dog();
    a.speak();           // calls Dog.speak(). The DECLARED type is ignored.

    Here the choice IS made at runtime, from the actual object. Same-looking code, opposite mechanism.

THE EVERYDAY VERSION: overloading is a menu where the dish is chosen by what you WROTE on the order
slip. Overriding is a dish where the recipe is chosen by which kitchen actually cooks it. Write "soup"
and the slip decides which soup; who cooks it decides how that soup is made.

TERMS AS THEY APPEAR:
- STATIC TYPE (declared type): what the variable is declared as. Known at compile time.
- DYNAMIC TYPE (runtime type): what the object actually is.
- DYNAMIC DISPATCH: choosing the method body from the runtime type. What "polymorphism" means.
- HIDING: what happens to static methods and fields, which look overridden and are not.""",

"""2. THE INTUITION — one dispatch table, and three things that are not in it

WHEN YOU CALL AN INSTANCE METHOD, the compiler picks the SIGNATURE and the JVM picks the BODY.

    THE COMPILER'S JOB: from the declared types, choose which overload's signature is being invoked, and
    emit an instruction naming it. This is finished at compile time and is never revisited.
    THE JVM'S JOB: at the call, look at the actual object, find that signature in its class's method
    table, and run whatever body is there.

    SO EVERY CALL IS TWO DECISIONS, ONE PER PHASE. Overloading lives entirely in the first. Overriding
    lives entirely in the second. Confusing them is the source of nearly every surprise in this topic.

NOW THE THREE THINGS THAT ARE NOT IN THE RUNTIME TABLE — and are therefore NOT polymorphic:

    STATIC METHODS. They belong to the CLASS, not to an instance. A subclass declaring the same static
    signature does not override it — it HIDES it, and which one runs is decided from the DECLARED type
    of the reference. `Animal a = new Dog(); a.describe();` calls `Animal.describe()` even though the
    object is a Dog. WORSE, `a` may be null and the call still works, because the reference is never
    dereferenced.

    FIELDS. Fields are never polymorphic, in any object-oriented language that has them separate from
    methods. `Animal a = new Dog(); a.name` reads `Animal.name` if both classes declare `name`. The
    object has BOTH fields, and which one you see depends on the declared type of the expression.

    PRIVATE METHODS. Not visible to the subclass, so a same-named method there is a NEW method, not an
    override. Implicitly final in effect.

    THE COMMON THREAD: dynamic dispatch applies to INSTANCE METHODS AND NOTHING ELSE. Every other member
    is resolved from what the compiler could see.

WHY OVERLOAD RESOLUTION FEELS ARBITRARY — it is not, it is three ordered phases:

    PHASE 1: try to find a match using only WIDENING conversions (int → long → float → double). No
             boxing, no varargs.
    PHASE 2: if none, allow BOXING and unboxing.
    PHASE 3: if still none, allow VARARGS.

    THE PHASES ARE TRIED IN ORDER AND THE FIRST ONE THAT FINDS A MATCH WINS. Which is why, given
    `f(long)` and `f(Integer)` called with an `int`, `f(long)` wins — widening is phase 1 and boxing is
    phase 2. And why `f(int...)` loses to almost everything. This ordering exists for backward
    compatibility: adding autoboxing and varargs in Java 5 must not have changed the meaning of any
    existing program, so both were made last resorts.

    WITHIN A PHASE, THE MOST SPECIFIC APPLICABLE METHOD WINS. `f(String)` beats `f(Object)` because
    every String is an Object. If neither is more specific than the other — `f(String)` and
    `f(Integer)` called with `null` — it is an AMBIGUITY COMPILE ERROR.""",

"""3. THE MECHANISM — five invoke instructions, and what @Override buys you

THE JVM HAS FIVE METHOD-CALL INSTRUCTIONS, and knowing which one a call compiles to tells you exactly
what can happen at runtime:

    invokestatic      a static method. NO receiver, NO dispatch. Chosen entirely at compile time.
    invokespecial     constructors, `private` methods, and `super.x()`. NO dispatch — exactly the named
                      method runs. This is why `super.toString()` cannot be intercepted by a subclass.
    invokevirtual     a normal instance method on a class. DISPATCHED through the object's method table.
    invokeinterface   an instance method through an interface reference. Dispatched too, historically
                      via a slower search because a class's interface positions are not fixed.
    invokedynamic     lambdas, method references, and string concatenation. The target is decided by a
                      bootstrap method on first execution.

    OVERRIDING IS `invokevirtual` AND `invokeinterface`. Those two are the whole of polymorphism.
    Everything compiled to `invokestatic` or `invokespecial` is fixed before the program runs.

THE METHOD TABLE (VTABLE). Each class has an array of method pointers; a subclass inherits its
superclass's table and OVERWRITES the slots it overrides. A virtual call is therefore "load the class
pointer from the object, index a fixed slot, jump" — a couple of instructions. AND THE JIT USUALLY
REMOVES EVEN THAT: if only one type has ever appeared at a call site, it inlines that implementation
behind a class check.

THE RULES FOR A LEGAL OVERRIDE — each with a reason:
    SAME NAME AND PARAMETER TYPES. Different parameters means you wrote an OVERLOAD, silently.
    RETURN TYPE MAY BE COVARIANT (narrower). Java 5 onwards. `clone()` returning your own type.
    ACCESS MAY WIDEN, NEVER NARROW. A `public` method cannot become `protected`, or a caller holding
    the supertype could no longer do what the supertype promised.
    CHECKED EXCEPTIONS MAY NARROW OR VANISH, NEVER BROADEN. Same reason.
    `final`, `static` AND `private` METHODS CANNOT BE OVERRIDDEN.

`@Override` IS THE MOST VALUABLE ANNOTATION IN JAVA, and the reason is precise: THE COMPILER CANNOT
OTHERWISE TELL THE DIFFERENCE BETWEEN AN OVERRIDE AND AN ACCIDENTAL OVERLOAD.

    Write `public boolean equals(MyClass other)` and you have created a NEW METHOD. It compiles. It
    looks right. `Object.equals(Object)` is still inherited, so every collection calls THAT one, and
    your `HashSet` silently contains duplicates. `@Override` turns this into a compile error, instantly.
    THIS IS THE SINGLE MOST COMMON REAL BUG IN THIS ENTIRE TOPIC.

BRIDGE METHODS, for completeness: when generics or covariant returns are involved, javac synthesises an
extra method with the erased signature that casts and delegates. So `Comparable<Foo>.compareTo(Foo)`
gets a hidden `compareTo(Object)` companion — which is what the runtime actually dispatches to, and
why a generic override works at all after erasure.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `equals(MyType)` INSTEAD OF `equals(Object)`. An overload, not an override. Collections use
the inherited `Object.equals`, so sets contain duplicates and maps miss lookups. `@Override` catches it.

CASE 2 — `Object o = "hi"; print(o);` CALLS `print(Object)`. The runtime type is irrelevant to overload
selection. The most common demonstration of the compile-time rule.

CASE 3 — STATIC METHOD "OVERRIDDEN". It is HIDDEN. Which runs depends on the DECLARED type, so
`Animal a = new Dog(); a.describe();` runs `Animal.describe()`.

CASE 4 — CALLING A STATIC METHOD THROUGH A NULL REFERENCE. `Animal a = null; a.describe();` works. The
reference is never dereferenced because the call compiles to `invokestatic`.

CASE 5 — FIELD HIDING. If both classes declare `name`, the object has BOTH, and which you see depends
on the declared type of the expression. Fields are never polymorphic.

CASE 6 — CALLING AN OVERRIDABLE METHOD FROM A CONSTRUCTOR. The subclass override runs BEFORE the
subclass's fields are initialised, so it sees nulls and zeros. A genuinely nasty bug, and the reason
Effective Java says constructors must not invoke overridable methods.

CASE 7 — `null` PASSED TO OVERLOADS. It binds to the MOST SPECIFIC applicable type; if two are
unrelated, it is an ambiguity compile error. Cast to disambiguate.

CASE 8 — WIDENING BEATS BOXING. With `f(long)` and `f(Integer)`, an `int` argument calls `f(long)`.
Phase 1 before phase 2, for backward compatibility with pre-Java-5 code.

CASE 9 — VARARGS ALWAYS LOSES. `f(int, int)` beats `f(int...)` for two arguments, because varargs is
phase 3.

CASE 10 — `list.remove(1)` VS `list.remove(Integer.valueOf(1))`. Overload resolution silently choosing
index over value on a `List<Integer>`. Both compile.

CASE 11 — NARROWING ACCESS ON AN OVERRIDE. A compile error, and rightly: it would break the
supertype's promise to its callers.

CASE 12 — OVERLOADING ACROSS AN INHERITANCE BOUNDARY. Subclass overloads join the superclass's set, so
adding a method in a superclass can silently change which overload an existing subclass call selects.
This is why Effective Java advises against overloading with the same arity at all.

CASE 13 — LAMBDAS AND OVERLOADS. Passing a lambda where two overloads take different functional
interfaces is often ambiguous, because a lambda has no type of its own until a target type is chosen.""",

"""5. THE ALTERNATIVES — designing so the distinction never bites

DO NOT OVERLOAD WITH THE SAME NUMBER OF PARAMETERS. Effective Java Item 52, and it is the single most
effective rule here: if two overloads have the same arity, a reader cannot tell which runs without
knowing the declared types, and neither can a maintainer.

    GIVE THEM DIFFERENT NAMES INSTEAD. `readFromFile(String)` and `readFromUrl(String)`. This is why
    `ObjectOutputStream` has `writeInt`, `writeLong`, `writeBoolean` rather than eleven `write`
    overloads — the API's author faced exactly this and chose names.

STATIC FACTORY METHODS with descriptive names instead of overloaded constructors. `BigDecimal.valueOf`
versus `new BigDecimal(...)` — where, notoriously, the `double` and `String` overloads behave
differently and the wrong one is easy to reach.

`@Override` ON EVERY OVERRIDE, ALWAYS. It costs nothing and converts the accidental-overload bug class
into a compile error. Turn on the IDE inspection that requires it.

PREFER COMPOSITION TO INHERITANCE when the hierarchy is getting deep. Overriding is a contract between
a superclass and its subclasses that is almost never written down; composition makes it explicit.
Effective Java Item 18: "design for inheritance or prohibit it" — and `final` on a class is a
legitimate design choice, not laziness.

SEALED CLASSES AND INTERFACES (Java 17) plus PATTERN-MATCHING `switch` — when you have a closed set of
types and want behaviour selected per type. This gives you EXHAUSTIVENESS CHECKING, which dynamic
dispatch never provided: add a subtype and every switch that does not handle it fails to compile.

THE VISITOR PATTERN, historically, for double dispatch — choosing behaviour from the runtime types of
TWO objects, which single dispatch cannot express. Largely superseded by sealed types and pattern
matching, and worth knowing mainly to explain why those features were added.

TEMPLATE METHOD — a `final` public method defining the sequence, calling `protected abstract` hooks.
This is overriding used well: the extension points are declared, documented, and constrained.

WHAT TO SAY: "Overloading is compile-time and uses declared types; overriding is runtime and uses the
actual object. I avoid overloads with the same arity because the reader cannot tell which runs, always
write `@Override` because the accidental `equals(MyType)` overload is a real bug the compiler will
catch, and never call an overridable method from a constructor."

""",

"""6. HOW TO GET IT RIGHT — numbered steps

STEP 1 — ASK "COMPILE TIME OR RUNTIME?" Overloading is compile time from declared types. Overriding is
runtime from the object. Every surprise follows from getting this backwards.

STEP 2 — PUT `@Override` ON EVERY OVERRIDE. Without it, a signature typo silently creates an overload.

STEP 3 — WHEN YOU IMPLEMENT `equals`, ITS PARAMETER IS `Object`. Anything else is a new method and your
collections will misbehave silently.

STEP 4 — AVOID OVERLOADS WITH THE SAME ARITY. Use distinct names, or static factories.

STEP 5 — NEVER CALL AN OVERRIDABLE METHOD FROM A CONSTRUCTOR. The override runs before the subclass's
fields exist.

STEP 6 — REMEMBER STATIC METHODS ARE HIDDEN, NOT OVERRIDDEN. Call them on the class, never through an
instance reference — most IDEs warn, and the warning is right.

STEP 7 — DO NOT SHADOW FIELDS. If a subclass needs a different value, use a protected accessor; fields
are never polymorphic and hiding them produces two live values.

STEP 8 — REMEMBER WIDENING BEATS BOXING BEATS VARARGS. When resolution surprises you, that ordering is
almost always the reason.

STEP 9 — CAST `null` WHEN PASSING IT TO OVERLOADS. `f((String) null)` states the intent and avoids the
ambiguity error.

STEP 10 — MAKE A CLASS `final` OR DESIGN IT FOR INHERITANCE, and document which methods may be
overridden and what they may assume. An undocumented override contract is a bug waiting for a
maintainer.

STEP 11 — FOR A CLOSED SET OF TYPES, PREFER SEALED TYPES AND PATTERN MATCHING over a virtual method,
when you want exhaustiveness checked at compile time.

STEP 12 — WHEN AN OVERLOAD IS AMBIGUOUS TO YOU, IT IS AMBIGUOUS TO EVERY READER. Rename it.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Overloading is several methods with the same name and different parameters. Which one runs is decided
BY THE COMPILER, from the DECLARED types of the arguments. Overriding is a subclass replacing an
inherited method with the same signature, and which one runs is decided AT RUNTIME from the actual
object.

So the sentence I'd lead with is: overloading is compile time and uses the declared type; overriding is
runtime and uses the real type. Everything surprising falls out of that.

The demonstration is two lines. `Object o = "hello"; print(o);` calls print(Object), not print(String).
The object IS a String at runtime — the compiler doesn't care, because the variable is declared Object
and the overload was chosen at compile time. Nothing revisits it. Overloading has no runtime component
at all. Whereas `Animal a = new Dog(); a.speak();` calls Dog.speak and ignores the declared type.

The three things that are NOT polymorphic are worth naming, because they all look like they should be.
Static methods belong to the class, so a subclass declaring the same signature HIDES rather than
overrides, and which runs is decided from the declared type — which also means calling a static method
through a null reference works fine, because the reference is never dereferenced. Fields are never
polymorphic either: if both classes declare `name`, the object has BOTH, and which you see depends on
the declared type of the expression. And private methods aren't visible to the subclass, so a same-named
method there is just a new method. The thread through all three: dynamic dispatch applies to instance
methods and nothing else.

Overload resolution feels arbitrary but it's three ordered phases. Phase one tries widening only —
int to long to double. Phase two allows boxing. Phase three allows varargs. First phase to find a match
wins. So with f(long) and f(Integer), an int argument calls f(long), because widening is phase one and
boxing is phase two. That ordering exists for backward compatibility: adding autoboxing and varargs in
Java 5 must not have changed the meaning of any existing program, so both were made last resorts.

At the bytecode level, overriding is invokevirtual and invokeinterface — those two are the whole of
polymorphism. invokestatic and invokespecial are fixed before the program runs, which is exactly why
static methods and super calls can't be intercepted.

The practical bug I'd flag hardest: writing `public boolean equals(MyClass other)`. That's an OVERLOAD,
not an override. It compiles, it looks right, Object.equals(Object) is still inherited, so every
collection calls that one and your HashSet silently contains duplicates. `@Override` turns it into a
compile error instantly, which is why I'd put that annotation on every override without exception.

And two design rules: don't overload with the same arity, because the reader can't tell which one runs
— that's why ObjectOutputStream has writeInt and writeLong rather than eleven write overloads. And
never call an overridable method from a constructor, because the subclass's override runs before the
subclass's fields are initialised and sees nulls and zeros.'""",

"""8. THE CODE, LINE BY LINE

    // ── OVERLOADING: the compiler decides, from the DECLARED type ───────
    static void print(Object o) { System.out.println("Object"); }
    static void print(String s) { System.out.println("String"); }

    String s = "hi";  print(s);        // "String"  ← declared String
    Object o = "hi";  print(o);        // "Object"  ← DECLARED Object. The runtime
    //                                    type is String and it is IRRELEVANT: the
    //                                    overload was chosen at compile time and
    //                                    nothing revisits it.
    print((String) o);                 // "String"  ← a cast changes the DECLARED type

    // ── OVERRIDING: the JVM decides, from the ACTUAL object ─────────────
    class Animal { String speak() { return "..."; } }
    class Dog extends Animal { @Override String speak() { return "Woof"; } }
    Animal a = new Dog();  a.speak();  // "Woof" ← declared type IGNORED

    // ── STATIC METHODS ARE HIDDEN, NOT OVERRIDDEN ───────────────────────
    class Animal { static String describe() { return "an animal"; } }
    class Dog extends Animal { static String describe() { return "a dog"; } }
    Animal a = new Dog();
    System.out.println(a.describe());  // "an animal"  ← the DECLARED type wins
    Animal n = null;
    System.out.println(n.describe());  // "an animal" — NO NullPointerException,
    //                                    because this compiles to invokestatic and
    //                                    the reference is never dereferenced.

    // ── FIELDS ARE NEVER POLYMORPHIC ────────────────────────────────────
    class Animal { String name = "animal"; }
    class Dog extends Animal { String name = "dog"; }
    Dog d = new Dog();
    Animal a = d;
    System.out.println(a.name);        // "animal"   ← declared type
    System.out.println(d.name);        // "dog"      ← SAME OBJECT, both fields exist
    System.out.println(((Animal) d).name);  // "animal" — a cast selects the field

    // ── THE BUG @Override EXISTS TO CATCH ───────────────────────────────
    class Point {
        int x, y;
        public boolean equals(Point other) { return x == other.x && y == other.y; }
    //                       ^^^^^ AN OVERLOAD. Object.equals(Object) is still
    //   inherited, so every collection calls THAT one — reference equality.
    }
    var set = new HashSet<Point>();
    set.add(new Point(1,1)); set.add(new Point(1,1));
    System.out.println(set.size());    // 2. Silent duplicates.
    @Override public boolean equals(Point o)   // ← COMPILE ERROR. Fixed instantly.
    @Override public boolean equals(Object o)  // ← correct

    // ── OVERLOAD RESOLUTION: three ordered phases ───────────────────────
    static void f(long x)     { print("long");    }   // phase 1: widening
    static void f(Integer x)  { print("Integer"); }   // phase 2: boxing
    static void f(int... x)   { print("varargs"); }   // phase 3: varargs
    f(5);                              // "long" — phase 1 finds a match and STOPS.
    //   Backward compatibility: adding boxing and varargs in Java 5 could not be
    //   allowed to change the meaning of any existing program.
    f(null);                           // needs a cast: which reference type?

    // ── THE CONSTRUCTOR TRAP ────────────────────────────────────────────
    class Base { Base() { init(); } void init() { } }
    class Sub extends Base {
        private final List<String> items = new ArrayList<>();
        @Override void init() { items.add("x"); }
    //                          ^^^^^ NullPointerException. Base's constructor runs
    //   FIRST, calls the override, and `items` has not been assigned yet — the
    //   field initialiser runs AFTER the super constructor returns.
    }""",

"""9. THE TRACE — the same call site, two mechanisms

SETUP:
    class Animal { String speak() { return "..."; }  static String kind() { return "animal"; }
                   String name = "animal"; }
    class Dog extends Animal { String speak() { return "Woof"; }  static String kind() { return "dog"; }
                              String name = "dog"; }
    Animal a = new Dog();

FOUR ACCESSES THROUGH THE SAME REFERENCE, and what each one resolves against:

    expression      bytecode          resolved from        result      why
    ---------------------------------------------------------------------------------
    a.speak()       invokevirtual     THE OBJECT           "Woof"      dynamic dispatch
    a.kind()        invokestatic      the DECLARED type    "animal"    no dispatch exists
    a.name          getfield          the DECLARED type    "animal"    fields never dispatch
    ((Dog)a).name   getfield          the CAST type        "dog"       the same object!
    ---------------------------------------------------------------------------------
    ONE OBJECT. ONE REFERENCE. FOUR ACCESSES, AND ONLY THE FIRST IS POLYMORPHIC. The instruction the
    compiler emitted decides everything, and it emitted a different instruction for each row.

NOW THE OVERLOAD TRACE — following the three phases:

    given:  f(long), f(Integer), f(int...)     call:  f(5)   where 5 is an int
    ---------------------------------------------------------------------------------
    phase 1  widening only, no boxing, no varargs
             f(long)     — int widens to long          APPLICABLE  ← MATCH FOUND
             f(Integer)  — would need boxing           not eligible in this phase
             f(int...)   — varargs                     not eligible in this phase
             → phase 1 succeeded, so PHASES 2 AND 3 ARE NEVER TRIED
    ---------------------------------------------------------------------------------
    RESULT: "long". Not Integer, which looks like the closer match to a human. The phases exist so that
    Java 5's autoboxing could not silently change the behaviour of any program written before it.

    same overloads, call:  f(Integer.valueOf(5))
    ---------------------------------------------------------------------------------
    phase 1  f(Integer) — exact match, no conversion at all              MATCH
    → "Integer". The argument's DECLARED type changed, so the answer changed.
    ---------------------------------------------------------------------------------

AND THE CONSTRUCTOR TRACE — the initialisation order that produces the null:

    step  what runs                                    `items` is
    ---------------------------------------------------------------------------------
    1     `new Sub()` → Sub's constructor begins        null (default value)
    2     it implicitly calls `super()` FIRST           null
    3     Base's constructor body runs → `init()`       null
    4     DISPATCH picks Sub.init() — the override      null
    5     `items.add("x")`                              NullPointerException
    6     (never reached) Sub's field initialisers      would have run HERE
    7     (never reached) Sub's constructor body
    ---------------------------------------------------------------------------------
    DYNAMIC DISPATCH IS WORKING PERFECTLY. That is what makes this subtle: step 4 does exactly what
    polymorphism promises — it picks the subclass's method — and the subclass's own state does not exist
    yet, because field initialisers run AFTER the super constructor returns. The feature and the bug are
    the same mechanism.

WHAT PRODUCED WHAT:
    THE COMPILER CHOOSING THE SIGNATURE   produced every "declared type wins" row: the overload result,
                                          the static call, and both field reads.
    THE JVM CHOOSING THE BODY             produced the one polymorphic row, and the constructor trap.
    PHASE ORDERING                        produced "long" beating "Integer", and exists purely for
                                          backward compatibility.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Overload resolution: entirely at compile time. Zero runtime cost.
    Virtual dispatch: load the class pointer, index a fixed vtable slot, jump — a couple of
    instructions, and usually inlined away by the JIT when only one type appears at the site.
    `invokestatic` / `invokespecial`: no dispatch at all, fixed before the program runs.
    `invokeinterface`: historically slower than `invokevirtual` because interface method positions are
    not fixed across implementing classes.
    Overload phases: 1 widening, 2 boxing, 3 varargs. First match wins; within a phase, most specific
    wins; a tie is a compile error.

THE #1 MISTAKE: `equals(MyType)` instead of `equals(Object)`. An overload, so collections silently use
reference equality and sets contain duplicates. `@Override` prevents it entirely.

THE #2 MISTAKE: expecting overload selection to use the runtime type. It never does.

THE #3 MISTAKE: believing static methods are overridden. They are HIDDEN, and resolved from the
declared type.

THE #4 MISTAKE: expecting fields to be polymorphic. The object holds both, and the declared type
selects.

THE #5 MISTAKE: calling an overridable method from a constructor. The override runs before the
subclass's fields are initialised.

THE #6 MISTAKE: overloading with the same arity. No reader can tell which runs. Use distinct names.

THE #7 MISTAKE: assuming boxing beats widening. Phase 1 before phase 2, always.

THE #8 MISTAKE: passing an uncast `null` to overloads. Most specific wins, or it is ambiguous.

THE #9 MISTAKE: narrowing access or broadening checked exceptions in an override. Compile errors, and
correctly so — both would break the supertype's promise.

THE #10 MISTAKE: omitting `@Override`. It is free and it converts a silent bug class into a compile
error.

THE #11 MISTAKE: adding an overload to a superclass and assuming subclasses are unaffected. Overload
sets merge across the hierarchy, so an existing call can silently start selecting the new method.

ONE-SENTENCE TAKEAWAY: overloading is resolved by the COMPILER from the DECLARED types — in three
ordered phases where widening beats boxing beats varargs — while overriding is resolved by the JVM from
the ACTUAL OBJECT, and only instance methods participate in that runtime dispatch, so static methods
are HIDDEN and fields are shadowed with both values living in the same object and the declared type
choosing between them; the practical consequences are that `Object o = "hi"; print(o)` calls
`print(Object)`, that a static method call through a null reference does not throw, that writing
`equals(MyType)` silently creates an overload which every collection ignores — which is why `@Override`
belongs on every override — and that calling an overridable method from a constructor invokes the
subclass's version before the subclass's fields exist.""",
]


DEEP["Abstract class vs interface — and what default methods changed"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two ways to say "these types share something"

AN ABSTRACT CLASS is a partly-written class. It can have fields, constructors, private methods, and
finished method bodies alongside the unfinished ones. You cannot instantiate it; a subclass fills in
the gaps. A class may extend EXACTLY ONE of them.

AN INTERFACE is a set of method signatures a type promises to provide. A class may implement AS MANY AS
IT LIKES.

    THAT USED TO BE THE WHOLE ANSWER: "abstract classes can have code and state, interfaces are pure
    contracts, and you get one parent but many interfaces." Then Java 8 gave interfaces DEFAULT METHODS
    — method bodies — and Java 9 gave them private methods, and half the traditional answer stopped
    being true.

    SO THE MODERN ANSWER HAS TO NAME WHAT STILL DIFFERS, AND IT IS SHORT: **STATE**. An interface
    cannot have instance fields. It can have behaviour; it cannot have data. Plus: no constructors, and
    still only one superclass.

    AND — THIS IS THE PART MOST ANSWERS MISS — DEFAULT METHODS WERE NOT ADDED TO GIVE JAVA MULTIPLE
    INHERITANCE OF BEHAVIOUR. They were added to solve a specific, urgent problem: how do you add
    `stream()` and `forEach()` to `java.util.Collection` without breaking every implementation of it
    ever written, anywhere in the world? Before Java 8, adding a method to an interface broke every
    implementor. Default methods made INTERFACE EVOLUTION possible. The multiple-inheritance-of-behaviour
    capability is a side effect, and the JDK authors said so explicitly.

THE EVERYDAY VERSION: an abstract class is a half-built house — foundations, plumbing, some rooms
finished — and you can only build on one plot. An interface is a building code: a list of things any
house must provide. Java 8 let the building code include some standard fittings you get for free. It
still cannot pour you a foundation, because a code is not a plot of land.

TERMS AS THEY APPEAR:
- DEFAULT METHOD: an interface method with a body, inherited by implementors. Java 8.
- STATE: instance fields. The remaining hard line between the two.
- DIAMOND PROBLEM: inheriting the same method from two places, with no obvious winner.""",

"""2. THE INTUITION — what each one is FOR, once you know they overlap

SINCE BOTH CAN CARRY BEHAVIOUR, THE CHOICE IS NO LONGER TECHNICAL. It is about what you are modelling:

    AN INTERFACE DESCRIBES A CAPABILITY OR A ROLE. "This can be compared." "This can be closed." "This
    can be serialised." It says nothing about what the thing IS. A `Duck` and a `Rocket` can both be
    `Comparable` without having anything else in common — and that is exactly why interfaces support
    multiple implementation: a type has many roles and only one identity.

    AN ABSTRACT CLASS DESCRIBES A PARTIAL IDENTITY WITH SHARED MACHINERY. "Every AbstractList works like
    this, and here are the fields and the invariants." It is inherited singly BECAUSE identity is
    singular, and because inheriting fields from two places genuinely has no sane answer.

    THAT ASYMMETRY — MANY ROLES, ONE IDENTITY — IS WHY JAVA CHOSE SINGLE INHERITANCE OF CLASSES AND
    MULTIPLE OF INTERFACES, and it is a much better justification than "to avoid the diamond problem".

THE DIAMOND PROBLEM, SINCE IT COMES UP: what if you inherit the same method from two parents?

    WITH FIELDS IT IS GENUINELY UNANSWERABLE. If both parents declare `count`, does the child have one
    or two? C++ answers with virtual inheritance and a memory layout most people never fully learn.
    JAVA SIDESTEPS IT BY FORBIDDING STATE IN INTERFACES — which is precisely why the one remaining
    difference is the one that matters.
    WITH METHODS IT IS ANSWERABLE, and Java 8 answered it with three rules, in order:
        1. A CLASS WINS. A method inherited from a superclass beats any interface default.
        2. THE MORE SPECIFIC INTERFACE WINS. If `B extends A` and both define it, `B`'s is used.
        3. OTHERWISE IT IS A COMPILE ERROR, and you must resolve it explicitly with `A.super.method()`.
    RULE 3 IS THE IMPORTANT ONE: Java refuses to guess. Ambiguity is an error, not a silent choice.

WHY "CLASS WINS" — the reason is compatibility, and it is worth knowing: a default method added to an
interface in a later JDK must never override behaviour an existing class already had. Otherwise
upgrading the JDK would silently change your program.

THE MODERN PATTERN THAT USES BOTH — INTERFACE PLUS SKELETAL IMPLEMENTATION:

    Declare the type as an INTERFACE, so callers depend on the capability and implementors are free.
    Provide an ABSTRACT SKELETAL CLASS — `AbstractList`, `AbstractMap`, `AbstractSet` — that implements
    the tedious parts for anyone who wants to extend it.
    IMPLEMENTORS THEN CHOOSE: extend the skeleton for convenience, or implement the interface directly
    when they already have a superclass. This is Effective Java Item 20, it is how the entire
    collections framework is built, and it gets both benefits with neither constraint.""",

"""3. THE MECHANISM — what each can hold, and what default methods actually compile to

WHAT EACH CAN CONTAIN, precisely:

                                    interface                    abstract class
    instance fields                 NO — the hard line           yes
    `static final` constants        yes (implicitly public        yes
                                    static final)
    constructors                    NO                            yes
    abstract methods                yes (implicitly public)       yes
    concrete methods                yes — `default` (Java 8)      yes
    static methods                  yes (Java 8)                  yes
    private methods                 yes (Java 9)                  yes
    protected members               NO — everything is public      yes
                                    except private methods
    `final` methods                 NO — a default cannot be      yes
                                    final
    how many per class              MANY                          ONE

    READ THE FIRST AND LAST ROWS TOGETHER — THEY ARE THE SAME FACT. Interfaces allow many because they
    carry no state; classes allow one because they do.

TWO SUBTLETIES ABOUT INTERFACE MEMBERS:

    ALL INTERFACE FIELDS ARE `public static final`, IMPLICITLY. So an "interface constant" is a global
    constant, and the old "constant interface" pattern — implementing an interface purely to import its
    constants — is an anti-pattern (Effective Java Item 22): it leaks an implementation detail into the
    type's public API forever. Use an enum or a final class of static members.
    INTERFACE STATIC METHODS ARE NOT INHERITED. `MyList.of(...)` does not exist just because
    `List.of(...)` does; you must call `List.of`. This is deliberate — it stops static helpers from
    polluting every implementor.

WHAT A DEFAULT METHOD COMPILES TO: an ordinary method in the interface's class file with a body, and
`invokeinterface` at the call site dispatches to it if the implementing class provides nothing.
`X.super.method()` compiles to `invokespecial` naming the interface — which is the ONLY way to reach a
specific inherited default explicitly.

WHY `Iterable.forEach` AND `Collection.stream` EXIST AS DEFAULTS: this is the concrete case the feature
was built for. In 2014 there were millions of classes implementing `List` and `Collection` in code the
JDK team could not see or change. Adding an abstract `stream()` would have broken every one of them at
compile time. A DEFAULT METHOD ADDS THE CAPABILITY AND BREAKS NOBODY — and `Collection.removeIf` and
`Map.getOrDefault`/`computeIfAbsent`/`merge` all arrived the same way.

THE COST THEY ACCEPTED: a default method can only use the interface's own methods. It has no fields to
read, so it must be expressible in terms of the contract alone. `forEach` is `for (T t : this)
action.accept(t)` — nothing more is available to it. THAT LIMIT IS WHY DEFAULTS DID NOT TURN
INTERFACES INTO CLASSES.

FUNCTIONAL INTERFACES: exactly one abstract method, so a lambda can implement it. Default and static
methods do not count towards that one, which is why `Comparator` can carry `thenComparing`, `reversed`
and a dozen others and still be a lambda target. `@FunctionalInterface` makes the compiler enforce it.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — TRYING TO PUT STATE IN AN INTERFACE. A field there is `public static final` — one value shared
by every implementor, not per-instance. People discover this by writing a "counter" that is global.

CASE 2 — THE CONSTANT INTERFACE. Implementing an interface only to inherit its constants. It becomes
part of your public API permanently and can never be removed. Use an enum or a utility class.

CASE 3 — EXPECTING STATIC INTERFACE METHODS TO BE INHERITED. They are not. `MyImpl.of(...)` does not
exist because `List.of(...)` does.

CASE 4 — THE DIAMOND WITH TWO UNRELATED INTERFACES. Both define the same default and neither extends
the other: COMPILE ERROR, and you must write `A.super.hello()`. Java refuses to guess.

CASE 5 — A DEFAULT METHOD SILENTLY LOSING TO AN INHERITED CLASS METHOD. "Class wins" means a
superclass's `toString` beats an interface default, even if the interface is much more specific to
your intent.

CASE 6 — ADDING A DEFAULT METHOD TO AN INTERFACE AND BREAKING A DIAMOND. Source-compatible for anyone
implementing one interface; a compile error for anyone who implements two that now both define it. THE
FEATURE THAT MAKES EVOLUTION SAFE HAS ITS OWN INCOMPATIBILITY MODE.

CASE 7 — TRYING TO OVERRIDE `equals`, `hashCode` OR `toString` AS A DEFAULT METHOD. Explicitly
forbidden by the language. Those come from `Object`, "class wins" would make the default unreachable
anyway, and allowing it would let an interface change identity semantics.

CASE 8 — A `@FunctionalInterface` THAT ACQUIRES A SECOND ABSTRACT METHOD. Every lambda using it stops
compiling. The annotation exists to make this a declaration-site error rather than a use-site one.

CASE 9 — DEEP ABSTRACT CLASS HIERARCHIES. Three or four levels of `protected` methods and template
hooks, and no one can tell which class contributes which behaviour. Composition is usually the fix.

CASE 10 — AN ABSTRACT CLASS WHOSE CONSTRUCTOR CALLS AN ABSTRACT METHOD. The subclass override runs
before the subclass's fields are initialised, so it sees nulls.

CASE 11 — A CLASS THAT CANNOT USE YOUR SKELETAL IMPLEMENTATION because it already has a superclass.
This is exactly the scenario the interface-plus-skeleton pattern exists to handle, and forcing an
abstract class instead makes your type unusable in that codebase.

CASE 12 — RECORDS CANNOT EXTEND A CLASS. They can implement any number of interfaces. If you want a
type usable by records, it must be an interface.""",

"""5. THE ALTERNATIVES — and how to choose in practice

CHOOSE AN INTERFACE WHEN:
    you are describing a CAPABILITY or ROLE rather than an identity;
    unrelated types should be able to provide it;
    implementors may already have a superclass;
    you want records, enums or lambdas to be able to implement it;
    you want callers to depend on the smallest possible surface.
    THIS IS THE DEFAULT for anything crossing a module or team boundary.

CHOOSE AN ABSTRACT CLASS WHEN:
    there is genuine SHARED STATE — fields with invariants the subclasses must not violate;
    you need a constructor to establish those invariants;
    you want `protected` members visible to subclasses and to nobody else;
    you need to make some methods `final` to protect a template.

CHOOSE BOTH — THE SKELETAL IMPLEMENTATION PATTERN, which is the answer that shows you have used this in
anger. `Collection` / `AbstractCollection`, `List` / `AbstractList`, `Map` / `AbstractMap`. The
interface is the type; the abstract class is a convenience. Implementors take the shortcut or not, as
their own hierarchy allows.

MODERN ALTERNATIVES THAT OFTEN BEAT BOTH:
    COMPOSITION AND DELEGATION. "Has-a" instead of "is-a". No fragile base class, no hidden coupling
    through `protected`, and the relationship is visible in a field rather than in a header line.
    Effective Java Item 18, and it is the right answer more often than inheritance is.
    SEALED INTERFACES (Java 17) + RECORDS + PATTERN-MATCHING `switch`. A closed set of implementations,
    checked EXHAUSTIVELY at compile time. This is the shape modern Java reaches for when the set of
    subtypes is known — and unlike virtual dispatch, adding a case makes every incomplete switch fail
    to compile.
    A FUNCTIONAL INTERFACE plus lambdas, when the abstraction is really one operation. A whole class
    hierarchy for a strategy is often one `Function`.
    ENUMS WITH BEHAVIOUR — constant-specific method bodies give you a fixed set of implementations with
    no class hierarchy at all.

WHAT NOT TO DO: an interface with a single implementation created "for testability". Modern mocking
frameworks handle classes fine, and the extra type is pure indirection. ADD THE INTERFACE WHEN THERE IS
A SECOND IMPLEMENTATION, or a real boundary.

WHAT TO SAY: "Interfaces for capabilities and for anything crossing a boundary, abstract classes when
there is genuine shared state with invariants, and the skeletal-implementation pattern when I want
both. Default methods exist for INTERFACE EVOLUTION — they were how `stream()` was added to
`Collection` without breaking the world — so I would not treat them as a licence for multiple
inheritance of behaviour."

""",

"""6. HOW TO CHOOSE — numbered steps

STEP 1 — ASK: IS THERE SHARED STATE? Instance fields with invariants mean abstract class. No state means
interface. This is the only remaining hard technical line.

STEP 2 — ASK: CAPABILITY OR IDENTITY? "Can be compared", "can be closed" — interface. "Is a kind of" with
machinery — abstract class.

STEP 3 — DEFAULT TO THE INTERFACE for anything a caller depends on. It leaves implementors free and it
lets records, enums and lambdas participate.

STEP 4 — IF YOU WANT TO OFFER CONVENIENCE, USE THE SKELETAL PATTERN. Interface as the type, abstract
class as an optional base.

STEP 5 — USE `default` FOR EVOLUTION, NOT FOR CONVENIENCE. If you are adding a method to a released
interface, a default is the right tool. If you are designing something new, prefer an abstract method
plus a skeleton.

STEP 6 — DO NOT PUT STATE-LIKE CONSTANTS IN AN INTERFACE. Every field there is `public static final` and
becomes permanent public API.

STEP 7 — NEVER USE A CONSTANT INTERFACE. Use an enum or a final class with static members.

STEP 8 — MARK SINGLE-ABSTRACT-METHOD INTERFACES `@FunctionalInterface`. It makes accidentally adding a
second method an error at the declaration rather than at every lambda.

STEP 9 — IF THE SET OF IMPLEMENTATIONS IS CLOSED, MAKE IT `sealed`. You gain exhaustiveness checking in
`switch`, which no amount of virtual dispatch gives you.

STEP 10 — PREFER COMPOSITION WHEN THE HIERARCHY PASSES TWO LEVELS. Deep abstract hierarchies hide which
class contributes which behaviour.

STEP 11 — NEVER CALL AN ABSTRACT METHOD FROM A CONSTRUCTOR. The override runs before the subclass's
fields exist.

STEP 12 — RESOLVE DIAMONDS EXPLICITLY WITH `A.super.method()`. Java will not guess, and that is a
feature.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The classic answer is: abstract classes can have code and state, interfaces are pure contracts, you get
one superclass but many interfaces. Java 8 broke half of that, because default methods gave interfaces
method bodies, and Java 9 gave them private methods too.

So the modern answer has to name what actually still differs, and it's short: STATE. An interface cannot
have instance fields. It can have behaviour, it cannot have data. Plus no constructors, and still only
one superclass.

And here's the part I think most answers miss. Default methods weren't added to give Java multiple
inheritance of behaviour. They were added to solve one urgent problem: how do you add stream() and
forEach() to java.util.Collection without breaking every implementation of it ever written? Before
Java 8, adding a method to an interface broke every implementor at compile time, and in 2014 there were
millions of classes implementing List in code the JDK team couldn't see. A default method adds the
capability and breaks nobody. Default methods are INTERFACE EVOLUTION — the multiple-inheritance
capability is a side effect.

There's a nice consequence of that. A default method can only use the interface's own methods, because
it has no fields to read. forEach is literally "for each t in this, action.accept(t)" and nothing more
is available to it. That limit is exactly why defaults didn't turn interfaces into classes.

On the diamond problem: with FIELDS it's genuinely unanswerable — if both parents declare a counter,
does the child have one or two? C++ answers with virtual inheritance and a memory layout nobody fully
learns. Java sidesteps it by forbidding state in interfaces, which is why the one remaining difference
is the one that matters. With METHODS it's answerable, and Java 8 gave three rules: a class wins over
any interface default; a more specific interface wins over a less specific one; and otherwise it's a
COMPILE ERROR and you resolve it with A.super.method(). Java refuses to guess. And "class wins" is a
compatibility rule — a default added in a later JDK must never silently override behaviour an existing
class already had.

How I'd actually choose: since both can carry behaviour, the choice isn't technical any more, it's
about what you're modelling. An interface is a CAPABILITY or a role — "can be compared", "can be
closed" — and says nothing about what the thing is, which is why a Duck and a Rocket can both be
Comparable. An abstract class is a partial IDENTITY with shared machinery. Many roles, one identity —
that asymmetry is the real reason Java has single class inheritance and multiple interface
implementation, and it's a better justification than "to avoid the diamond".

In practice I'd use both: the interface-plus-skeletal-implementation pattern. Collection and
AbstractCollection, List and AbstractList. The interface is the type so callers depend on the
capability; the abstract class is an optional convenience for implementors who don't already have a
superclass. That gets both benefits with neither constraint, and it's how the whole collections
framework is built.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT AN INTERFACE CAN AND CANNOT HOLD ───────────────────────────
    interface Greeter {
        String MAX = "x";              // implicitly PUBLIC STATIC FINAL — a global
        //                                constant, not per-instance state. People
        //                                discover this by writing a broken counter.
        // int count;                  // ✗ NOT ALLOWED. No instance fields. THE LINE.
        // Greeter() { }               // ✗ NOT ALLOWED. No constructors.

        String name();                 // implicitly public abstract

        default String greet() {       // Java 8: a BODY
            return "Hello, " + name() + prefix();
        //                     ^^^^^^ it can only call the interface's OWN methods.
        //   No fields exist to read. That limit is exactly why defaults did not
        //   turn interfaces into classes.
        }
        private String prefix() { return "!"; }   // Java 9: shared helper, hidden
        static Greeter of(String n) { return () -> n; }   // Java 8, NOT INHERITED
    }
    // MyGreeter.of(...) does NOT exist just because Greeter.of does. Deliberate.

    // ── THE DIAMOND, AND JAVA REFUSING TO GUESS ─────────────────────────
    interface A { default String hi() { return "A"; } }
    interface B { default String hi() { return "B"; } }
    class C implements A, B { }        // ✗ COMPILE ERROR: "inherits unrelated
    //                                    defaults for hi() from types A and B"
    class C implements A, B {
        @Override public String hi() { return A.super.hi(); }
    //                                 ^^^^^^^^^ compiles to invokespecial naming the
    //   interface — the ONLY way to reach a specific inherited default explicitly.
    }

    // ── "CLASS WINS", AND WHY ───────────────────────────────────────────
    class Base { public String hi() { return "Base"; } }
    interface I { default String hi() { return "I"; } }
    class D extends Base implements I { }
    new D().hi();                      // "Base" — the CLASS wins, always.
    // This is a COMPATIBILITY rule: a default added in a later JDK must never
    // silently override behaviour an existing class already had.

    // ── WHY DEFAULTS EXIST AT ALL ───────────────────────────────────────
    // Java 8 needed to add these to java.util.Collection, which millions of classes
    // implement in code the JDK team cannot see:
    default Stream<E> stream()                     { ... }
    default void forEach(Consumer<? super T> a)    { for (T t : this) a.accept(t); }
    default boolean removeIf(Predicate<? super E>) { ... }
    // ^ As ABSTRACT methods these would have broken every implementor on Earth at
    //   compile time. As defaults they broke nobody. THAT is what the feature is for.

    // ── AN ABSTRACT CLASS: state, constructor, protected, final ─────────
    abstract class Animal {
        protected final String name;        // ← STATE. The thing an interface cannot do.
        protected Animal(String name) { this.name = name; }   // ← invariant established
        public final String describe() {    // ← FINAL: the template cannot be broken
            return name + " says " + speak();
        }
        protected abstract String speak();  // ← the hook subclasses fill in
    }

    // ── THE PATTERN THAT USES BOTH ──────────────────────────────────────
    public interface Shape { double area(); String name(); }      // THE TYPE
    public abstract class AbstractShape implements Shape {        // a CONVENIENCE
        @Override public String name() { return getClass().getSimpleName(); }
    }
    class Circle extends AbstractShape { public double area() { return ...; } }
    record Square(double side) implements Shape {      // ← a record CANNOT extend a
        public double area() { return side * side; }   //   class, only implement an
        public String name() { return "Square"; }      //   interface. Which is why
    }                                                  //   the TYPE must be the
    //                                                     interface.

    // ── AND WHAT YOU MAY NOT DEFAULT ────────────────────────────────────
    // interface X { default String toString() { ... } }   ✗ COMPILE ERROR
    // equals, hashCode and toString come from Object; "class wins" would make the
    // default unreachable anyway, and an interface must not redefine identity.""",

"""9. THE TRACE — the same design, three ways, and what each forbids

REQUIREMENT: every shape reports an area and a name; the name defaults to the class's simple name.

    DESIGN 1 — ABSTRACT CLASS ONLY
    consequence                                            verdict
    ---------------------------------------------------------------------------------
    `class Circle extends AbstractShape`                    fine
    `class Circle extends JComponent` — already has a       ✗ IMPOSSIBLE. One
    superclass                                                superclass, and it is
                                                              already taken.
    `record Square(double side)`                            ✗ IMPOSSIBLE. Records
                                                              cannot extend a class.
    `enum Tile implements ...`                              ✗ IMPOSSIBLE. Same reason.
    ---------------------------------------------------------------------------------
    THE ABSTRACT CLASS SPENT THE ONE INHERITANCE SLOT. Any type that already has a parent — or that is
    a record or an enum — simply cannot participate.

    DESIGN 2 — INTERFACE WITH A DEFAULT
    consequence                                            verdict
    ---------------------------------------------------------------------------------
    every kind of type can implement it                     fine
    the default `name()` is shared                          fine
    a shared `final String label` field                     ✗ IMPOSSIBLE. No state.
    validating in a constructor                             ✗ IMPOSSIBLE. No
                                                              constructors.
    making `describe()` final so no one breaks the template ✗ IMPOSSIBLE. Defaults
                                                              cannot be final.
    ---------------------------------------------------------------------------------
    MAXIMUM FREEDOM FOR IMPLEMENTORS, NO ABILITY TO ENFORCE ANYTHING BEYOND THE SIGNATURES.

    DESIGN 3 — INTERFACE + SKELETAL ABSTRACT CLASS
    consequence                                            verdict
    ---------------------------------------------------------------------------------
    `Shape` is the type callers depend on                   fine
    `AbstractShape` gives the shared machinery, state,      fine
    constructor and final template
    `class Circle extends AbstractShape`                    takes the shortcut
    `class Widget extends JComponent implements Shape`      implements directly
    `record Square(...) implements Shape`                   works
    ---------------------------------------------------------------------------------
    NOBODY IS FORCED INTO THE HIERARCHY AND NOBODY IS DENIED THE CONVENIENCE. This is why the entire
    collections framework is built this way, and it is the answer that shows you have hit design 1's
    wall in real code.

NOW THE RESOLUTION TRACE — which body actually runs, given a diamond:

    hierarchy                                    `new D().hi()`   rule that fired
    ---------------------------------------------------------------------------------
    D implements A                               "A"              only candidate
    D implements A, B (unrelated defaults)       COMPILE ERROR    rule 3: Java refuses
                                                                  to guess
    D implements B, where `B extends A`          "B"              rule 2: more specific
                                                                  interface wins
    D extends Base implements I                  "Base"           rule 1: CLASS WINS
    D implements A, B with an explicit override  whatever you     you resolved it with
                                                 chose            A.super.hi()
    ---------------------------------------------------------------------------------
    ROW 2 IS THE DESIGN DECISION WORTH ADMIRING. Every other language with default-method-like features
    picks a winner by some ordering rule; Java makes it a compile error and forces the author to state
    the intent. Ambiguity becomes a conversation with the compiler rather than a surprise at runtime.

    AND ROW 4 IS THE COMPATIBILITY GUARANTEE. If a future JDK adds `default String hi()` to an
    interface you implement, and your class already has an inherited `hi()`, YOUR BEHAVIOUR DOES NOT
    CHANGE. Without that rule, upgrading the JDK could silently alter running programs.

WHAT PRODUCED WHAT:
    NO STATE IN INTERFACES     produced the diamond being answerable at all, and produced design 2's
                               entire list of "impossible" rows.
    ONE SUPERCLASS             produced design 1's wall.
    INTERFACE EVOLUTION        produced default methods, and therefore produced `Collection.stream()`
                               existing without breaking a single implementor.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Interface: no instance fields, no constructors, everything implicitly public (except private
    methods since 9), implemented by many; fields are implicitly `public static final`.
    Abstract class: fields, constructors, `protected`, `final` methods; extended by ONE.
    Default methods: Java 8, for interface EVOLUTION. Private interface methods: Java 9.
    Diamond resolution: 1) class wins, 2) more specific interface wins, 3) compile error.
    `equals`, `hashCode` and `toString` cannot be default methods.
    Static interface methods are NOT inherited by implementors.
    Dispatch cost: `invokeinterface` is historically slower than `invokevirtual`, and the JIT usually
    inlines both away at a monomorphic call site.

THE #1 MISTAKE: thinking default methods were about multiple inheritance. They exist so `Collection`
could gain `stream()` without breaking every implementor on Earth.

THE #2 MISTAKE: trying to keep per-instance state in an interface. Every field is `public static final`
— one value, shared globally.

THE #3 MISTAKE: the constant interface. It becomes permanent public API and can never be removed.

THE #4 MISTAKE: expecting static interface methods to be inherited. They are not.

THE #5 MISTAKE: assuming an interface default beats an inherited class method. Class wins, always, for
compatibility.

THE #6 MISTAKE: choosing an abstract class for a type that records, enums or already-parented classes
must implement. You have spent their one inheritance slot.

THE #7 MISTAKE: not offering a skeletal implementation alongside an interface. It costs one class and
removes the entire trade-off.

THE #8 MISTAKE: adding a default method to a released interface without considering diamonds. It is
source-compatible for single implementors and a compile error for anyone implementing two interfaces
that now both define it.

THE #9 MISTAKE: an abstract class constructor calling an abstract method. The override runs before the
subclass's fields exist.

THE #10 MISTAKE: deep abstract hierarchies. Past two levels nobody can say which class contributes what.
Compose instead.

THE #11 MISTAKE: creating an interface with one implementation "for testability". Modern mocking handles
classes; add it when there is a second implementation or a real boundary.

THE #12 MISTAKE: using an open interface where the implementations are a known, closed set. `sealed`
gives you exhaustiveness checking in `switch`, which dynamic dispatch never did.

ONE-SENTENCE TAKEAWAY: after Java 8 gave interfaces method bodies the only hard technical differences
left are STATE (interfaces have no instance fields), constructors, and one-superclass-versus-many — and
the reason defaults were added was INTERFACE EVOLUTION, so `Collection.stream()` could exist without
breaking millions of implementors, which is also why a default can only call the interface's own
methods and why "class wins" in the diamond rules; choose an interface for a CAPABILITY and anything
crossing a boundary, an abstract class when there is genuine shared state with invariants to protect,
and in practice offer BOTH via the interface-plus-skeletal-implementation pattern the collections
framework is built on — because an abstract class spends the implementor's one inheritance slot, which
locks out records, enums, and every class that already has a parent.""",
]


DEEP["ConcurrentHashMap and friends — and why null is forbidden"] = [
"""1. THE GOAL IN PLAIN ENGLISH — a map many threads can use without a lock around it

A plain `HashMap` used by two threads at once is not merely "might give wrong answers". It can CORRUPT
ITSELF: two threads resizing simultaneously in older JDKs could link a bucket's chain into a cycle, and
a later `get()` would spin forever at 100% CPU. That is a real, famous production failure mode, and it
is why "just wrap it in synchronized" existed.

    THE OBVIOUS FIX — ONE LOCK AROUND EVERYTHING — WORKS AND SCALES BADLY. `Hashtable` and
    `Collections.synchronizedMap` put every method behind a single monitor, so a hundred threads reading
    a hundred different keys queue up one at a time even though they never touch each other's data.

    `ConcurrentHashMap` MAKES READS COMPLETELY LOCK-FREE AND LOCKS WRITES ONLY AT THE INDIVIDUAL BUCKET.
    Two threads writing different keys almost never contend. Readers never block at all, ever, including
    while a writer is working.

    AND IT FORBIDS `null` — as a key AND as a value — which surprises everyone and is the most
    interesting design decision in the class. See section 2: it is not an arbitrary restriction, it is
    the removal of an ambiguity that CANNOT be resolved in a concurrent setting.

THE EVERYDAY VERSION: a library with a hundred thousand shelves. One lock on the front door means one
person inside at a time. Locking each shelf as you reshelve it means a hundred people work at once and
only collide when they want the same shelf. Readers just look — nobody has to wait for them, and they
never wait for anyone.

TERMS AS THEY APPEAR:
- BIN / BUCKET: one slot of the hash table, holding a chain (or a tree) of entries.
- CAS: compare-and-set. A single atomic instruction: "if this is still X, make it Y". No lock.
- LOCK-FREE: progress does not require acquiring a lock. A stalled thread cannot block others.
- WEAKLY CONSISTENT: an iterator that never throws and reflects the map at some point at or after it
  was created, without promising a single instant.""",

"""2. THE INTUITION — why null is banned, which is the whole design in miniature

START WITH THE PLAIN `HashMap`. `map.get(k)` returns null. That means one of two things: THERE IS NO
MAPPING, or THERE IS A MAPPING TO null. You disambiguate with `map.containsKey(k)`.

    NOW MAKE IT CONCURRENT AND TRY THE SAME THING:

        if (map.get(k) == null) {          // ← is it absent, or mapped to null?
            if (map.containsKey(k)) { ... } // ← ANOTHER THREAD MAY HAVE CHANGED IT
        }                                   //   BETWEEN THESE TWO LINES

    THE DISAMBIGUATION IS NOT POSSIBLE. Two separate calls cannot be made atomic by the caller, and the
    map has no single operation that answers "absent or null?" — the answer would already be stale by
    the time it returned. THE AMBIGUITY IS UNRESOLVABLE, NOT MERELY INCONVENIENT.

    So Doug Lea removed the ambiguity by removing the case. In `ConcurrentHashMap`, `get()` returning
    null means EXACTLY ONE THING: no mapping. That is a guarantee the caller can actually use.

    HIS OWN ARGUMENT WENT FURTHER: he has said that allowing null in maps and sets was probably a
    mistake in the original collections, and that it "creates more trouble than it's worth" — the
    concurrent classes simply did not repeat it. This is worth saying in an interview because it turns
    a memorised restriction into a design principle: AN API SHOULD NOT OFFER A RETURN VALUE WHOSE
    MEANING THE CALLER CANNOT DETERMINE.

THE SECOND INTUITION — WHY PER-BUCKET LOCKING IS ENOUGH:

    A hash map's whole premise is that keys SPREAD across buckets. If two threads pick random keys in a
    table with thousands of bins, the chance they land in the same bin is tiny. So locking the bin gives
    you almost the concurrency of no locking at all, with none of the reasoning burden.

    AND READS NEED NO LOCK BECAUSE OF ONE FIELD MODIFIER. The `val` and `next` fields of each node are
    `volatile`, and the table array is read with volatile semantics. A reader either sees the old value
    or the new one — never a half-written node — because writers publish a fully-constructed node with
    a single atomic store. THAT IS THE ENTIRE READ PATH: no lock, no CAS, no retry loop.

THE THIRD, AND THE ONE THAT CHANGES HOW YOU WRITE CODE: A THREAD-SAFE MAP DOES NOT MAKE YOUR CODE
THREAD-SAFE.

        if (!map.containsKey(k)) map.put(k, compute());   // ← STILL A RACE

    Both calls are individually atomic and the SEQUENCE is not. Two threads can both see "absent" and
    both compute and both put. THIS IS WHY THE CLASS PROVIDES `putIfAbsent`, `computeIfAbsent`,
    `compute` and `merge` — they are not conveniences, they are the only way to make a read-modify-write
    atomic, and they are the actual reason to use the class.""",

"""3. THE MECHANISM — CAS on empty bins, synchronized on the first node, and an approximate size

THE JAVA 8 REWRITE. Before it, `ConcurrentHashMap` had 16 SEGMENTS, each a small hash table with its own
`ReentrantLock` — so concurrency was capped at 16 regardless of table size, and each segment carried
overhead. Java 8 threw that away:

    THE TABLE IS A FLAT `Node<K,V>[]`, exactly like `HashMap`.
    INSERTING INTO AN EMPTY BIN uses a CAS on the array slot — NO LOCK AT ALL. This is the common case
    in a sparsely-populated table.
    IF THE BIN IS OCCUPIED, the writer `synchronized`s ON THE FIRST NODE OF THAT BIN and walks the
    chain. The lock's granularity is therefore one bucket, and the number of independent locks grows
    with the table.
    READS TAKE NOTHING. `Node.val` and `Node.next` are `volatile`.
    TREEIFICATION at 8 nodes in a bin, exactly like `HashMap`, so a degenerate hash cannot make an
    operation O(n).

RESIZING IS COOPERATIVE, which is the cleverest part: a thread that arrives during a resize does not
wait — it HELPS, taking a range of bins to transfer. So a resize is spread across whichever threads
happen to be working, instead of stalling everyone behind one.

`size()` IS AN ESTIMATE, AND THIS IS DELIBERATE. A single shared counter would be the hottest
contention point in the class — every write hitting one cache line. Instead the count is STRIPED across
an array of counter cells (the same idea as `LongAdder`): each thread increments its own cell, and
`size()` sums them. THE SUM IS NOT AN INSTANT SNAPSHOT, because writes happen while you are summing.

    USE `mappingCount()`, which returns `long` and is the documented preferred form. And treat any size
    as advisory: in a concurrent map, "the size" is not a well-defined quantity at a moment in time.

THE ATOMIC COMPOSITE OPERATIONS, which are the actual API:

    putIfAbsent(k, v)          insert only if absent; returns the existing value or null.
    computeIfAbsent(k, fn)     compute and insert only if absent. THE MEMOISATION PRIMITIVE, and the
                               function runs AT MOST ONCE per key even under contention.
    compute(k, fn)             read-modify-write, with the old value passed in. Returning null REMOVES.
    merge(k, v, fn)            insert v if absent, otherwise combine. The counter idiom.
    remove(k, expectedValue)   conditional remove.
    replace(k, old, new)       conditional replace.

    ALL OF THESE HOLD THE BIN LOCK FOR THE DURATION OF YOUR FUNCTION — which has a sharp consequence:
    THE FUNCTION MUST BE SHORT AND MUST NOT TOUCH THE MAP. A `computeIfAbsent` whose mapping function
    inserts another key that hashes to the same bin can deadlock; since Java 9 the class detects the
    same-key case and throws `IllegalStateException: Recursive update` rather than corrupting silently.

BULK OPERATIONS — `forEach`, `search`, `reduce` — take a PARALLELISM THRESHOLD: below that many
elements they run sequentially, above it they use the common ForkJoinPool. Passing `Long.MAX_VALUE`
means "always sequential", which is usually what you want.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `NullPointerException` FROM `put(k, null)`. Neither key nor value may be null. Code migrated
from `HashMap` fails at runtime, not at compile time, and often only on the path where the value is
absent.

CASE 2 — CHECK-THEN-ACT ON A THREAD-SAFE MAP. `if (!containsKey) put(...)` is a race even though each
call is atomic. Use `putIfAbsent` or `computeIfAbsent`.

CASE 3 — `computeIfAbsent` WHOSE FUNCTION TOUCHES THE MAP. The bin lock is held. Same key throws
`IllegalStateException` since Java 9; a different key in the same bin can deadlock.

CASE 4 — A LONG-RUNNING `computeIfAbsent` MAPPING FUNCTION. It blocks every other writer to that bin.
Loading from a database inside one serialises far more than you expect.

CASE 5 — TRUSTING `size()`. It is a sum of striped counters taken while writes continue. Use
`mappingCount()` and treat it as advisory.

CASE 6 — EXPECTING ITERATION TO BE A SNAPSHOT. Iterators are WEAKLY CONSISTENT: they never throw
`ConcurrentModificationException`, and they may or may not show concurrent changes. That is a different
guarantee, not a stronger one.

CASE 7 — COMPOUND OPERATIONS ACROSS TWO MAPS, or a map plus another variable. No single-map method can
make those atomic; you need a lock or a redesign.

CASE 8 — `Collections.synchronizedMap` AND EXPECTING SAFE ITERATION. Each method is synchronized; the
LOOP is not. You must synchronize on the map across the whole iteration yourself, and almost nobody
does.

CASE 9 — USING IT AS A CACHE WITH NO EVICTION. It grows without bound. `ConcurrentHashMap` is a map, not
a cache — Caffeine or Guava for eviction, expiry and refresh.

CASE 10 — MUTABLE KEYS. Same problem as `HashMap`: mutate a key after insertion and it lands in the
wrong bucket and is unfindable. Concurrency makes it harder to notice, not different.

CASE 11 — `keySet().removeIf(...)` UNDER HEAVY WRITE LOAD. Correct, but it is many individual atomic
removals rather than one atomic bulk operation, so the map is never in a "before" or "after" state as a
whole.

CASE 12 — ASSUMING BULK OPERATIONS ARE ATOMIC. `forEach`, `search` and `reduce` are not; they observe a
weakly consistent view.

CASE 13 — REACHING FOR IT WHEN THE MAP IS EFFECTIVELY IMMUTABLE. If it is populated once at startup and
only read afterwards, a plain `Map.copyOf(...)` is faster and states the intent.""",

"""5. THE ALTERNATIVES — the whole concurrent-collections family and when each is right

`ConcurrentHashMap` — the default for a shared mutable map. Lock-free reads, per-bin write locks,
atomic compute/merge. Use it unless you need one of the below.

`ConcurrentSkipListMap` / `ConcurrentSkipListSet` — the SORTED concurrent map. A lock-free skip list, so
O(log n) rather than O(1), and it gives you `firstKey`, `headMap`, `ceilingKey` and ordered iteration.
THERE IS NO CONCURRENT `TreeMap`, and this is why.

`CopyOnWriteArrayList` / `CopyOnWriteArraySet` — every WRITE copies the whole array; reads and iteration
take nothing and iterate a snapshot. Perfect for listener registries and configuration read on every
request and changed twice a day. Catastrophic for anything write-heavy.

THE BLOCKING QUEUES, which are how you should usually hand work between threads:
    `ArrayBlockingQueue`      bounded, one lock. Bounded is a FEATURE — it is backpressure.
    `LinkedBlockingQueue`     optionally bounded, separate head and tail locks, higher throughput.
    `SynchronousQueue`        zero capacity: a direct handoff. What `newCachedThreadPool` uses.
    `PriorityBlockingQueue`   unbounded, ordered.
    `DelayQueue`              elements become available at a time. Scheduling.
    `LinkedTransferQueue`     the fastest general-purpose one; `transfer` waits for a consumer.

THE ATOMICS AND ACCUMULATORS:
    `AtomicInteger` / `AtomicLong` / `AtomicReference` — CAS on a single variable.
    `LongAdder` — the SAME STRIPING IDEA as `ConcurrentHashMap`'s counter: many cells, summed on read.
    UNDER HIGH CONTENTION IT MASSIVELY OUTPERFORMS `AtomicLong`, because CAS on one hot cache line is
    the bottleneck. Use it for metrics counters; use `AtomicLong` when you need the exact current value
    at every increment.

WHAT NOT TO USE:
    `Hashtable` — legacy, one lock, and now also slower for no benefit.
    `Collections.synchronizedMap` — one lock, and iteration is still your problem.
    `Vector`, `Stack` — legacy for the same reason.

AND THE OPTION THAT IS OFTEN BEST: DO NOT SHARE THE MAP. Confine it to one thread and communicate
through a queue, or make it immutable and publish it with a volatile reference — replace the whole map
on update. NO LOCK, NO CONCURRENT CLASS, NO REASONING.

WHAT TO SAY: "`ConcurrentHashMap` and its atomic `compute`/`merge` methods, because a thread-safe map
does not make check-then-act safe. `ConcurrentSkipListMap` if I need ordering, `CopyOnWriteArrayList`
for read-mostly lists, `LongAdder` for contended counters — and a real cache library the moment I need
eviction, because this is a map, not a cache."

""",

"""6. HOW TO USE IT WELL — numbered steps

STEP 1 — NEVER PUT `null`. Not as a key, not as a value. Use a sentinel object or `Optional` as the
value type if absence must be recorded.

STEP 2 — REPLACE EVERY CHECK-THEN-ACT WITH AN ATOMIC METHOD. `putIfAbsent`, `computeIfAbsent`,
`compute`, `merge`, or the two-argument `remove`/`replace`.

STEP 3 — KEEP MAPPING FUNCTIONS SHORT AND PURE. They run while the bin lock is held. No I/O, no calls
back into the map, no locks of your own.

STEP 4 — USE `merge` FOR COUNTERS. `map.merge(k, 1L, Long::sum)` is the whole idiom and it is atomic.

STEP 5 — USE `mappingCount()` RATHER THAN `size()`, and treat any count as advisory.

STEP 6 — DO NOT EXPECT ITERATION TO BE A SNAPSHOT. Weakly consistent means it never throws and never
promises an instant.

STEP 7 — IF YOU NEED ORDERING, USE `ConcurrentSkipListMap`. There is no concurrent `TreeMap`.

STEP 8 — IF IT IS A CACHE, USE A CACHE LIBRARY. Eviction, expiry, refresh-ahead and stampede protection
are not this class's job, and an unbounded cache is a memory leak with a schedule.

STEP 9 — FOR HIGHLY CONTENDED COUNTERS, USE `LongAdder`. Striping beats CAS on one cache line by a wide
margin when many threads increment.

STEP 10 — IF THE MAP IS READ-ONLY AFTER STARTUP, MAKE IT IMMUTABLE. `Map.copyOf` is faster and states
the intent; concurrency machinery you do not need is still cost you pay.

STEP 11 — FOR COMPOUND INVARIANTS ACROSS MULTIPLE STRUCTURES, TAKE A LOCK. No concurrent collection can
make two of your operations atomic together.

STEP 12 — PREFER NOT SHARING AT ALL. Thread confinement plus a queue, or an immutable map republished
on change, removes the problem instead of managing it.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A plain HashMap shared between threads isn't just "might be wrong" — it can corrupt itself. In older
JDKs two threads resizing at once could link a bucket's chain into a cycle, and a later get() would spin
at 100% CPU forever. That's a real famous production failure.

The obvious fix — one lock around everything, which is what Hashtable and synchronizedMap do — works and
scales badly: a hundred threads reading a hundred different keys queue up one at a time even though
they never touch each other's data.

ConcurrentHashMap makes reads completely lock-free and locks writes at the individual BUCKET. Since
Java 8 it's a flat Node array like HashMap: inserting into an EMPTY bin is a CAS on the array slot with
no lock at all, and if the bin is occupied the writer synchronizes on the first node of that bin. So the
number of independent locks grows with the table. Before Java 8 it was 16 segments each with a lock, so
concurrency was capped at 16 no matter how big the map got.

Reads take nothing because Node.val and Node.next are volatile — a reader sees either the old value or
the new one, never a half-written node, because the writer publishes a fully-constructed node with one
atomic store. And resizing is COOPERATIVE: a thread arriving during a resize doesn't wait, it helps,
taking a range of bins to transfer.

The design decision I find most interesting is that null is forbidden — as a key AND as a value. In a
HashMap, get returning null means either "absent" or "mapped to null", and you disambiguate with
containsKey. In a concurrent map you CANNOT: another thread can change things between your two calls,
and there's no single operation that answers the question. The ambiguity is unresolvable, not just
inconvenient. So they removed the case rather than the confusion: in ConcurrentHashMap, get returning
null means exactly one thing. Doug Lea has said allowing null in maps was probably a mistake in the
original collections and the concurrent classes just didn't repeat it.

And then the thing that actually changes how you write code: A THREAD-SAFE MAP DOESN'T MAKE YOUR CODE
THREAD-SAFE. `if (!map.containsKey(k)) map.put(k, compute())` is still a race — both calls are atomic
and the SEQUENCE isn't, so two threads can both see absent and both put. Which is why putIfAbsent,
computeIfAbsent, compute and merge exist. Those aren't conveniences, they're the only way to make a
read-modify-write atomic, and they're the real reason to use the class.

The catch with them is that the bin lock is held while YOUR function runs. So the function has to be
short and must not touch the map — a computeIfAbsent whose function inserts another key hashing to the
same bin can deadlock, and since Java 9 the same-key case throws IllegalStateException: Recursive
update rather than corrupting silently.

One more: size() is an estimate. A single counter would be the hottest contention point in the class, so
the count is striped across cells like LongAdder and summed on read. Use mappingCount, and treat any
size in a concurrent map as advisory — "the size at an instant" isn't really a well-defined quantity.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE RACE A THREAD-SAFE MAP DOES NOT FIX ─────────────────────────
    if (!map.containsKey(k)) {         // ← thread A: absent
        map.put(k, expensive());       // ← thread B ran the SAME two lines in the gap
    }                                  //   Both compute. Both put. One result is lost.
    // Each call is atomic. THE SEQUENCE IS NOT. This is the bug the class exists to
    // remove, and using ConcurrentHashMap without changing this line fixes nothing.

    map.computeIfAbsent(k, key -> expensive());
    //  ^^^^^^^^^^^^^^^ atomic. The function runs AT MOST ONCE per key, even with a
    //  hundred threads arriving simultaneously.

    map.merge(userId, 1L, Long::sum);  // ← the counter idiom, atomic, one line
    map.compute(k, (key, old) -> old == null ? v : combine(old, v));
    map.remove(k, expectedValue);      // ← conditional; plain remove(k) is not

    // ── WHY null IS FORBIDDEN ───────────────────────────────────────────
    Object v = hashMap.get(k);
    if (v == null) {
        if (hashMap.containsKey(k)) { /* mapped TO null */ }
        else                        { /* absent        */ }
    }
    // ^ Works single-threaded. In a CONCURRENT map another thread can change the
    //   entry BETWEEN those two calls, and there is no single operation that answers
    //   "absent or null?". THE AMBIGUITY IS UNRESOLVABLE — so the case was removed.
    chm.put(k, null);                  // → NullPointerException
    chm.put(null, v);                  // → NullPointerException
    // Now `chm.get(k) == null` means EXACTLY ONE THING: no mapping.

    // ── THE WRITE PATH, IN OUTLINE ──────────────────────────────────────
    for (Node<K,V>[] tab = table;;) {
        if ((f = tabAt(tab, i)) == null) {
            if (casTabAt(tab, i, null, new Node<>(hash, key, value)))
    //          ^^^^^^^^^ EMPTY BIN → a single CAS on the array slot. NO LOCK. This is
    //          the common case in a sparsely populated table.
                break;
        } else {
            synchronized (f) {         // ← lock the FIRST NODE of this bin only
    //          ^^^^^^^^^^^^ granularity is ONE BUCKET, and the number of independent
    //          locks grows with the table. (Pre-Java-8: 16 segment locks, forever.)
                ... walk the chain or the tree, insert or replace ...
            }
        }
    }
    static class Node<K,V> {
        final int hash; final K key;
        volatile V val;                // ← THE ENTIRE REASON READS NEED NO LOCK:
        volatile Node<K,V> next;       //   a reader sees the old value or the new one,
    }                                  //   never a half-written node.

    // ── THE MAPPING FUNCTION RUNS UNDER THE BIN LOCK ────────────────────
    map.computeIfAbsent(k, key -> { map.put(other, v); return x; });
    //                              ^^^^^^^^^^^^^^^^ TOUCHING THE MAP while holding
    //   its bin lock. Same key → IllegalStateException: Recursive update (Java 9+).
    //   Different key, same bin → DEADLOCK.
    map.computeIfAbsent(k, key -> db.load(key));
    //                              ^^^^^^^^^^^ a database call under the bin lock —
    //   every other writer to that bin waits for the network. Load outside, then put.

    // ── SIZE IS AN ESTIMATE, ON PURPOSE ─────────────────────────────────
    map.size();                        // int, and a sum of STRIPED counter cells
    map.mappingCount();                // long, and the documented preferred form
    // A single shared counter would be the hottest cache line in the class, so the
    // count is striped exactly like LongAdder and summed on read. Advisory, always.

    // ── AND WHAT IT IS NOT ──────────────────────────────────────────────
    // ConcurrentHashMap is a MAP, not a CACHE. No eviction, no expiry, no refresh,
    // no stampede protection. An unbounded cache is a memory leak with a schedule.
    Caffeine.newBuilder().maximumSize(10_000).expireAfterWrite(5, MINUTES).build();""",

"""9. THE TRACE — four threads, four keys, and where each one actually waits

THE MAP has a 64-bin table. Four threads act at the same instant:

    thread  operation              bin  what it does                  waits for
    ---------------------------------------------------------------------------------
    T1      get("alpha")           12   volatile read of the node      NOTHING, EVER
    T2      put("beta", 1)         12   bin 12 is OCCUPIED by alpha    the bin-12 lock
                                        → synchronized on that node
    T3      put("gamma", 2)        40   bin 40 is EMPTY → a single     nothing
                                        CAS on the array slot
    T4      put("delta", 3)        12   same bin as T2                 T2's bin lock
    ---------------------------------------------------------------------------------
    ONLY T4 WAITED, AND ONLY BEHIND T2. T1 read while T2 was writing the same bin and did not block —
    it saw either the old chain or the new one, because the node's `val` and `next` are volatile and the
    new node was published with one atomic store. T3 never touched a lock at all.

    NOW CONTRAST `Collections.synchronizedMap`, same four operations:
    T1 waits, T2 waits, T3 waits, T4 waits — ALL BEHIND ONE MONITOR, including the reader and including
    the two threads working on completely unrelated keys. That is the entire difference, in one table.

THE CHECK-THEN-ACT RACE, traced — this is the bug that survives switching map implementations:

    time  Thread A                          Thread B                    map state
    ---------------------------------------------------------------------------------
    t0    containsKey("x") → false          —                           {}
    t1    —                                 containsKey("x") → false    {}
    t2    expensive() ... running           expensive() ... running     {}
    t3    put("x", A_result)                —                           {x=A}
    t4    —                                 put("x", B_result)          {x=B}
    ---------------------------------------------------------------------------------
    `expensive()` RAN TWICE and A's result was silently discarded. Every individual call was atomic and
    correct. If `expensive()` opened a connection, allocated an id, or charged a card, you now have two
    of them.

    THE SAME SEQUENCE WITH `computeIfAbsent`:
    t0    A enters computeIfAbsent, takes the bin lock
    t1    B enters computeIfAbsent, BLOCKS on the bin lock
    t2    A runs expensive(), stores, releases
    t3    B acquires, finds the value present, RETURNS IT WITHOUT CALLING THE FUNCTION
    ---------------------------------------------------------------------------------
    ONE CALL. Which is precisely why "the function runs at most once per key" is the guarantee worth
    knowing.

AND THE COST OF THAT GUARANTEE, traced with a slow function:

    t0    A: computeIfAbsent(k, key -> db.load(key))   ← takes the bin lock
    t1    A: waiting on the network                    ← STILL HOLDING THE BIN LOCK
    t2    B: put(otherKeyInSameBin, v)                 ← BLOCKED, on a network call
    t3    C: put(anotherKeyInSameBin, v)               ← BLOCKED
    t4    A: db returns after 200ms, releases
    ---------------------------------------------------------------------------------
    THE LOCK IS FINE-GRAINED AND YOUR FUNCTION IS NOT. Every writer to that bin waited 200 ms for a
    database you did not know they were waiting for. The fix is to load outside and `putIfAbsent`
    after — accepting that the load may occasionally run twice, which is usually the better trade.

WHAT PRODUCED WHAT:
    VOLATILE val AND next     produced T1 never waiting — the whole lock-free read path.
    CAS ON AN EMPTY BIN       produced T3 never waiting.
    PER-BIN synchronized      produced T4 waiting, and ONLY behind T2.
    THE BIN LOCK SPANNING     produced both the "at most once" guarantee and the 200 ms stall. Same
    YOUR FUNCTION             mechanism, read as a feature or a hazard depending on what you put in it.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `get`: O(1) average, LOCK-FREE. Never blocks, ever, even during a concurrent write or resize.
    `put`: O(1) average. A CAS on an empty bin; `synchronized` on the first node otherwise.
    Treeification at 8 nodes per bin, so a degenerate hash is O(log n) rather than O(n).
    Lock granularity: ONE BIN, and the number of locks grows with the table. (Pre-Java 8: 16 segments,
    fixed.)
    Resize: cooperative — arriving threads help transfer bins instead of waiting.
    `size()` / `mappingCount()`: a sum over striped counter cells. An ESTIMATE by design.
    Iterators: weakly consistent. Never throw, never promise an instant.
    `ConcurrentSkipListMap`: O(log n), sorted, lock-free. The only ordered concurrent map.

THE #1 MISTAKE: check-then-act on a thread-safe map. Each call is atomic and the sequence is not. Use
`computeIfAbsent` / `merge` / `putIfAbsent`.

THE #2 MISTAKE: putting `null`. Forbidden for both key and value, and the failure is at runtime.

THE #3 MISTAKE: doing real work inside a mapping function. The bin lock is held, so I/O there
serialises every writer to that bin.

THE #4 MISTAKE: calling back into the map from a mapping function. `IllegalStateException` on the same
key, deadlock on a different key in the same bin.

THE #5 MISTAKE: relying on `size()` as exact. Striped counters, summed while writes continue.

THE #6 MISTAKE: expecting iteration to be a snapshot. Weakly consistent is a different guarantee, not a
weaker version of the same one.

THE #7 MISTAKE: `Collections.synchronizedMap` for concurrent iteration. Per-method locking; the loop is
yours to protect.

THE #8 MISTAKE: using it as a cache. No eviction, no expiry — an unbounded cache is a scheduled memory
leak. Use Caffeine.

THE #9 MISTAKE: `AtomicLong` for a hot counter. `LongAdder` stripes exactly like this class's own size
counter and wins by a wide margin under contention.

THE #10 MISTAKE: reaching for a concurrent map when the data is written once at startup. `Map.copyOf`
is faster and says what you mean.

THE #11 MISTAKE: expecting a single map to protect an invariant spanning two structures. Nothing here
can make two of your operations atomic together.

ONE-SENTENCE TAKEAWAY: `ConcurrentHashMap` makes reads entirely lock-free — `val` and `next` are
volatile, so a reader sees the old node or the new one and never blocks — and locks writes at ONE BIN
(a CAS when the bin is empty, `synchronized` on its first node otherwise), with cooperative resizing and
a deliberately approximate striped size; `null` is banned as key and value because `get` returning null
would otherwise be ambiguous between "absent" and "mapped to null" and NO SEQUENCE OF CALLS CAN
DISAMBIGUATE IT CONCURRENTLY; and the fact that actually changes your code is that a thread-safe map
does not make check-then-act safe, so `putIfAbsent`, `computeIfAbsent`, `compute` and `merge` are the
real API — remembering that they hold the bin lock while YOUR function runs, which is what makes "at
most once per key" a guarantee and a database call in there a stall.""",
]


DEEP["CompletableFuture — composing async work without blocking"] = [
"""1. THE GOAL IN PLAIN ENGLISH — a result that has not arrived yet, that you can still build on

`Future` arrived in Java 5 and is almost useless. You submit work, you get a `Future`, and the ONLY
thing you can do with it is call `get()` — WHICH BLOCKS. You cannot ask it to notify you. You cannot
chain a transformation. You cannot combine two of them. You cannot attach an error handler.

    SO EVERY `Future` EVENTUALLY BECOMES A BLOCKED THREAD, which defeats the purpose of having started
    the work asynchronously in the first place.

`CompletableFuture` (Java 8) is two things at once:

    A FUTURE YOU CAN COMPLETE YOURSELF — `complete(value)` or `completeExceptionally(e)` — which is what
    lets you adapt any callback-based API into one.
    AND A COMBINATOR LIBRARY: describe what to do WHEN the value arrives, without ever waiting for it.

    THE SHIFT IS FROM "GET THE VALUE" TO "DESCRIBE THE PIPELINE". You never hold a thread waiting. You
    say "when the user arrives, fetch their orders; when those arrive, render the page; if anything
    fails, return the cached version" — and the whole description executes itself as results arrive.

THE EVERYDAY VERSION: ordering a coffee. `Future.get()` is standing at the counter staring at the
barista until it is ready — you are occupied the whole time. `CompletableFuture` is taking a buzzer:
you say "when it is ready, I will add sugar and take it to table 4", and then you go and do something
else. The instructions are attached to the buzzer, not to you.

    AND THE MODERN CAVEAT WORTH STATING UP FRONT: since Java 21, VIRTUAL THREADS make blocking cheap
    again, so for simple sequential I/O you can go back to plain blocking calls and skip all of this.
    `CompletableFuture` remains the right tool for genuine FAN-OUT — several independent calls combined
    — and for timeouts and fallbacks.

TERMS AS THEY APPEAR:
- STAGE: one step in the chain. The interface is literally `CompletionStage`.
- COMPLETE: the moment a value (or an exception) becomes available.
- COMBINATOR: a method that builds a new stage from existing ones — `thenApply`, `thenCombine`, `allOf`.""",

"""2. THE INTUITION — the naming scheme, and the two decisions it encodes

THE API LOOKS ENORMOUS — around fifty methods — AND IT IS ACTUALLY A GRID. Learn the two axes and the
whole thing collapses:

    AXIS 1 — WHAT YOUR FUNCTION DOES WITH THE VALUE:
        thenApply(fn)      takes T, returns U            → a TRANSFORM (this is `map`)
        thenAccept(c)      takes T, returns nothing      → a SIDE EFFECT
        thenRun(r)         ignores the value entirely    → "just do this afterwards"
        thenCompose(fn)    takes T, returns ANOTHER CompletableFuture  → this is `flatMap`
        thenCombine(other, fn)  waits for TWO, combines them           → this is `zip`

    AXIS 2 — WHICH THREAD RUNS IT:
        thenApply(fn)                  runs on WHICHEVER THREAD COMPLETED THE PREVIOUS STAGE — or on
                                       YOUR CALLING THREAD if the stage is already complete.
        thenApplyAsync(fn)             runs on the common ForkJoinPool.
        thenApplyAsync(fn, executor)   runs on YOUR executor. ← THE ONLY ONE TO USE IN PRODUCTION.

    AXIS 2 IS WHERE THE REAL BUGS LIVE. The non-async form gives you no idea which thread your code runs
    on: it may be the calling thread, or a pool thread belonging to whatever produced the value.
    Attaching an expensive callback with `thenApply` can therefore hijack a Netty I/O thread or a
    database driver's callback thread — a genuinely serious production problem.

`thenApply` VERSUS `thenCompose` IS THE CLASSIC QUESTION, and the answer is `map` versus `flatMap`:

    If your function returns a PLAIN VALUE, use `thenApply`.
    If your function returns ANOTHER `CompletableFuture` — which it does whenever the next step is
    itself async — use `thenCompose`. Using `thenApply` there gives you
    `CompletableFuture<CompletableFuture<User>>`, a nested future you then have to unwrap by hand.
    IT IS EXACTLY `Optional.map` VERSUS `Optional.flatMap`, and exactly `Stream.map` versus
    `Stream.flatMap`. Same shape, three places in the JDK.

THE OTHER DECISION THE API ENCODES: FAILURE IS A VALUE THAT FLOWS THROUGH THE PIPELINE.

    If any stage throws, every downstream `thenApply`/`thenAccept` is SKIPPED and the exception is
    carried forward, until something handles it. That is exactly how a `try` block behaves — the
    remaining statements do not run — and it is why you can put one `exceptionally` at the end of a
    ten-stage chain rather than a try/catch around each step.

    `exceptionally(fn)`   handle the failure, supply a fallback value. Only runs on failure.
    `handle((v, e) -> …)` runs on BOTH paths; you inspect `e` and decide.
    `whenComplete((v,e))` observes both and CHANGES NOTHING — the result passes through unaltered.
                          This is the logging hook.""",

"""3. THE MECHANISM — the default executor, exception wrapping, and what cancellation is not

THE DEFAULT EXECUTOR IS `ForkJoinPool.commonPool()`, AND THIS IS THE SINGLE MOST IMPORTANT OPERATIONAL
FACT ABOUT THE CLASS.

    Its parallelism is `availableProcessors() - 1`. On a 2-core container that is ONE THREAD.
    It is shared by every parallel stream, every executor-less `CompletableFuture`, and every library
    doing either, across the entire JVM.
    Its threads are DAEMON threads, so pending work does not keep the JVM alive and can be killed at
    shutdown with no notice.
    IT IS SIZED FOR CPU-BOUND WORK. Every blocking call you put on it removes one of your very few
    threads for the duration.
    THEREFORE: PASS AN EXECUTOR TO EVERY `*Async` METHOD AND TO `supplyAsync`. This is not a style
    preference; the default is wrong for I/O and the failure is a JVM-wide stall.

EXCEPTION WRAPPING, which trips everyone once:
    Inside the pipeline, a thrown exception is wrapped in a `CompletionException`.
    `get()` throws the CHECKED `ExecutionException` wrapping the cause.
    `join()` throws the UNCHECKED `CompletionException` wrapping the cause.
    So the handler you write almost always needs `e.getCause()`, and code that catches your domain
    exception directly will silently not match. `join()` is generally preferable inside lambdas
    precisely because it is unchecked and functional interfaces cannot declare `throws`.

CANCELLATION IS WEAKER THAN IT LOOKS. `cancel(true)` completes the future exceptionally with a
`CancellationException` — IT DOES NOT INTERRUPT THE RUNNING THREAD. The `mayInterruptIfRunning` flag is
ignored, and the Javadoc says so. Work started by `supplyAsync` runs to completion regardless; you have
cancelled the RESULT, not the WORK. If you need real cancellation you must plumb it yourself, and
`StructuredTaskScope` exists partly because of this.

TIMEOUTS DID NOT EXIST UNTIL JAVA 9. `orTimeout(t, unit)` completes exceptionally with
`TimeoutException`; `completeOnTimeout(v, t, unit)` completes with a fallback value. Before Java 9 you
had to build one from a scheduled executor, which is why so much older code blocks on `get(timeout)`
instead.

`allOf` AND `anyOf`, and the sharp edges on both:
    `allOf(a, b, c)` returns `CompletableFuture<Void>` — it gives you NO RESULTS. The idiom is to join
    each individual future after `allOf` completes, at which point every `join()` returns immediately.
    `allOf` fails as soon as ANY input fails, but the others keep running.
    `anyOf(...)` returns `CompletableFuture<Object>` — untyped, because the inputs need not share a
    type — and it completes on the first to finish EITHER WAY, including with a failure.

WHAT VIRTUAL THREADS CHANGED. Much of this API existed to avoid blocking a scarce OS thread. On Java 21
blocking is cheap, so the sequential case — call A, then call B with A's result — is better written as
two ordinary blocking calls in a virtual thread, with a real stack trace and a working debugger. WHAT
`CompletableFuture` STILL DOES BEST IS FAN-OUT, timeouts, and fallbacks — the cases where the structure
genuinely is a graph rather than a line.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — NOT PASSING AN EXECUTOR. Everything lands on the common pool, sized `cores - 1`, shared
JVM-wide. On a 2-core container that is one thread for the entire process's async work.

CASE 2 — BLOCKING INSIDE A STAGE ON THE COMMON POOL. A JDBC call or a `get()` inside a
`supplyAsync` starves parallel streams and every other library using the pool.

CASE 3 — `thenApply` WHERE `thenCompose` BELONGS. Gives
`CompletableFuture<CompletableFuture<T>>`. It compiles, and the nesting is discovered later.

CASE 4 — NOT KNOWING WHICH THREAD A NON-ASYNC CALLBACK RUNS ON. It may be your calling thread, or the
completing thread — which could be a Netty I/O thread or a driver callback thread you must not occupy.

CASE 5 — `allOf` AND EXPECTING RESULTS. It returns `Void`. Join each future afterwards.

CASE 6 — CATCHING YOUR OWN EXCEPTION TYPE IN A HANDLER. It arrives wrapped in `CompletionException`.
Unwrap with `getCause()` or the `catch` will not match.

CASE 7 — EXPECTING `cancel(true)` TO INTERRUPT. It does not. The work runs to completion; only the
result is discarded.

CASE 8 — `join()` OR `get()` IN THE MIDDLE OF A CHAIN. It blocks, which is exactly what the whole API
exists to avoid, and on a pool thread it can deadlock the pool.

CASE 9 — SWALLOWING FAILURES. A chain with no `exceptionally`/`handle`, whose result nobody joins,
fails completely silently. THE SAME SHAPE AS `ExecutorService.submit` WITH AN IGNORED `Future`.

CASE 10 — `whenComplete` USED AS A HANDLER. It observes and passes the result through unchanged; it
does NOT recover. Use `exceptionally` or `handle` to change the outcome.

CASE 11 — DAEMON THREADS AT SHUTDOWN. Common-pool threads are daemons, so pending work can be killed at
JVM exit with no warning.

CASE 12 — LOSING `ThreadLocal` CONTEXT ACROSS STAGES. MDC logging context, security context and
transaction context do not follow the value to another thread. Frameworks provide decorators; without
one your logs lose their correlation id.

CASE 13 — BUILDING A CHAIN AND NEVER TRIGGERING IT. A `CompletableFuture` created but never completed
simply never runs its dependents. Nothing warns.

CASE 14 — UNBOUNDED FAN-OUT. `list.stream().map(x -> supplyAsync(...))` over ten thousand items submits
ten thousand tasks at once. Bound it with a `Semaphore` or a sized executor.""",

"""5. THE ALTERNATIVES — including the one that makes most of this unnecessary

VIRTUAL THREADS (Java 21) FOR SEQUENTIAL I/O. If the shape is "call A, then call B with A's result",
just write the two blocking calls in a virtual thread. You get a stack trace containing your caller, a
debugger that steps, and try/catch that spans the operation — all of which async code gives up.
`CompletableFuture` was largely a workaround for expensive threads, and that premise has changed.

STRUCTURED CONCURRENCY (`StructuredTaskScope`) FOR FAN-OUT. Fork several tasks, join them, and the
scope guarantees none outlives the block, cancels siblings on failure, and attaches child stack traces
to the parent. THIS IS THE SUCCESSOR for the parallel case, and it fixes exactly the two things
`CompletableFuture` is weakest at: lifetime and cancellation.

`CompletableFuture` IS STILL RIGHT FOR:
    combining a fixed set of independent calls — `thenCombine`, `allOf`;
    timeouts and fallbacks — `orTimeout`, `completeOnTimeout`, `exceptionally`;
    adapting a CALLBACK-BASED API into something composable, via `complete`/`completeExceptionally`;
    library APIs that must return a non-blocking result to callers you do not control.

REACTIVE (Reactor, RxJava) WHEN YOU HAVE A STREAM, NOT A VALUE. `CompletableFuture` holds exactly ONE
result. If the answer is a sequence with backpressure, windowing, merging or retry policies, that is a
`Flux`, and no amount of futures will express it. Conversely, do not adopt reactive for a single async
value — you are paying the whole cost for none of the benefit.

`ExecutorService` + `Future` — only when you genuinely just want to fire work and block later, and even
then `CompletableFuture.supplyAsync` gives you a superset.

RESILIENCE LIBRARIES — Resilience4j, Failsafe — for retry, circuit breaking, bulkheads and rate
limiting. Hand-rolling retry on a `CompletableFuture` chain is possible and rarely correct: jitter,
budgets and half-open states are the hard parts.

`Flow` (Java 9) — the reactive-streams interfaces in the JDK. An interop SPI, not something to build on
directly.

WHAT TO SAY: "On Java 21 I would write sequential I/O as plain blocking calls in a virtual thread,
because the stack traces and debugging are worth more than the thread saving. I would use
`CompletableFuture` for genuine fan-out, timeouts and fallbacks — always passing an explicit executor,
because the default is the common pool sized to cores minus one and shared by the whole JVM — and
`StructuredTaskScope` where I can, since it gives bounded lifetimes and real cancellation, which
`CompletableFuture` does not."

""",

"""6. HOW TO USE IT WELL — numbered steps

STEP 1 — ASK WHETHER YOU NEED IT AT ALL. Sequential I/O on Java 21 is better as blocking calls in a
virtual thread. Reach for this when the shape is a graph, not a line.

STEP 2 — ALWAYS PASS AN EXECUTOR. Every `supplyAsync` and every `*Async` method. The default is the
common pool, sized `cores - 1`, shared by the entire JVM.

STEP 3 — NEVER BLOCK INSIDE A STAGE RUNNING ON THE COMMON POOL. Use a dedicated I/O executor.

STEP 4 — USE `thenCompose` WHEN THE FUNCTION RETURNS A FUTURE, `thenApply` WHEN IT RETURNS A VALUE.
flatMap versus map.

STEP 5 — PREFER THE EXPLICIT `*Async(fn, executor)` FORMS even when the non-async one would work, so
that which thread runs your code is stated rather than inherited.

STEP 6 — TERMINATE EVERY CHAIN WITH `exceptionally` OR `handle`, AND LOG. An unhandled, unjoined chain
fails in complete silence.

STEP 7 — UNWRAP `CompletionException` IN HANDLERS. `e.getCause()` is the exception you actually threw.

STEP 8 — ADD A TIMEOUT. `orTimeout` or `completeOnTimeout` (Java 9+). A future with no timeout is a hang
with extra steps.

STEP 9 — AFTER `allOf`, JOIN EACH FUTURE INDIVIDUALLY to collect results — `allOf` gives you `Void`.

STEP 10 — DO NOT RELY ON `cancel` TO STOP WORK. It discards the result; the task keeps running. Plumb a
cancellation flag if you need one.

STEP 11 — BOUND YOUR FAN-OUT. Mapping a large collection to `supplyAsync` submits one task per element.

STEP 12 — PROPAGATE CONTEXT DELIBERATELY. MDC, security and transaction context do not follow the value
across threads; wrap the executor or pass the context explicitly.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Future from Java 5 is almost useless: the only thing you can do with it is call get(), which BLOCKS.
You can't be notified, you can't chain, you can't combine two, you can't attach an error handler. So
every Future eventually becomes a blocked thread, which defeats the point of starting the work
asynchronously.

CompletableFuture is two things. It's a future you can complete yourself — complete or
completeExceptionally — which is what lets you wrap any callback-based API. And it's a combinator
library: you describe what to do WHEN the value arrives instead of waiting for it.

The API looks enormous, about fifty methods, but it's really a grid with two axes. The first is what
your function does with the value: thenApply is map, thenAccept is a side effect, thenRun ignores the
value, thenCompose is flatMap, thenCombine is zip. The thenApply-versus-thenCompose question is just map
versus flatMap — if your function returns another CompletableFuture, which it does whenever the next
step is also async, you need thenCompose, or you get a CompletableFuture of a CompletableFuture. Same
distinction as Optional.map versus flatMap.

The second axis is WHICH THREAD runs it, and that's where the real bugs are. Plain thenApply runs on
whichever thread completed the previous stage — or on your CALLING thread if the stage is already
complete. So you genuinely don't know where your code runs, and attaching something expensive can
hijack a Netty I/O thread or a driver's callback thread.

Which leads to the single most important operational fact: the default executor is
ForkJoinPool.commonPool, with parallelism of cores MINUS ONE. On a 2-core container that's one thread,
shared by every parallel stream and every executor-less future in the whole JVM, and it's sized for
CPU-bound work. So every blocking call you put on it removes one of your very few threads. Always pass
an explicit executor — that's not style, the default is wrong for I/O and the failure is a JVM-wide
stall.

Failure is a VALUE that flows through the pipeline: if a stage throws, every downstream thenApply is
skipped and the exception is carried forward until something handles it — exactly like the rest of a
try block not running. That's why one exceptionally at the end of a ten-stage chain works. Just
remember exceptions get wrapped in CompletionException, so handlers usually need getCause. And
whenComplete OBSERVES both outcomes and changes nothing — it's the logging hook, not a recovery.

Two things that surprise people. cancel(true) does NOT interrupt the running thread — the flag is
ignored, the work runs to completion, and you've cancelled the RESULT not the WORK. And allOf returns
Void, so you have to join each future afterwards to get results.

And I'd be honest about the modern picture: virtual threads made blocking cheap again, so on Java 21 I'd
write sequential I/O as plain blocking calls and get real stack traces and a working debugger back.
CompletableFuture still earns its place for genuine fan-out, timeouts and fallbacks — and
StructuredTaskScope is the better answer for fan-out now, because it gives bounded lifetimes and real
cancellation, which this doesn't.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHY Future WAS NOT ENOUGH ───────────────────────────────────────
    Future<User> f = executor.submit(() -> loadUser(id));
    User u = f.get();                  // ← BLOCKS. And that is the ONLY option.
    //                                    No callback, no chaining, no combining,
    //                                    no error handler. A thread is now parked.

    // ── THE TWO AXES OF THE API ─────────────────────────────────────────
    cf.thenApply(u -> u.name())            // map:      T → U
    cf.thenAccept(u -> log.info("{}", u))  // consume:  T → void
    cf.thenRun(() -> metrics.inc())        // ignore the value entirely
    cf.thenCompose(u -> loadOrders(u))     // FLATMAP:  T → CompletableFuture<U>
    cf.thenCombine(other, (a, b) -> merge(a, b))   // zip TWO futures

    cf.thenApply(fn)                   // runs on whichever thread COMPLETED the
    //                                    previous stage — or YOUR CALLING THREAD if
    //                                    it is already complete. You do not know.
    cf.thenApplyAsync(fn)              // the COMMON POOL. Sized cores-1. JVM-wide.
    cf.thenApplyAsync(fn, ioExecutor)  // ← THE ONLY FORM TO USE IN PRODUCTION

    // ── THE map/flatMap MISTAKE ─────────────────────────────────────────
    CompletableFuture<CompletableFuture<List<Order>>> nested =
        userFuture.thenApply(u -> loadOrders(u));
    //             ^^^^^^^^^ loadOrders RETURNS A FUTURE, so thenApply wraps a future
    //             in a future. It compiles. You discover it later.
    CompletableFuture<List<Order>> flat =
        userFuture.thenCompose(u -> loadOrders(u));      // ← flatMap

    // ── FAILURE IS A VALUE THAT FLOWS DOWN THE CHAIN ────────────────────
    loadUser(id)
        .thenCompose(u -> loadOrders(u))     // ← SKIPPED if loadUser failed
        .thenApply(this::render)             // ← SKIPPED
        .exceptionally(e -> cachedPage())    // ← the exception arrives HERE
    // Exactly like the rest of a try block not running. One handler for ten stages.

    .handle((v, e) -> e == null ? v : fallback())   // runs on BOTH paths
    .whenComplete((v, e) -> log.info("done {} {}", v, e))
    //             ^^^^^^ OBSERVES and passes the result through UNCHANGED. It is the
    //             logging hook, NOT a recovery. People use it as one and lose the fix.

    // ── THE WRAPPING THAT BREAKS YOUR catch ─────────────────────────────
    .exceptionally(e -> {
        if (e instanceof MyDomainException) { ... }        // ← NEVER MATCHES
        if (e.getCause() instanceof MyDomainException) { } // ← the real one
    //       ^^^^^^^^^^ everything is wrapped in CompletionException on the way here
    })
    // get()  throws the CHECKED ExecutionException.
    // join() throws the UNCHECKED CompletionException — preferable inside lambdas,
    //        because functional interfaces cannot declare `throws`.

    // ── THE OPERATIONAL FACT THAT MATTERS MOST ──────────────────────────
    CompletableFuture.supplyAsync(() -> jdbc.query(sql));
    //                                  ^^^^^^^^^^^^^^^ A BLOCKING CALL on
    //   ForkJoinPool.commonPool(), whose parallelism is availableProcessors() MINUS
    //   ONE — one thread on a 2-core container — shared by every parallel stream and
    //   every executor-less future in the entire JVM, and sized for CPU-bound work.
    CompletableFuture.supplyAsync(() -> jdbc.query(sql), ioExecutor);   // ← always

    // ── FAN-OUT, WHICH IS WHAT IT IS ACTUALLY GOOD AT ───────────────────
    var user   = supplyAsync(() -> loadUser(id),   io);
    var orders = supplyAsync(() -> loadOrders(id), io);
    var prefs  = supplyAsync(() -> loadPrefs(id),  io);
    CompletableFuture.allOf(user, orders, prefs)
    //               ^^^^^ returns CompletableFuture<VOID> — NO RESULTS. You must
        .thenApply(v -> new Page(user.join(), orders.join(), prefs.join()))
    //                            ^^^^^^ join each one; they return immediately now
        .orTimeout(2, SECONDS)         // ← Java 9. Before that, no timeout existed.
        .exceptionally(e -> Page.degraded());

    // ── WHAT cancel DOES NOT DO ─────────────────────────────────────────
    cf.cancel(true);
    //        ^^^^ mayInterruptIfRunning is IGNORED. The task runs to completion.
    //        You cancelled the RESULT, not the WORK. The Javadoc says so.""",

"""9. THE TRACE — three calls, four ways to arrange them

THE TASK: load a user (100 ms), their orders (150 ms) and their preferences (120 ms), then render.

    ARRANGEMENT 1 — SEQUENTIAL BLOCKING
    step                     elapsed    threads held
    ---------------------------------------------------------------------------------
    loadUser                 0–100ms    1 (blocked)
    loadOrders               100–250    1 (blocked)
    loadPrefs                250–370    1 (blocked)
    render                   370–375    1
    TOTAL 375 ms, one thread parked for 370 of them.

    ARRANGEMENT 2 — FAN-OUT WITH allOf
    step                     elapsed    threads held
    ---------------------------------------------------------------------------------
    all three submitted      0          3 pool threads, each blocked on I/O
    prefs completes          120        2
    orders completes         150        1  ← the slowest determines the total
    user completed at        100        —
    render                   150–155    1
    TOTAL 155 ms. THE SUM BECAME THE MAXIMUM. That is the entire point of the class.

    ARRANGEMENT 3 — THE ACCIDENTAL SEQUENTIAL CHAIN
    loadUser().thenCompose(u -> loadOrders(u)).thenCompose(o -> loadPrefs(o))
    ---------------------------------------------------------------------------------
    TOTAL 375 ms again — identical to arrangement 1, using three times the machinery.
    thenCompose means "AFTER this, do that". If the calls do not actually depend on
    each other, chaining them throws away the only benefit while keeping every cost.
    THIS IS THE MOST COMMON WAY CompletableFuture CODE ENDS UP SLOWER THAN BLOCKING
    CODE: the shape says parallel and the operators say sequential.

    ARRANGEMENT 4 — VIRTUAL THREADS, JAVA 21
    try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
        var u = scope.fork(() -> loadUser(id));   // plain blocking calls
        var o = scope.fork(() -> loadOrders(id));
        var p = scope.fork(() -> loadPrefs(id));
        scope.join().throwIfFailed();
        return new Page(u.get(), o.get(), p.get());
    }
    ---------------------------------------------------------------------------------
    TOTAL 155 ms — the same as arrangement 2 — with real stack traces, a working
    debugger, try/catch spanning the whole thing, and tasks that CANNOT outlive the
    block. This is why StructuredTaskScope is the successor for fan-out.

NOW THE THREAD TRACE — where a non-async callback actually runs:

    code                                        which thread runs the lambda
    ---------------------------------------------------------------------------------
    cf.thenApply(fn), cf already complete       YOUR CALLING THREAD
    cf.thenApply(fn), cf completes later        the thread that COMPLETED cf — which
                                                may be a Netty I/O thread, a JDBC
                                                driver callback thread, or a pool
                                                thread you have never heard of
    cf.thenApplyAsync(fn)                       a common-pool thread (cores - 1)
    cf.thenApplyAsync(fn, myExecutor)           yours. Stated, not inherited.
    ---------------------------------------------------------------------------------
    ROW 2 IS THE PRODUCTION HAZARD. Attach anything expensive there and you occupy a thread whose owner
    needs it for something else. The symptom is a completely unrelated subsystem getting slow.

AND THE COMMON-POOL TRACE ON A 2-CORE CONTAINER:

    availableProcessors() = 2  →  commonPool parallelism = 1
    supplyAsync(() -> jdbc.query(...))          ← occupies THE thread for 40 ms
    someList.parallelStream().map(...)          ← waits
    another library's executor-less future      ← waits
    ---------------------------------------------------------------------------------
    ONE BLOCKING CALL SERIALISED THE ENTIRE JVM'S ASYNC WORK. Nothing threw, nothing logged, and the
    fix is one extra argument.

WHAT PRODUCED WHAT:
    INDEPENDENT SUBMISSION   produced 375 ms → 155 ms. Sum became maximum.
    thenCompose              produced arrangement 3 — correct, and sequential by definition.
    THE DEFAULT EXECUTOR     produced the last table, and it is one argument away from never
                             happening.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Fan-out turns a SUM of latencies into a MAXIMUM. That is the whole performance story.
    Default executor: `ForkJoinPool.commonPool()`, parallelism `availableProcessors() - 1`, daemon
    threads, shared JVM-wide, sized for CPU-bound work.
    Non-async callbacks run on the completing thread — or the calling thread if already complete.
    Exceptions are wrapped: `get()` → checked `ExecutionException`; `join()` → unchecked
    `CompletionException`. Handlers need `getCause()`.
    `cancel(true)` does NOT interrupt; the work runs to completion.
    `orTimeout` / `completeOnTimeout`: Java 9+. There was no timeout before that.
    `allOf` returns `Void`; `anyOf` returns `Object` and completes on the first result OR failure.

THE #1 MISTAKE: not passing an executor. The common pool is `cores - 1`, shared by the whole JVM, and
one blocking call on a small container serialises everything.

THE #2 MISTAKE: `thenApply` where `thenCompose` belongs. A future inside a future.

THE #3 MISTAKE: chaining independent calls with `thenCompose`. Correct, sequential, and slower than the
blocking version it replaced.

THE #4 MISTAKE: not knowing which thread a non-async callback runs on. It can hijack an I/O thread.

THE #5 MISTAKE: `whenComplete` used as a recovery. It observes and changes nothing.

THE #6 MISTAKE: catching your own exception type without unwrapping `CompletionException`.

THE #7 MISTAKE: expecting `cancel` to stop work. It discards the result only.

THE #8 MISTAKE: `allOf` and then looking for results in the returned future. It is `Void`.

THE #9 MISTAKE: no `exceptionally`/`handle`, and nobody joins the chain. Silent failure, exactly like an
ignored `Future` from `submit`.

THE #10 MISTAKE: no timeout. A future that never completes is a hang with extra machinery.

THE #11 MISTAKE: losing MDC, security or transaction context across stages. It does not follow the
value to another thread.

THE #12 MISTAKE: unbounded fan-out over a large collection. One task per element, all submitted at once.

ONE-SENTENCE TAKEAWAY: `CompletableFuture` replaces "get the value" with "describe the pipeline" — a
grid of combinators where `thenApply` is map, `thenCompose` is flatMap, `thenCombine` is zip, and a
failure flows down the chain skipping every stage until something handles it, so fan-out turns a SUM of
latencies into a MAXIMUM; the operational fact that matters most is that the default executor is the
common ForkJoinPool sized to `cores - 1` and shared by the entire JVM, so every `*Async` call needs an
explicit executor, and the two behaviours that surprise people are that non-async callbacks run on
whichever thread completed the previous stage and that `cancel(true)` never interrupts anything — while
on Java 21 sequential I/O belongs in a virtual thread with plain blocking calls, and fan-out
increasingly belongs in `StructuredTaskScope`, which gives the bounded lifetimes and real cancellation
this API never had.""",
]


DEEP["Comparable vs Comparator — and the contract that silently breaks TreeMap"] = [
"""1. THE GOAL IN PLAIN ENGLISH — one built-in order, or as many as you like

`Comparable` is a class saying "here is my NATURAL order". `String` sorts alphabetically, `Integer`
numerically, `LocalDate` chronologically. You implement `compareTo(T other)` inside the class, and you
get exactly ONE, because a type has at most one obvious order.

`Comparator` is a SEPARATE OBJECT that knows how to order two things. You can write as many as you like,
for types you do not own, for orders that are not natural, and choose one per call.

    THE RULE OF THUMB: IF THERE IS AN OBVIOUS DEFAULT, MAKE THE CLASS `Comparable`. FOR EVERYTHING ELSE,
    PASS A `Comparator`.

    An `Employee` has no natural order — by name? salary? hire date? — so it should almost certainly
    NOT be `Comparable`, and the callers should say what they want. A `Money` or a `Version` does have
    one.

BOTH RETURN AN INT, AND THE CONVENTION IS THE SAME:

    NEGATIVE   this comes BEFORE the other
    ZERO       they tie
    POSITIVE   this comes AFTER

    The magnitude means nothing. Only the sign is read. WHICH IS WHY THE MOST COMMON BUG IN THIS TOPIC
    IS WRITING `return a.value - b.value`: it gives the right sign almost always, and overflows into
    the WRONG SIGN when the values are far apart. See section 4.

AND THE REASON THIS ENTRY EXISTS AT ALL: getting the ORDER slightly wrong is a cosmetic bug, but
violating the CONTRACT is not. `TreeMap`, `TreeSet` and `PriorityQueue` use `compareTo` INSTEAD OF
`equals` to decide whether two things are the same. So a comparator that disagrees with `equals`
silently changes what "contains" means, and `Arrays.sort` can throw an error most people have never
seen: "Comparison method violates its general contract!"

THE EVERYDAY VERSION: a natural order is the alphabetical filing you already use. A comparator is a
one-off instruction — "today, sort these by date received". You can have many instructions and only one
filing system.

TERMS AS THEY APPEAR:
- NATURAL ORDERING: the order given by `compareTo`. Used whenever no comparator is supplied.
- TOTAL ORDER: every pair is comparable, consistently, with no cycles.
- STABLE SORT: equal elements keep their original relative order.""",

"""2. THE INTUITION — the contract, and the clause that is "only recommended"

THE CONTRACT HAS THREE HARD RULES AND ONE STRONG SUGGESTION, and the suggestion is where all the damage
happens.

    1. ANTISYMMETRY.  `sgn(x.compareTo(y)) == -sgn(y.compareTo(x))` for all x, y. If x comes before y,
       y must come after x. And if one throws, the other must throw.
    2. TRANSITIVITY.  If x > y and y > z then x > z.
    3. CONSISTENCY OF TIES. If `x.compareTo(y) == 0`, then x and y must compare the same way against
       every other z.

    4. STRONGLY RECOMMENDED, NOT REQUIRED: `(x.compareTo(y) == 0)` should equal `x.equals(y)`.

    THE JAVADOC EVEN SPELLS OUT THE CONSEQUENCE OF IGNORING RULE 4: "a class whose natural ordering is
    inconsistent with equals... will behave STRANGELY when used with sorted sets and sorted maps",
    because those "use the natural ordering INSTEAD OF the equals method".

WHY THAT MATTERS SO MUCH — THE CANONICAL EXAMPLE IS `BigDecimal`:

    new BigDecimal("1.0").equals(new BigDecimal("1.00"))       → FALSE  (scale differs)
    new BigDecimal("1.0").compareTo(new BigDecimal("1.00"))    → 0      (same value)

    So put both into a `HashSet` and you have TWO elements — `HashSet` uses `equals`.
    Put both into a `TreeSet` and you have ONE — `TreeSet` uses `compareTo`.

    SAME TWO OBJECTS. SAME `Set` INTERFACE. DIFFERENT SIZE. That is not a bug in either class; it is
    what "inconsistent with equals" means, and `BigDecimal` documents it. It is also why the answer to
    "how do I compare BigDecimals" is always `compareTo(...) == 0`, never `equals`.

THE SECOND CONSEQUENCE, AND IT IS THE ONE THAT PRODUCES AN ERROR NOBODY RECOGNISES:

    `Arrays.sort` and `Collections.sort` on objects use TIMSORT, which finds already-ordered RUNS in
    the data and merges them, relying on invariants about their lengths. If your comparator is
    inconsistent — antisymmetry or transitivity violated — those invariants break, and rather than
    silently corrupting the array TimSort throws:

        java.lang.IllegalArgumentException: Comparison method violates its general contract!

    IT IS NOT ALWAYS THROWN. TimSort only notices when the merge pattern happens to expose the
    inconsistency, which depends on the data. SO THE SAME BROKEN COMPARATOR WORKS FOR MONTHS ON SMALL
    INPUTS AND THROWS ON THE DAY THE LIST GETS LONG — and the message points at the sort, not at the
    comparator you wrote three years ago.

THE THIRD, quieter consequence: a `TreeMap` built with an inconsistent comparator can LOSE ENTRIES —
`put` finds an existing "equal" key and replaces it — and `get` can fail to find a key that is
demonstrably in the map. No exception. Just missing data.""",

"""3. THE MECHANISM — where each is used, and the combinators that replaced hand-written comparators

WHO USES WHICH:

    Collections.sort(list) / list.sort(null)   NATURAL ordering — requires `Comparable`.
    list.sort(cmp) / Arrays.sort(a, cmp)       the comparator.
    new TreeMap<>() / new TreeSet<>()          natural ordering.
    new TreeMap<>(cmp)                         the comparator — AND IT DEFINES EQUALITY FOR THAT MAP.
    new PriorityQueue<>(cmp)                   the comparator, for the heap order.
    stream.sorted() / sorted(cmp)              either.
    stream.max(cmp) / min(cmp)                 comparator required.
    Collections.binarySearch                   MUST use the same ordering the list is sorted by, or the
                                               result is undefined — and it will not tell you.

THE COMBINATORS (Java 8) — these replaced essentially all hand-written comparators:

    Comparator.comparing(Person::lastName)
              .thenComparing(Person::firstName)
              .thenComparingInt(Person::age)
              .reversed();

    `comparing(keyExtractor)`          order by an extracted `Comparable` key
    `comparingInt/Long/Double`         the same WITHOUT BOXING — use these for primitives
    `thenComparing(...)`               tie-breaker, chainable
    `reversed()`                       reverse — SEE THE TRAP BELOW
    `nullsFirst(cmp)` / `nullsLast`    wrap a comparator to tolerate nulls
    `naturalOrder()` / `reverseOrder()`

    THE `reversed()` TRAP: it reverses the ENTIRE COMPARATOR BUILT SO FAR, not the last clause.
    `comparing(A).thenComparing(B).reversed()` reverses BOTH A and B. To reverse only B, write
    `comparing(A).thenComparing(B, reverseOrder())`. This produces subtly wrong orderings that pass
    review because the code reads like English and does not mean what the English says.

SORTING ALGORITHMS, since the choice depends on the type:

    OBJECTS: TimSort — a stable, adaptive merge sort. O(n log n) worst case, O(n) on already-sorted
    input, and it needs O(n) auxiliary space. STABILITY IS GUARANTEED, which is what makes multi-pass
    sorting work: sort by name, then sort by department, and within each department the names are still
    in order.
    PRIMITIVES: dual-pivot quicksort. Faster and in-place, NOT stable — which does not matter, because
    two equal `int`s are indistinguishable.

    THAT ASYMMETRY IS DELIBERATE AND IS WORTH KNOWING: `Arrays.sort(int[])` and `Arrays.sort(Object[])`
    are different algorithms with different guarantees, chosen for exactly this reason.

TIES AND STABILITY: `compareTo` returning 0 means "these tie", and a stable sort leaves tied elements
in their input order. If your sort output is non-deterministic between runs, you almost certainly have
ties plus an unstable source order, and the fix is a tie-breaking `thenComparing` on something unique.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `return a.value - b.value`. It OVERFLOWS. With `a.value = Integer.MIN_VALUE` and
`b.value = 1`, the subtraction wraps to a positive number and says MIN_VALUE is GREATER than 1. The
comparator is now non-antisymmetric, and everything downstream is undefined. USE `Integer.compare(a, b)`.

CASE 2 — "Comparison method violates its general contract!" from `Arrays.sort`. TimSort detected an
inconsistent comparator during a merge. It is data-dependent, so it appears when the list grows, long
after the comparator was written.

CASE 3 — A COMPARATOR INCONSISTENT WITH `equals` IN A `TreeSet`. Elements silently vanish, because
`add` finds an "equal" one already present. `HashSet` on the same data has a different size.

CASE 4 — `BigDecimal` IN A `TreeSet` OR AS A `TreeMap` KEY. "1.0" and "1.00" collapse into one entry.
Documented, deliberate, and surprising every time.

CASE 5 — `compareTo` THAT RETURNS 0 FOR DIFFERENT OBJECTS in a `TreeMap`. `put` REPLACES rather than
adds. Data loss with no error.

CASE 6 — MUTATING AN OBJECT WHILE IT IS IN A `TreeSet` OR `PriorityQueue`. Its position is now wrong; it
becomes unfindable and unremovable. Same failure mode as mutating a `HashMap` key.

CASE 7 — `reversed()` REVERSING THE WHOLE CHAIN. `comparing(A).thenComparing(B).reversed()` reverses A
too. Use `thenComparing(B, reverseOrder())` to reverse one clause.

CASE 8 — NULLS. `compareTo` should throw `NullPointerException` on a null argument, per the contract.
For fields that may be null, wrap with `Comparator.nullsFirst(...)` — a naive `a.getName().compareTo(...)`
throws on the first null row.

CASE 9 — `Comparator.comparing` WITH A BOXING KEY EXTRACTOR. `comparing(Person::getAge)` boxes every
age. `comparingInt` does not, and on a large sort the difference is real.

CASE 10 — `binarySearch` WITH A DIFFERENT ORDERING THAN THE SORT USED. Undefined result, no error, and
it usually returns a plausible-looking wrong index.

CASE 11 — A `PriorityQueue`'s ITERATOR IS NOT SORTED. Only `peek`/`poll` respect the order; iteration
walks the heap array. `toString` on a `PriorityQueue` looks wrong and is not.

CASE 12 — INHERITANCE AND `compareTo`. Extending a `Comparable` class and adding a field breaks
antisymmetry between the subclass and superclass instances, for exactly the same reason it breaks
`equals`. Composition instead.

CASE 13 — RELYING ON SORT STABILITY FOR PRIMITIVES. `Arrays.sort(int[])` is dual-pivot quicksort and
unstable — harmless for primitives, but the same expectation applied to a parallel array is not.""",

"""5. THE ALTERNATIVES — how to express an ordering well

USE THE COMBINATORS, NOT A HAND-WRITTEN `compare`. `Comparator.comparing(...).thenComparing(...)` is
shorter, correct by construction on the overflow issue, and reads as the specification. A hand-written
multi-field `compare` with nested if-blocks is where sign errors and missing tie-breaks live.

USE `comparingInt` / `comparingLong` / `comparingDouble` for primitive keys — same clarity, no boxing.

`Integer.compare` / `Long.compare` / `Double.compare` inside any hand-written comparator. Never
subtraction. `Double.compare` additionally handles `NaN` and `-0.0` correctly, which `<` and `>` do
not — a comparator built from `<` on doubles violates its contract whenever a NaN appears.

MAKE THE ORDERING CONSISTENT WITH `equals` UNLESS YOU HAVE A REASON, and DOCUMENT it when it is not.
`BigDecimal` documents it; most classes that break it did so by accident.

FOR A CLASS WITH NO OBVIOUS ORDER, DO NOT IMPLEMENT `Comparable`. Provide named comparators as static
fields instead — `Employee.BY_SALARY`, `Employee.BY_HIRE_DATE` — so the call site states which order it
wants and nobody depends on an arbitrary default.

`record` + `Comparator.comparing` covers most value types: the record gives you `equals` and
`hashCode`, and a static comparator gives you the order, keeping the two definitions visible next to
each other.

FOR SORTED COLLECTIONS:
    `TreeMap` / `TreeSet` — O(log n), sorted, and EQUALITY IS DEFINED BY THE COMPARATOR.
    `PriorityQueue` — O(log n) insert and extract-min, and NOT sorted when iterated.
    `ConcurrentSkipListMap` — the concurrent sorted map.
    A SORTED `ArrayList` + `binarySearch` — often faster than a `TreeMap` for read-mostly data, because
    of locality.

`Collator` FOR HUMAN-FACING TEXT. `String.compareTo` orders by UTF-16 code unit, so "Z" sorts before
"a", and accented characters land in positions no user expects. Anything shown to a person in a
specific locale wants a `Collator`.

FOR SORTING BY A COMPUTED KEY THAT IS EXPENSIVE, precompute it. A comparator is called O(n log n) times,
so an expensive key extractor is evaluated far more often than there are elements — decorate, sort,
undecorate.

WHAT TO SAY: "`Comparable` only when there is a genuinely obvious natural order; otherwise named
static comparators so the call site states the intent. Always the `comparing`/`thenComparing`
combinators with the primitive variants, never subtraction — and I would keep the ordering consistent
with `equals`, because `TreeSet` and `TreeMap` use `compareTo` instead of `equals` to decide what is a
duplicate."

""",

"""6. HOW TO GET ORDERING RIGHT — numbered steps

STEP 1 — ASK WHETHER THERE IS A GENUINELY NATURAL ORDER. If reasonable people would disagree, do not
implement `Comparable`.

STEP 2 — USE THE COMBINATORS. `Comparator.comparing(...).thenComparing(...)`, not a hand-written
`compare`.

STEP 3 — NEVER SUBTRACT. `Integer.compare`, `Long.compare`, `Double.compare`. Subtraction overflows and
breaks antisymmetry at the extremes.

STEP 4 — USE `comparingInt`/`comparingLong`/`comparingDouble` FOR PRIMITIVE KEYS. Same code, no boxing.

STEP 5 — MAKE IT CONSISTENT WITH `equals`, OR DOCUMENT LOUDLY THAT IT IS NOT. Sorted collections use
`compareTo` to decide duplicates.

STEP 6 — ALWAYS ADD A TIE-BREAKER ON SOMETHING UNIQUE if you need deterministic output. Ties plus an
unstable input order produce results that differ between runs.

STEP 7 — WATCH `reversed()`. It reverses the whole chain; `thenComparing(key, reverseOrder())` reverses
one clause.

STEP 8 — HANDLE NULLS EXPLICITLY with `nullsFirst`/`nullsLast` rather than discovering them in
production.

STEP 9 — NEVER MUTATE AN OBJECT THAT IS INSIDE A `TreeSet`, `TreeMap` KEY SET, OR `PriorityQueue`.
Remove, mutate, re-add.

STEP 10 — USE THE SAME ORDERING FOR `sort` AND `binarySearch`. Different orderings give an undefined
result with no error.

STEP 11 — IF THE KEY IS EXPENSIVE TO COMPUTE, PRECOMPUTE IT. The comparator runs O(n log n) times.

STEP 12 — WHEN YOU SEE "Comparison method violates its general contract!", DO NOT SUPPRESS IT WITH
`-Djava.util.Arrays.useLegacyMergeSort=true`. That flag hides a genuinely broken comparator; find the
inconsistency instead.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Comparable is a class saying "here is my natural order" — you implement compareTo inside the class and
you get exactly one, because a type has at most one obvious order. Comparator is a separate object, so
you can write as many as you like, for types you don't own and for orders that aren't natural.

My rule of thumb: if reasonable people would disagree about the default, don't implement Comparable. An
Employee has no natural order — name? salary? hire date? — so I'd provide named static comparators and
let the call site say what it wants. Money or a Version does have one.

Both return an int, and only the SIGN is read; the magnitude means nothing. Which is why the most
common bug here is writing `return a.value - b.value`. That gives the right sign almost always and
OVERFLOWS into the wrong sign when the values are far apart — MIN_VALUE minus 1 wraps positive, so your
comparator claims MIN_VALUE is the larger. Use Integer.compare.

But the reason this topic actually matters isn't ordering, it's the CONTRACT. Three hard rules —
antisymmetry, transitivity, consistent ties — and then a fourth that's only "strongly recommended":
compareTo returning zero should agree with equals. That fourth one is where all the damage is, because
TreeMap, TreeSet and PriorityQueue use compareTo INSTEAD of equals to decide whether two things are the
same.

The canonical example is BigDecimal. "1.0".equals("1.00") is false because the scale differs, but
compareTo returns zero because the value is the same. So put both in a HashSet and you have two
elements; put both in a TreeSet and you have one. Same two objects, same Set interface, different size.
That's not a bug in either class — it's what "inconsistent with equals" means, and it's why the answer
to "how do I compare BigDecimals" is always compareTo == 0.

The second consequence is an error most people have never seen: "Comparison method violates its general
contract!" from Arrays.sort. Sorting objects uses TimSort, which finds already-ordered runs and merges
them relying on invariants about their lengths. An inconsistent comparator breaks those invariants, and
rather than silently corrupting the array, TimSort throws. And it's DATA-DEPENDENT — it only notices
when the merge pattern happens to expose the inconsistency. So the same broken comparator works for
months on small inputs and throws the day the list gets long, with a message pointing at the sort rather
than at the comparator someone wrote three years ago.

There's a quieter version too: a TreeMap with an inconsistent comparator loses entries, because put
finds an "equal" key and replaces it. No exception. Just missing data.

Practically I'd use the Java 8 combinators for everything — comparing, thenComparing, with the
comparingInt variants so primitive keys don't box. One trap there: reversed() reverses the ENTIRE chain
built so far, not the last clause, so comparing(A).thenComparing(B).reversed() reverses A too. To
reverse one clause it's thenComparing(B, reverseOrder()).'""",

"""8. THE CODE, LINE BY LINE

    // ── THE OVERFLOW BUG ────────────────────────────────────────────────
    Comparator<Item> byValue = (a, b) -> a.value() - b.value();
    //                                   ^^^^^^^^^^^^^^^^^^^^^ right sign ALMOST
    //   always. With a.value = Integer.MIN_VALUE and b.value = 1, the subtraction
    //   OVERFLOWS to a positive number → "MIN_VALUE is greater than 1". Antisymmetry
    //   is now violated and everything downstream is undefined.
    Comparator<Item> byValue = Comparator.comparingInt(Item::value);
    //                                    ^^^^^^^^^^^^ correct, and no boxing

    // ── THE CONTRACT, AND THE CLAUSE THAT IS ONLY "RECOMMENDED" ─────────
    // 1. sgn(x.compareTo(y)) == -sgn(y.compareTo(x))          REQUIRED
    // 2. x>y && y>z  ⟹  x>z                                   REQUIRED
    // 3. x.compareTo(y)==0 ⟹ x and y compare alike vs any z   REQUIRED
    // 4. (x.compareTo(y)==0) == x.equals(y)          STRONGLY RECOMMENDED ← the one
    //                                                that breaks TreeMap when ignored

    // ── THE CANONICAL EXAMPLE ───────────────────────────────────────────
    var a = new BigDecimal("1.0");
    var b = new BigDecimal("1.00");
    a.equals(b);        // FALSE — the SCALE differs
    a.compareTo(b);     // 0     — the VALUE is the same
    new HashSet<>(List.of(a, b)).size();   // 2  ← HashSet uses equals
    new TreeSet<>(List.of(a, b)).size();   // 1  ← TreeSet uses COMPARETO
    // SAME OBJECTS. SAME Set INTERFACE. DIFFERENT SIZE. Documented, and deliberate.

    // ── THE ERROR NOBODY RECOGNISES ─────────────────────────────────────
    Comparator<Task> broken = (x, y) -> x.priority() > y.priority() ? 1 : -1;
    //                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ NEVER
    //   returns 0, so equal priorities report BOTH "x before y" AND "y before x".
    //   Antisymmetry violated.
    Collections.sort(bigList, broken);
    // → java.lang.IllegalArgumentException: Comparison method violates its
    //   general contract!
    //   TimSort found the inconsistency while merging runs and refused to continue.
    //   IT IS DATA-DEPENDENT: works on 20 elements for years, throws on 2,000.

    // ── THE COMBINATORS, AND THE reversed() TRAP ────────────────────────
    Comparator.comparing(Person::lastName)
              .thenComparing(Person::firstName)
              .thenComparingInt(Person::age)      // ← Int variant: no boxing
              .reversed();
    //         ^^^^^^^^^^ REVERSES THE WHOLE CHAIN — lastName AND firstName AND age.
    //         Not just the last clause. The code reads like English and does not
    //         mean what the English says.
    Comparator.comparing(Person::lastName)
              .thenComparing(Person::age, Comparator.reverseOrder());
    //                                    ^^^^^^^^^^^^^^^^^^^^^^^^ reverses ONE clause

    // ── NULLS AND NaN ───────────────────────────────────────────────────
    comparing(Person::nickname)                        // NPE on the first null
    comparing(Person::nickname, nullsFirst(naturalOrder()))   // tolerant
    (a, b) -> a.score() < b.score() ? -1 : 1           // ✗ NaN breaks the contract
    comparingDouble(Item::score)                       // ✓ Double.compare handles
    //                                                    NaN and -0.0 correctly

    // ── TWO SORTS, TWO ALGORITHMS, TWO GUARANTEES ───────────────────────
    Arrays.sort(objectArray, cmp);   // TIMSORT: stable, O(n log n), O(n) space,
    //                                  O(n) on already-sorted input
    Arrays.sort(intArray);           // DUAL-PIVOT QUICKSORT: in place, NOT stable —
    //                                  which is fine, two equal ints are the same int
    // Stability is what makes multi-pass sorting work: sort by name, then by
    // department, and within each department the names are STILL in order.

    // ── AND ONE THAT LOOKS BROKEN AND IS NOT ────────────────────────────
    var pq = new PriorityQueue<>(List.of(5, 1, 3));
    System.out.println(pq);          // [1, 5, 3] — NOT sorted
    // Only peek() and poll() respect the order. Iteration walks the heap ARRAY.""",

"""9. THE TRACE — one inconsistent comparator, three victims

THE COMPARATOR: `(x, y) -> x.priority() > y.priority() ? 1 : -1`. It never returns 0.

    THE VIOLATION, made explicit:
    ---------------------------------------------------------------------------------
    two tasks A and B, both priority 5
    A.compareTo(B) → not greater → returns -1   ("A before B")
    B.compareTo(A) → not greater → returns -1   ("B before A")
    sgn(-1) == -sgn(-1)?   -1 == +1?   NO.      ← ANTISYMMETRY VIOLATED
    ---------------------------------------------------------------------------------
    It says each comes before the other. Everything built on that is now undefined.

    VICTIM 1 — `Collections.sort` ON A SHORT LIST
    input size   what happens
    ---------------------------------------------------------------------------------
    5 elements   sorted "successfully". TimSort used one run; no merge exposed the
                 inconsistency. The output order among ties is arbitrary but nothing
                 complains.
    2,000        multiple runs, merged. The merge invariant about run lengths fails.
                 → IllegalArgumentException: Comparison method violates its general
                   contract!
    ---------------------------------------------------------------------------------
    THE SAME COMPARATOR, THE SAME CODE. It passed every test and every small dataset for as long as the
    inputs stayed short. The exception's message names the sort; the defect is in a lambda somewhere
    else entirely.

    VICTIM 2 — `TreeSet`
    operation                                     result
    ---------------------------------------------------------------------------------
    add(A) — priority 5                            size 1
    add(B) — priority 5, a DIFFERENT task          the tree navigates by the
                                                   comparator, which never says 0, so
                                                   B is placed somewhere — but a
                                                   later contains(B) may walk a
                                                   different path and MISS IT
    contains(B)                                    false, unpredictably
    ---------------------------------------------------------------------------------
    NO EXCEPTION. The set contains an element it cannot find. A search tree is only correct if the
    comparator defines a consistent order; break that and the invariant that makes the search work is
    gone.

    VICTIM 3 — `PriorityQueue`
    ---------------------------------------------------------------------------------
    The heap property — "every parent orders before its children" — is maintained by sift-up and
    sift-down, both of which trust the comparator. With an inconsistent one, poll() can return elements
    OUT OF ORDER, quietly, forever. No error is possible, because the queue has no way to detect that
    the ordering it was given is not an ordering.

NOW THE OVERFLOW VERSION, traced with real values:

    a.value = Integer.MIN_VALUE (-2,147,483,648),  b.value = 1
    ---------------------------------------------------------------------------------
    mathematically      -2147483648 - 1 = -2147483649       → negative, "a first"
    in 32-bit int       wraps to        = +2147483647       → POSITIVE, "b first"
    ---------------------------------------------------------------------------------
    Integer.compare(a, b) → -1, correctly.
    THE SUBTRACTION IS RIGHT FOR EVERY VALUE YOU WILL EVER TEST WITH and wrong at the extremes — so it
    is a latent contract violation that arrives with the first sentinel value, the first negative id, or
    the first timestamp difference that exceeds two billion.

AND THE `reversed()` TRACE:

    comparator                                          Smith,Ann  Smith,Bob  Adams,Zoe
    ---------------------------------------------------------------------------------
    comparing(last).thenComparing(first)                 2          3          1
    comparing(last).thenComparing(first).reversed()      2          1          3
                                                         ^ Bob before Ann — BOTH clauses
                                                           reversed
    comparing(last).thenComparing(first, reverseOrder()) 3          2          1
                                                         ^ Adams still first, Bob before
                                                           Ann within Smith
    ---------------------------------------------------------------------------------
    ROWS 2 AND 3 ARE DIFFERENT ORDERINGS, and row 2 is what almost everyone writes when they mean row 3.

WHAT PRODUCED WHAT:
    NEVER RETURNING 0        produced the antisymmetry violation, and therefore all three victims.
    TIMSORT'S MERGE INVARIANT produced the only LOUD failure — and only on large enough input.
    A TREE'S SEARCH INVARIANT produced the silent one.
    32-BIT WRAPAROUND        produced a comparator that is correct on every value you would think to
                             test.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    A comparator is invoked O(n log n) times per sort — so an expensive key extractor runs far more
    often than there are elements. Decorate–sort–undecorate when the key is costly.
    `Arrays.sort(Object[])`: TimSort. Stable, O(n log n) worst case, O(n) on sorted input, O(n) space.
    `Arrays.sort(int[])`: dual-pivot quicksort. In place, NOT stable.
    `TreeMap` / `TreeSet`: O(log n), and EQUALITY IS THE COMPARATOR'S ZERO, not `equals`.
    `PriorityQueue`: O(log n) offer/poll, O(1) peek, and iteration is NOT ordered.
    `comparing` boxes; `comparingInt`/`Long`/`Double` do not.

THE #1 MISTAKE: `a - b` as a comparator. Overflows at the extremes and breaks antisymmetry.

THE #2 MISTAKE: an ordering inconsistent with `equals`, undocumented. `TreeSet` and `TreeMap` use
`compareTo` to decide duplicates, so elements silently vanish.

THE #3 MISTAKE: a comparator that never returns 0. Antisymmetry violated; TimSort throws, but only once
the input is large enough to merge.

THE #4 MISTAKE: suppressing "Comparison method violates its general contract!" with the legacy-merge-sort
flag. That hides a genuinely broken comparator.

THE #5 MISTAKE: `reversed()` believing it reverses only the last clause. It reverses the whole chain.

THE #6 MISTAKE: `comparing` with a primitive getter. Boxes every element; `comparingInt` does not.

THE #7 MISTAKE: `<` and `>` on doubles inside a comparator. `NaN` makes all comparisons false, so the
contract breaks. `Double.compare`.

THE #8 MISTAKE: mutating an object inside a `TreeSet` or `PriorityQueue`. Its position is stale and it
becomes unfindable.

THE #9 MISTAKE: `binarySearch` with an ordering different from the sort's. Undefined, silent, plausible.

THE #10 MISTAKE: implementing `Comparable` for a class with no natural order, forcing an arbitrary
default on every caller.

THE #11 MISTAKE: expecting a `PriorityQueue` to iterate in order. Only `peek` and `poll` do.

THE #12 MISTAKE: `String.compareTo` for human-facing sorting. It orders by UTF-16 code unit, so "Z"
precedes "a". Use a `Collator`.

ONE-SENTENCE TAKEAWAY: `Comparable` gives a class its single natural order and `Comparator` gives
callers as many alternative orders as they need, both returning only a SIGN — which is why `a - b`
is a latent bug that overflows into the wrong sign at the extremes — and the part that actually causes
outages is the contract's "strongly recommended" clause that a zero result should agree with `equals`,
because `TreeSet`, `TreeMap` and `PriorityQueue` use `compareTo` INSTEAD OF `equals` to decide what is a
duplicate (which is why `BigDecimal("1.0")` and `("1.00")` are two elements in a `HashSet` and one in a
`TreeSet`), and because an inconsistent comparator makes TimSort throw "Comparison method violates its
general contract!" only once the input is large enough to expose it — so build orderings from
`comparing`/`thenComparing` with the primitive variants, never subtraction, and remember `reversed()`
reverses the entire chain.""",
]


DEEP["Primitives vs objects — the split that explains half of Java"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two kinds of thing that look the same in source code

Java has EIGHT types that are not objects: `boolean`, `byte`, `short`, `char`, `int`, `long`, `float`,
`double`. Everything else — every String, every List, every class you write — is an object.

    A PRIMITIVE IS JUST A VALUE. `int x = 5` puts the number 5 somewhere. Four bytes. It has no
    methods, no identity, and it CANNOT BE null, because there is no "no number" bit pattern reserved
    for that.

    AN OBJECT IS A VALUE PLUS AN IDENTITY. `Integer x = 5` allocates a small object on the heap holding
    the number 5, plus a header, and `x` holds a REFERENCE to it. Two objects can contain the same
    number and still be different objects. And a reference CAN be null, because null is a valid
    reference.

    THAT ONE DIFFERENCE — IDENTITY — IS WHY `==` MEANS SOMETHING DIFFERENT FOR EACH. On primitives it
    compares values, and always does what you want. On objects it compares identities, and almost never
    does.

WHY THE SPLIT EXISTS AT ALL: in 1995, making every integer a heap object would have been catastrophically
slow. Primitives map directly onto what the CPU and the bytecode set already do. The cost of that
decision is that primitives cannot participate in the object world — they cannot go into collections,
cannot be generic type arguments, cannot be null — and Java has been patching around that ever since:
wrapper classes in 1.0, AUTOBOXING in Java 5, primitive streams in Java 8, and Project Valhalla still
working on it thirty years later.

    SO THIS IS NOT TRIVIA. THE PRIMITIVE/OBJECT SPLIT IS THE ROOT CAUSE OF: `Integer` caching and the
    `128 != 128` trap, `List<Integer>` instead of `List<int>`, NullPointerExceptions on arithmetic,
    `IntStream` existing separately from `Stream`, and a five-fold memory difference on numeric data.

THE EVERYDAY VERSION: a number written on a page versus a number written on a numbered card in a filing
cabinet. Two pages can both say "42" and the statement "these are the same 42" is meaningless — there
is only the value. Two cards can both say 42 and be genuinely different cards, and a card slot can be
empty, which a written number cannot be.

TERMS AS THEY APPEAR:
- WRAPPER: the object version of a primitive. `Integer`, `Long`, `Double`, `Boolean`, `Character`.
- BOXING: converting a primitive to its wrapper. UNBOXING: the reverse.
- AUTOBOXING: the compiler inserting those conversions for you. Java 5 onwards.""",

"""2. THE INTUITION — autoboxing made them look interchangeable, and they are not

BEFORE JAVA 5 YOU WROTE THE CONVERSIONS BY HAND: `list.add(new Integer(x))` and `int y =
i.intValue()`. Autoboxing removed that noise by having the compiler insert `Integer.valueOf(x)` and
`.intValue()` automatically.

    IT MADE THE CODE READ AS IF PRIMITIVES AND OBJECTS WERE THE SAME THING. THEY ARE NOT, AND THREE
    CONSEQUENCES LEAK THROUGH:

    CONSEQUENCE 1 — `==` SILENTLY CHANGES MEANING. `Integer a = 127, b = 127; a == b` is TRUE.
    `Integer a = 128, b = 128; a == b` is FALSE. Because `Integer.valueOf` returns a CACHED object for
    −128..127 and a new one outside that range. The comparison went from value equality to reference
    equality without a single character changing.

    CONSEQUENCE 2 — UNBOXING CAN THROW `NullPointerException` ON A LINE WITH NO METHOD CALL.
    `int count = map.get("missing");` — `get` returns null, the compiler inserted `.intValue()`, and
    you get an NPE pointing at an assignment. The same happens with `if (booleanWrapper)`, with
    arithmetic on a nullable `Integer`, and — most subtly — inside a ternary whose OTHER branch is a
    primitive, where the unboxing happens even though you are assigning the result to a wrapper.

    CONSEQUENCE 3 — THE COST IS INVISIBLE. `Long sum = 0L; for (...) sum += x;` allocates a NEW Long
    OBJECT ON EVERY ITERATION, because `sum` is a wrapper and wrappers are immutable. One character
    (`Long` versus `long`) changes an allocation-free loop into millions of allocations, and the code
    looks identical.

THE MEMORY PICTURE, which is the argument that persuades people:

    int[] OF ONE MILLION            4 MB. One contiguous block. 16 values per cache line.
    List<Integer> OF ONE MILLION    a 4 MB array of REFERENCES, plus one million Integer objects at
                                    16 bytes each (12-byte header + 4-byte value, 8-byte aligned)
                                    = ~20 MB, scattered across the heap.

    ROUGHLY FIVE TIMES THE MEMORY — and worse, five times the memory in the wrong SHAPE. Walking the
    `int[]` is a sequential scan the prefetcher runs ahead of. Walking the `List<Integer>` reads a
    reference, then follows it to wherever that object happens to live: A DEPENDENT CACHE MISS PER
    ELEMENT. The Integer cache helps only for small values that happen to repeat.

WHY GENERICS CANNOT HOLD PRIMITIVES: type erasure replaces `T` with `Object`, and `Object` is a
reference. A primitive is not a reference, so it cannot be a type argument. `List<int>` does not
compile, and that single limitation is why `IntStream` exists alongside `Stream<Integer>`, why
`OptionalInt` exists alongside `Optional<Integer>`, and why libraries like fastutil and Eclipse
Collections exist at all.""",

"""3. THE MECHANISM — the eight types, the caches, and what the compiler inserts

THE EIGHT PRIMITIVES:

    type      bits   range / notes                                    wrapper
    ---------------------------------------------------------------------------------
    boolean   —      true/false. Size is unspecified; typically a      Boolean
                     byte in an array, an int on the stack.
    byte      8      −128 to 127. SIGNED — which surprises people      Byte
                     doing binary I/O, where 0xFF reads as −1.
    short     16     −32,768 to 32,767                                 Short
    char      16     0 to 65,535. UNSIGNED. A UTF-16 code unit, NOT    Character
                     a character — emoji need two.
    int       32     ±2.1 billion. The default for integer literals.   Integer
    long      64     ±9.2 quintillion. Needs the `L` suffix.           Long
    float     32     ~7 significant decimal digits                     Float
    double    64     ~15–17 digits. The default for decimal literals.  Double

THE WRAPPER CACHES, and exactly which ones exist:

    Integer, Short, Byte, Long    cached −128 to 127
    Character                     cached 0 to 127
    Boolean                       both values, always cached
    Float, Double                 NEVER CACHED. There is no sensible finite set to cache.

    `Integer.valueOf(x)` returns the cached instance in range and `new Integer(x)` outside it —
    and the upper bound is tunable with `-XX:AutoBoxCacheMax`. THE CACHE EXISTS BECAUSE SMALL INTEGERS
    ARE OVERWHELMINGLY THE COMMON CASE (loop counters, sizes, small ids), and it is required by the
    language specification for −128..127, which is why the `127 == 127` / `128 != 128` behaviour is
    portable rather than a JVM quirk.

WHAT THE COMPILER ACTUALLY INSERTS:

    list.add(5)          →  list.add(Integer.valueOf(5))
    int x = integer      →  int x = integer.intValue()          ← THE NPE LIVES HERE
    Integer a = b + c    →  Integer.valueOf(b.intValue() + c.intValue())
    if (booleanWrapper)  →  if (booleanWrapper.booleanValue())  ← and here

    `new Integer(5)` has been DEPRECATED FOR REMOVAL since Java 9, precisely because it defeats the
    cache and creates identity where none was wanted.

THE TERNARY RULE, WHICH IS THE NASTIEST CORNER OF THE WHOLE TOPIC: if BOTH branches of `?:` are
convertible to numeric types and at least one is a PRIMITIVE, the whole expression undergoes BINARY
NUMERIC PROMOTION — so the selected branch is UNBOXED, whatever you are assigning the result to. So:

    Boolean enabled = flags.containsKey(k) ? flags.get(k) : false;

    throws `NullPointerException` when the stored value is null. The `false` is a primitive `boolean`,
    which forces the expression's type to `boolean`, so `flags.get(k)` must be unboxed to satisfy it —
    EVEN THOUGH THE TARGET VARIABLE IS A `Boolean` AND WOULD HAPPILY HAVE ACCEPTED null. Write
    `Boolean.FALSE` instead of `false` and the same line is fine.

    THE TYPE OF A CONDITIONAL EXPRESSION IS DECIDED BEFORE ANY BRANCH IS CHOSEN, from both operands
    together. That is why reading the taken branch tells you nothing, and it is specified behaviour
    rather than a compiler quirk.

MEMORY LAYOUT OF AN `Integer` on a 64-bit JVM with compressed pointers: 12 bytes of header (mark word +
class pointer) + 4 bytes of `int` value = 16 bytes, and you also pay 4 bytes for the reference pointing
at it. Twenty bytes to store four bytes of information.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `Integer a = 128, b = 128; a == b` IS FALSE, while 127 is TRUE. The cache boundary. Always
`.equals` or `.intValue()` on wrappers.

CASE 2 — NPE FROM UNBOXING, ON A LINE WITH NO METHOD CALL. `int c = map.get(k)` where the key is
absent. The `.intValue()` was inserted by the compiler and does not appear in the source.

CASE 3 — A TERNARY WITH ONE PRIMITIVE BRANCH UNBOXES THE OTHER.
`Boolean b = map.containsKey(k) ? map.get(k) : false;` throws when the stored value is null, even
though `b` is a `Boolean` that would accept it. The primitive `false` forces numeric promotion on the
whole expression. Using `Boolean.FALSE` fixes it.

CASE 4 — `if (nullableBoolean)` THROWS. The compiler inserted `.booleanValue()`.

CASE 5 — BOXING IN A HOT LOOP. `Long sum = 0L; sum += x;` allocates a new `Long` every iteration. One
capital letter separates it from an allocation-free loop.

CASE 6 — `list.remove(1)` ON A `List<Integer>`. `remove(int)` removes by INDEX, `remove(Object)` by
VALUE, and overload resolution silently prefers the primitive. Both compile.

CASE 7 — `byte` IS SIGNED. Reading binary data, `0xFF` becomes `−1`. Mask with `& 0xFF` to get the
unsigned value, and note the result must be held in an `int`.

CASE 8 — `char` IS A UTF-16 CODE UNIT, NOT A CHARACTER. Anything outside the Basic Multilingual Plane —
emoji, many CJK extensions — takes TWO chars, so `s.length()` is not the number of characters and
`charAt` can return half of one. Use `codePoints()`.

CASE 9 — INTEGER OVERFLOW IS SILENT. `Integer.MAX_VALUE + 1` is `Integer.MIN_VALUE`, no exception.
`Math.addExact` throws instead.

CASE 10 — INTEGER DIVISION TRUNCATES. `5 / 2` is 2, and `1 / 2 * 100` is 0, not 50.

CASE 11 — MIXED-TYPE ARITHMETIC PROMOTES SILENTLY. `int * int` stays `int` and can overflow BEFORE the
result is assigned to a `long`. `long total = bigInt * 1000` overflows unless one operand is a `long`.

CASE 12 — `Float`/`Double` ARE NEVER CACHED, so `==` on them is always reference comparison — and
`Double.NaN != Double.NaN` besides.

CASE 13 — A `Map<Integer, ...>` WITH LARGE KEYS. Every key is a heap object with a header; a
`HashMap<Integer, Integer>` of a million entries is tens of megabytes for eight megabytes of data.

CASE 14 — `Integer` AS A LOCK. `synchronized (Integer.valueOf(1))` locks a CACHED, GLOBALLY SHARED
object. Unrelated code can hold it.""",

"""5. THE ALTERNATIVES — how to keep primitives primitive

PRIMITIVE STREAMS — `IntStream`, `LongStream`, `DoubleStream`. `mapToInt`, `sum`, `average`,
`summaryStatistics`, `boxed()` to convert back. USE THESE WHENEVER THE VALUES ARE PRIMITIVES; the
difference against `Stream<Integer>` is not marginal on a large dataset.

`OptionalInt` / `OptionalLong` / `OptionalDouble` — the same idea for optionals.

ARRAYS — `int[]`, `long[]`, `double[]` — whenever the size is known or bounded. Perfect locality, no
headers, no boxing, and `Arrays.sort` on them uses dual-pivot quicksort in place. FOR LARGE NUMERIC
DATA THIS IS THE BIGGEST SINGLE WIN AVAILABLE.

PRIMITIVE COLLECTION LIBRARIES — Eclipse Collections, fastutil, HPPC, Trove. `IntArrayList`,
`Int2ObjectOpenHashMap`. They exist ENTIRELY because generics cannot hold primitives, and on
million-element numeric data they are routinely 3–5× smaller and faster than the JDK equivalents.

`LongAdder` INSTEAD OF `AtomicLong` for contended counters — it stripes across cells rather than
CAS-ing one hot cache line.

`Math.addExact` / `multiplyExact` / `toIntExact` when overflow must be detected rather than wrapped.
`Math.floorDiv` and `floorMod` when you want the mathematical behaviour on negatives rather than
truncation toward zero.

`Objects.requireNonNullElse(x, 0)` or `Optional.ofNullable(x).orElse(0)` at the boundary where a
nullable wrapper becomes a primitive, so the NPE becomes an explicit decision.

`record` FOR SMALL VALUE AGGREGATES — it does not remove the object header, but it makes the value
semantics explicit and gives you `equals`/`hashCode` that compare by content.

PROJECT VALHALLA, which is the real fix and worth mentioning: VALUE CLASSES that have no identity, so
the JVM can FLATTEN them into an array or an object with no header and no indirection — "codes like a
class, works like an int". It would let a `List<Point>` store the points inline rather than as a million
references, and it is the reason the whole primitive/object split may eventually stop mattering. It has
been in development for a decade, which is itself a comment on how deeply the split is embedded.

WHAT TO SAY: "Primitives wherever the value is a number, primitive streams and arrays for bulk numeric
data — the memory difference is about five times and the cache behaviour is worse than the size
suggests — wrappers only when I need null, a collection element, or a generic type argument. And I
never use `==` on wrappers, because the Integer cache makes it work for small values and fail for large
ones."

""",

"""6. HOW TO WORK WITH THE SPLIT — numbered steps

STEP 1 — DEFAULT TO PRIMITIVES. Use a wrapper only when you need null, a collection element, or a
generic type argument.

STEP 2 — NEVER USE `==` ON WRAPPERS. Use `.equals`, or unbox one side explicitly. The cache makes it
work for small values and fail for large ones, which is the worst possible failure pattern.

STEP 3 — CHECK FOR NULL BEFORE UNBOXING. `int c = map.getOrDefault(k, 0)` rather than `map.get(k)`.

STEP 4 — WATCH THE TERNARY. If one branch is a primitive and the other can be null, the null is unboxed
and throws. Make both branches the same reference type, or check first.

STEP 5 — DECLARE ACCUMULATORS AS PRIMITIVES. `long sum`, not `Long sum`. One capital letter separates
zero allocations from millions.

STEP 6 — USE `IntStream`/`LongStream`/`DoubleStream` FOR NUMERIC PIPELINES. `mapToInt(...).sum()`, not
`map(...).reduce(0, Integer::sum)`.

STEP 7 — USE PRIMITIVE ARRAYS FOR LARGE NUMERIC DATA. About five times less memory and a sequential
access pattern instead of pointer chasing.

STEP 8 — MASK `byte` VALUES WITH `& 0xFF` WHEN READING BINARY DATA. It is signed, and the result needs
an `int` to hold it.

STEP 9 — USE `codePoints()` RATHER THAN `charAt` FOR TEXT THAT MAY CONTAIN EMOJI OR CJK EXTENSIONS. A
`char` is a UTF-16 code unit, not a character.

STEP 10 — USE `Math.addExact`/`multiplyExact` WHERE OVERFLOW WOULD BE A CORRECTNESS BUG. Silent
wraparound is the default.

STEP 11 — CAST BEFORE MULTIPLYING WHEN THE RESULT IS A `long`. `(long) a * b`, because `int * int`
overflows before the assignment happens.

STEP 12 — NEVER SYNCHRONIZE ON A WRAPPER. Cached instances are globally shared.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Java has eight types that aren't objects — boolean, byte, short, char, int, long, float, double — and
everything else is. A primitive is just a VALUE: four bytes for an int, no methods, no identity, and it
can't be null because there's no bit pattern reserved for that. An object is a value plus an IDENTITY:
Integer x = 5 allocates a small heap object holding 5 plus a header, and x holds a reference to it.

That one difference — identity — is why == means something different for each. On primitives it
compares values and always does what you want. On objects it compares identities and almost never does.

The split exists because in 1995, making every integer a heap object would have been catastrophically
slow — primitives map directly onto what the CPU already does. The COST is that primitives can't
participate in the object world: no collections, no generic type arguments, no null. And Java's been
patching around that ever since — wrappers in 1.0, autoboxing in Java 5, primitive streams in Java 8,
and Valhalla still working on it thirty years later.

Autoboxing is what makes this dangerous, because it made the two look interchangeable. The compiler
inserts Integer.valueOf and .intValue for you, and three things leak through.

First, == silently changes meaning. Integer a = 127, b = 127 — a == b is TRUE. Change both to 128 and
it's FALSE. Because valueOf returns a CACHED object for minus 128 to 127 and a new one outside that.
The comparison went from value equality to reference equality without a character changing, and it's
required by the spec, so it's portable behaviour rather than a JVM quirk.

Second, unboxing throws NullPointerException on a line with no method call. `int count =
map.get("missing")` — get returns null, the compiler inserted .intValue(), and you get an NPE pointing
at an assignment. The worst version is the ternary: `Boolean b = map.containsKey(k) ? map.get(k) :
false` throws when the stored value is null — even though b is a Boolean that would happily hold null.
The primitive `false` forces the whole expression to type boolean, so the other branch gets unboxed.
Write Boolean.FALSE instead and the identical-looking line is fine. The type of a conditional
expression is decided from BOTH operands before either branch is chosen, which is why reading the
taken branch tells you nothing.

Third, the cost is invisible. `Long sum = 0L; sum += x` in a loop allocates a new Long every iteration,
because wrappers are immutable. One capital letter separates an allocation-free loop from millions of
allocations, and the code looks identical.

The number that persuades people is the memory. A million ints in an int[] is 4 MB, one contiguous
block, sixteen values per cache line. A million in a List<Integer> is a 4 MB array of REFERENCES plus a
million 16-byte objects — about 20 MB, scattered. Five times the memory, and in the wrong SHAPE:
walking the array is a sequential scan the prefetcher runs ahead of, while walking the list is a
dependent cache miss per element.

And the reason generics can't hold primitives is erasure: T becomes Object, Object is a reference, a
primitive isn't. That single limitation is why IntStream exists alongside Stream<Integer>, why
OptionalInt exists, and why fastutil and Eclipse Collections exist at all. Valhalla's value classes are
the real fix — no identity, so the JVM can flatten them inline — but it's been a decade, which tells you
how deep the split goes.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT THE COMPILER ACTUALLY INSERTS ──────────────────────────────
    list.add(5);              // → list.add(Integer.valueOf(5))
    int x = someInteger;      // → int x = someInteger.intValue()   ← THE NPE IS HERE
    Integer a = b + c;        // → Integer.valueOf(b.intValue() + c.intValue())
    if (nullableBoolean)      // → if (nullableBoolean.booleanValue())  ← and here
    // NONE of this appears in your source. That is what makes it dangerous.

    // ── THE CACHE BOUNDARY ──────────────────────────────────────────────
    Integer a = 127, b = 127;  System.out.println(a == b);   // true
    Integer c = 128, d = 128;  System.out.println(c == d);   // FALSE
    //                                            ^^^^^^ valueOf returns a CACHED
    //   instance for −128..127 and a NEW object outside it. The comparison silently
    //   changed from value equality to reference equality. REQUIRED BY THE SPEC for
    //   that range, so it is portable behaviour, not a JVM quirk.
    System.out.println(c.equals(d));       // true — always use this
    System.out.println(c.intValue() == d); // true — or unbox one side

    // ── THE NPE WITH NO METHOD CALL ON THE LINE ─────────────────────────
    Map<String,Integer> m = new HashMap<>();
    int count = m.get("missing");
    //          ^^^^^^^^^^^^^^^^ returns null → .intValue() → NullPointerException,
    //   reported at an ASSIGNMENT. Nothing in the source says "call a method".
    int count = m.getOrDefault("missing", 0);      // ← the fix

    // ── THE TERNARY, WHICH IS THE NASTIEST CORNER ───────────────────────
    Boolean enabled = flags.containsKey(k) ? flags.get(k) : false;
    //                                                      ^^^^^ a primitive boolean,
    //   which forces the WHOLE expression to type `boolean` — so flags.get(k) is
    //   UNBOXED, and throws NullPointerException when the stored value is null.
    //   EVEN THOUGH `enabled` IS A Boolean THAT WOULD HAVE ACCEPTED null.
    Boolean enabled = flags.containsKey(k) ? flags.get(k) : Boolean.FALSE;
    //                                                      ^^^^^^^^^^^^^ both branches
    //   are references now, so no promotion and no unboxing. Identical-looking line.
    Integer x = flag ? 1 : nullableInteger;   // NPE when flag is FALSE, same rule

    // ── ONE CAPITAL LETTER, MILLIONS OF ALLOCATIONS ─────────────────────
    Long sum = 0L;
    for (long i = 0; i < 10_000_000; i++) sum += i;
    //                                    ^^^^^^ unbox, add, BOX AGAIN. Ten million
    //   Long objects allocated, because wrappers are immutable.
    long sum = 0L;                     // ← the fix. Zero allocations.

    // ── THE MEMORY DIFFERENCE, CONCRETELY ───────────────────────────────
    int[] a = new int[1_000_000];
    //  4 MB. ONE contiguous block. 16 values per 64-byte cache line. The prefetcher
    //  runs ahead of you.
    List<Integer> b = ...;   // 1,000,000 entries
    //  a 4 MB array of REFERENCES + 1,000,000 Integer objects at 16 bytes each
    //  (12-byte header + 4-byte value, 8-byte aligned) ≈ 20 MB, SCATTERED.
    //  Reading element i: load the reference, THEN follow it. A dependent cache miss
    //  per element. FIVE TIMES THE MEMORY IN THE WRONG SHAPE.

    // ── WHY List<int> DOES NOT EXIST ────────────────────────────────────
    // Erasure replaces T with Object. Object is a REFERENCE. A primitive is not.
    // That single fact is why IntStream exists alongside Stream<Integer>, why
    // OptionalInt exists alongside Optional<Integer>, and why fastutil exists.
    items.stream().map(Item::count).reduce(0, Integer::sum);   // boxes EVERY value
    items.stream().mapToInt(Item::count).sum();                // no boxing at all

    // ── THREE SILENT ARITHMETIC TRAPS ───────────────────────────────────
    Integer.MAX_VALUE + 1;             // Integer.MIN_VALUE. No exception.
    Math.addExact(Integer.MAX_VALUE, 1);   // throws ArithmeticException
    long total = bigInt * 1000;        // int * int OVERFLOWS BEFORE the assignment
    long total = (long) bigInt * 1000; // ← cast one operand first
    byte b = (byte) 0xFF;              // −1, because byte is SIGNED
    int unsigned = b & 0xFF;           // 255. And the result needs an int.""",

"""9. THE TRACE — the same loop, two declarations

TEN MILLION ADDITIONS, differing by one capital letter:

    long sum = 0L;                          Long sum = 0L;
    for (...) sum += i;                     for (...) sum += i;
    ---------------------------------------------------------------------------------
    bytecode per iteration:                 bytecode per iteration:
      lload / ladd / lstore                   sum.longValue()      ← unbox
      (three instructions, registers only)    ladd
                                              Long.valueOf(result) ← BOX: allocate
                                              astore
    ---------------------------------------------------------------------------------
    allocations: ZERO                       allocations: 10,000,000 Long objects
    heap churn:  none                       ~160 MB pushed through the young generation
    ---------------------------------------------------------------------------------
    THE CODE IS VISUALLY IDENTICAL. The right column allocates because wrappers are IMMUTABLE — `sum +=
    i` cannot modify the existing Long, so it must produce a new one. This is the same reason string
    concatenation in a loop is quadratic: immutability plus reassignment in a loop.

    (The garbage is short-lived so the GC handles it cheaply — see the generational hypothesis — but
    the boxing, unboxing and allocation instructions are pure overhead in the loop body itself.)

THE CACHE BOUNDARY, traced through `valueOf`:

    expression        what valueOf does                          `==` result
    ---------------------------------------------------------------------------------
    Integer a = 127   in −128..127 → returns cache[255]           a == b is TRUE
    Integer b = 127   in range → returns THE SAME cache[255]      (same object)
    Integer c = 128   OUT of range → `new Integer(128)`           c == d is FALSE
    Integer d = 128   out of range → ANOTHER new Integer(128)     (different objects)
    ---------------------------------------------------------------------------------
    THE WORST POSSIBLE FAILURE PATTERN: it works for exactly the values a developer tests with — loop
    counters, small ids, sizes — and fails for the values production uses. And it is SPECIFIED, so no
    JVM will save you.

THE TERNARY, traced through the type rules:

    Boolean enabled = flags.containsKey(k) ? flags.get(k) : false;
    step  what the compiler does
    ---------------------------------------------------------------------------------
    1     look at BOTH branch types: `Boolean` and `boolean`
    2     both are convertible to a numeric/boolean type and one is a PRIMITIVE, so the
          conditional is promoted → the expression's type is `boolean`
    3     therefore the selected branch must yield a `boolean`
    4     so `flags.get(k)` gets an inserted `.booleanValue()` call
    5     the resulting `boolean` is then RE-BOXED to assign to `Boolean enabled`
    ---------------------------------------------------------------------------------
    AT RUNTIME, when the key is present with a null value: step 4 runs `.booleanValue()` on null → NPE.
    The target variable is a `Boolean` and would have accepted null perfectly well — the unboxing came
    entirely from the OTHER branch being a primitive.

    now change ONE token:
    Boolean enabled = flags.containsKey(k) ? flags.get(k) : Boolean.FALSE;
    ---------------------------------------------------------------------------------
    1     both branch types are now `Boolean` — no primitive operand
    2     no promotion. The expression's type is `Boolean`.
    3     no unboxing is inserted anywhere. null flows through unharmed.
    ---------------------------------------------------------------------------------
    THE TYPE OF A CONDITIONAL EXPRESSION IS DECIDED FROM BOTH OPERANDS, BEFORE EITHER BRANCH IS
    CHOSEN. Which is why reading the branch that runs tells you nothing about whether it will throw, and
    why `false` versus `Boolean.FALSE` — five characters — is the entire difference.

AND THE ACCESS-PATTERN TRACE, one million elements:

    structure         what reading element i costs
    ---------------------------------------------------------------------------------
    int[]             one array index into a contiguous block. The line holding
                      element i also holds i+1..i+15, and the prefetcher already
                      fetched the next line. ~62,500 line fetches, nearly all free.
    List<Integer>     read the reference from the contiguous array (cheap, prefetched)
                      THEN dereference it to an object that may be anywhere on the
                      heap. A DEPENDENT LOAD — the CPU cannot fetch ahead because it
                      does not know the address until the first load returns.
    ---------------------------------------------------------------------------------
    SAME O(1) PER ELEMENT. One runs at memory BANDWIDTH, the other at memory LATENCY. That distinction
    is invisible in Big-O and is most of the real difference — the 5× memory figure understates it.

WHAT PRODUCED WHAT:
    IMMUTABILITY OF WRAPPERS   produced the ten million allocations.
    THE −128..127 CACHE        produced `==` working for test values and failing for production ones.
    NUMERIC PROMOTION          produced the ternary NPE, and it is a TYPE rule, so no runtime check
                               could have avoided it.
    IDENTITY ITSELF            produced the indirection, and therefore the dependent cache miss.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `int`: 4 bytes, no header, no indirection. `Integer`: 16 bytes (12-byte header + 4-byte value,
    8-byte aligned) plus a 4-byte reference to reach it.
    A million: `int[]` ≈ 4 MB contiguous; `List<Integer>` ≈ 20 MB scattered. About 5×, and the access
    pattern is worse than the ratio suggests — bandwidth versus latency.
    Wrapper caches: Integer/Short/Byte/Long −128..127, Character 0..127, Boolean always. Float and
    Double NEVER.
    Boxing allocates; unboxing can throw. Both are inserted invisibly by the compiler.
    Generics cannot take primitives, because erasure turns `T` into `Object`.

THE #1 MISTAKE: `==` on wrappers. Works below 128, fails above it. The worst possible failure pattern,
and it is specified behaviour rather than a bug.

THE #2 MISTAKE: unboxing a possibly-null wrapper. An NPE on a line with no visible method call. Use
`getOrDefault` or check first.

THE #3 MISTAKE: a ternary with one primitive branch and one nullable wrapper branch. Promotion unboxes
the selected branch even when the target variable is a wrapper that would have accepted null — a TYPE
rule decided from both operands before either is chosen.

THE #4 MISTAKE: a wrapper accumulator in a loop. One capital letter, millions of allocations.

THE #5 MISTAKE: `Stream<Integer>` where `IntStream` belongs. Every element boxed.

THE #6 MISTAKE: `List<Integer>` for large numeric data. Five times the memory and a dependent cache
miss per element. Use `int[]` or a primitive collection library.

THE #7 MISTAKE: `list.remove(1)` on a `List<Integer>`. Index or value, chosen silently by overload
resolution.

THE #8 MISTAKE: forgetting `byte` is signed. `0xFF` reads as `−1` in binary I/O.

THE #9 MISTAKE: treating `char` as a character. It is a UTF-16 code unit; emoji take two.

THE #10 MISTAKE: assuming overflow throws. It wraps silently. `Math.addExact` if it matters.

THE #11 MISTAKE: `int * int` assigned to a `long`. The multiplication overflows before the assignment.
Cast one operand first.

THE #12 MISTAKE: `synchronized` on an `Integer` or `Boolean`. Cached instances are globally shared
locks.

ONE-SENTENCE TAKEAWAY: a primitive is a bare VALUE with no identity and no null, while a wrapper is a
heap object with a 12-byte header and a reference to reach it — and autoboxing hid that distinction so
thoroughly that `==` silently switches from value to reference comparison at the −128..127 cache
boundary, unboxing throws NullPointerException on lines containing no method call (worst of all inside a
ternary, where one primitive branch forces the other to be unboxed even when you are assigning the
result to a wrapper that would have accepted null), and a single capital letter
turns an allocation-free loop into ten million allocations; because erasure turns `T` into `Object`,
generics cannot hold primitives at all, which is why `IntStream` and `OptionalInt` and fastutil exist,
and why a million numbers cost 4 MB contiguous as an `int[]` and about 20 MB scattered as a
`List<Integer>` — five times the memory in a shape that turns a prefetched sequential scan into a
dependent cache miss per element.""",
]


DEEP["Static nested vs inner class — and the memory leak the inner one causes"] = [
"""1. THE GOAL IN PLAIN ENGLISH — one keyword, and a hidden reference

You can declare a class inside another class. If you write `static` in front of it, you get a STATIC
NESTED CLASS. If you leave `static` off, you get an INNER CLASS. They look nearly identical in source
and they are fundamentally different objects.

    A STATIC NESTED CLASS IS JUST A TOP-LEVEL CLASS THAT LIVES IN ANOTHER CLASS'S NAMESPACE. It knows
    nothing about any instance of the outer class. You create one with `new Outer.Nested()`, and it has
    no more connection to an `Outer` object than any unrelated class would.

    AN INNER CLASS SECRETLY HOLDS A REFERENCE TO THE OUTER INSTANCE THAT CREATED IT. The compiler adds
    a hidden field — conventionally named `this$0` — and a hidden constructor parameter to pass it in.
    That is how `inner.someOuterMethod()` works without you writing anything: it is really
    `this$0.someOuterMethod()`.

    ONE KEYWORD ADDS A REFERENCE TO ANOTHER OBJECT, AND THE SOURCE CODE DOES NOT SHOW IT.

    AND THAT REFERENCE IS THE MEMORY LEAK. As long as ANYTHING holds your inner-class instance, the
    entire outer object — and everything IT references — cannot be collected. Hand a short-lived inner
    class to a long-lived registry, executor or timer, and you have pinned an object graph you never
    meant to keep.

THE EVERYDAY VERSION: two kinds of note in a filing cabinet. One is a standalone note that happens to be
filed under "Projects". The other is a sticky note attached to a specific 200-page dossier — pick up
the sticky note and the whole dossier comes with it, because it is stuck to it. If someone pins that
sticky note to a noticeboard for a year, the dossier hangs there too.

TERMS AS THEY APPEAR:
- ENCLOSING INSTANCE: the outer object an inner class instance belongs to.
- `this$0`: the compiler-generated field holding it. Visible in a heap dump; invisible in source.
- LOCAL CLASS: a class declared inside a method.
- ANONYMOUS CLASS: a class declared and instantiated in one expression — `new Runnable() { ... }`.""",

"""2. THE INTUITION — four kinds of nested class, and one rule

JAVA HAS FOUR, and they differ in exactly one dimension: WHAT DOES EACH ONE CAPTURE?

    STATIC NESTED    captures NOTHING. `static class Node { ... }`
    INNER            captures the ENCLOSING INSTANCE. `class Node { ... }`
    LOCAL            captures the enclosing instance (if in an instance context) AND the effectively
                     final local variables it uses.
    ANONYMOUS        the same as local, declared and instantiated in one expression.

    THE RULE THAT FOLLOWS IS EFFECTIVE JAVA ITEM 24, AND IT IS ABOUT AS UNAMBIGUOUS AS ADVICE GETS:
    IF A MEMBER CLASS DOES NOT NEED ACCESS TO AN ENCLOSING INSTANCE, ALWAYS DECLARE IT `static`.

    Because a non-static one costs a reference field per instance, costs the memory of everything
    reachable through it, and prevents the outer object from ever being collected while any inner
    instance is alive. YOU PAY ALL THREE FOR A CAPABILITY YOU ARE NOT USING.

THE JDK FOLLOWS ITS OWN ADVICE, AND THE PAIR OF CHOICES IT MADE IS THE BEST ILLUSTRATION OF THE TEST.
`HashMap.Node`, `HashMap.TreeNode`, `ConcurrentHashMap.Node` and `AbstractMap.SimpleEntry` are all
`static`, because a map entry does not need to know which map it came from — and a `HashMap` with a
million entries would otherwise carry a million redundant back-pointers to the same object. But
`ArrayList.Itr` is deliberately INNER, because an iterator genuinely must see the list's `modCount` and
`elementData`, and there is one of it at a time.

    THAT IS THE TEST TO APPLY: DOES AN INSTANCE OF THIS CLASS GENUINELY NEED TO REACH BACK? An iterator
    does. A node does not. A builder does not. A comparator does not.

WHY LOCAL VARIABLES MUST BE "EFFECTIVELY FINAL" — the reason is mechanical, not stylistic:

    Java does NOT close over the variable; it COPIES THE VALUE into a synthetic field of the inner
    class instance. So the inner class and the method now hold two separate copies. If the method
    changed its copy afterwards, the two would silently diverge and nobody could say which one was
    "the" value.

    OTHER LANGUAGES CHOSE DIFFERENTLY. JavaScript closures capture the VARIABLE, so a loop that creates
    closures over `i` famously gives every closure the final value. Java's copy-by-value semantics make
    that class of bug impossible — at the cost of forbidding mutation, which is why the workaround is a
    one-element array or an `AtomicInteger`.

LAMBDAS ARE NOT INNER CLASSES, AND THE DIFFERENCE IS WORTH KNOWING:

    Inside an anonymous class, `this` refers to THE ANONYMOUS INSTANCE. Inside a lambda, `this` refers
    to the ENCLOSING instance — lambdas do not introduce a new scope for `this`, `super` or names.
    A NON-CAPTURING LAMBDA IS INSTANTIATED ONCE and reused; an anonymous class allocates a new object
    every time the expression is evaluated.
    But a lambda that DOES reference an instance member captures `this` just as firmly, so it leaks
    exactly the same way. LAMBDAS ARE NOT A CURE FOR THIS LEAK — they just make it easier to miss.""",

"""3. THE MECHANISM — what the compiler generates, and where the leak shows up

WHAT `javac` ACTUALLY EMITS for an inner class:

    class Outer$Inner {
        final Outer this$0;                        // ← the hidden field
        Outer$Inner(Outer outer) { this$0 = outer; }  // ← the hidden parameter
        void doThing() { this$0.outerMethod(); }   // ← how "implicit" access works
    }

    Writing `new Inner()` inside an instance method compiles to `new Outer$Inner(this)`. From OUTSIDE
    the outer class you must write the strange-looking `outer.new Inner()`, because an enclosing
    instance is REQUIRED and there is nowhere else to get one. THAT SYNTAX IS THE LANGUAGE TELLING YOU
    THE DEPENDENCY EXISTS.

    A static nested class compiles to `Outer$Nested` with no extra field and no extra parameter.

WHERE THE COST LANDS:
    MEMORY PER INSTANCE: one reference — 4 bytes with compressed pointers. Trivial on its own, and
    material when there are millions (which is precisely why `HashMap.Node` is static).
    RETAINED MEMORY: unbounded. The inner instance keeps the outer object alive, and the outer object
    keeps alive everything IT references. A 4-byte field can retain 200 MB.
    SERIALIZATION: serializing an inner class instance drags the outer object in too — and if the outer
    class is not `Serializable`, you get `NotSerializableException` naming a class you never tried to
    serialize.

THE LEAK PATTERN, IN ITS THREE COMMONEST FORMS:

    A LISTENER OR CALLBACK. `registry.add(new Listener() { ... })` inside an instance method captures
    the enclosing object. The registry lives for the life of the application. So does the enclosing
    object.
    A `Runnable` OR `TimerTask` HANDED TO AN EXECUTOR. If the task is scheduled at a fixed rate, the
    executor holds it forever.
    A `Thread` SUBCLASS OR A NON-STATIC `Handler`. The canonical Android bug: an inner `Handler`
    holding an `Activity`, keeping an entire screen's view hierarchy and bitmaps alive across rotations.
    THIS IS THE SINGLE MOST COMMON MEMORY LEAK IN THE HISTORY OF ANDROID, and it is one missing
    `static`.

HOW YOU SEE IT: in a heap dump, open the DOMINATOR TREE and look at what retains the outer object. The
path will read `... → Outer$1 → this$0 → Outer`. THE `this$0` EDGE IN A RETENTION PATH IS THE
DIAGNOSIS — once you have seen it once, you recognise it instantly.

NESTMATES (Java 11, JEP 181), for completeness: nested classes have always been able to touch each
other's `private` members, but the JVM had no concept of nesting, so `javac` generated SYNTHETIC
package-private bridge methods (`access$000`) to make it work. Java 11 gave the class file `NestHost`
and `NestMembers` attributes, so the JVM enforces it directly and the synthetic accessors disappeared.
This is why old decompiled code is full of `access$000` calls and modern code is not.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — A NON-STATIC LISTENER REGISTERED WITH A LONG-LIVED REGISTRY. The enclosing object and its
entire graph live for the application's lifetime. The most common instance of this bug class.

CASE 2 — AN INNER `Runnable` SUBMITTED TO A SCHEDULED EXECUTOR. Held until the schedule is cancelled,
which is usually never.

CASE 3 — AN INNER CLASS RETURNED FROM A FACTORY. The caller has no idea they are holding the factory
too, and neither does the review.

CASE 4 — SERIALIZING AN INNER CLASS. The outer instance is serialized as well, or you get
`NotSerializableException` naming a class you never mentioned.

CASE 5 — MILLIONS OF INNER-CLASS INSTANCES. One redundant reference each. This is exactly why
`HashMap.Node` is `static` and why the JDK is careful about it everywhere.

CASE 6 — `outer.new Inner()` FROM OUTSIDE. The syntax is unfamiliar enough that people conclude the API
is broken. It is the language insisting an enclosing instance exists.

CASE 7 — `this` INSIDE AN ANONYMOUS CLASS MEANING THE ANONYMOUS INSTANCE. To reach the outer one you
need `Outer.this`. Inside a LAMBDA, `this` already means the outer instance — the two read identically
and mean different things.

CASE 8 — A LAMBDA THAT CAPTURES `this`. `() -> this.field` or, more subtly, `() -> field` and
`this::method` — all capture the enclosing instance and leak exactly like an inner class. LAMBDAS ARE
NOT A FIX.

CASE 9 — CAPTURING A LOCAL AND EXPECTING TO MUTATE IT. Captured locals are COPIED, so they must be
effectively final. The array-of-one workaround works and signals that the design wants a different
shape.

CASE 10 — A NESTED CLASS THAT NEEDS ITS OWN STATIC FIELDS. Before Java 16, a non-static inner class
could not declare `static` members other than constants at all — a genuine source of "why won't this
compile".

CASE 11 — REFLECTION AND FRAMEWORKS. An inner class has no no-argument constructor from the JVM's point
of view; its constructor takes the enclosing instance. Frameworks that instantiate reflectively
(Jackson, JPA, JUnit parameter resolvers) fail on inner classes and work on static nested ones.

CASE 12 — ANONYMOUS CLASSES IN A LOOP. Each evaluation allocates a new object. A NON-CAPTURING lambda in
the same position is instantiated once and reused.

CASE 13 — DEBUGGING NAMES. `Outer$1`, `Outer$2` in stack traces and heap dumps tell you nothing about
which anonymous class it is. A named static nested class costs nothing and is greppable.""",

"""5. THE ALTERNATIVES — what to use instead of an inner class

`static` NESTED, ALMOST ALWAYS. The default for any helper type that belongs to a class conceptually
but does not need to reach back: `Builder`, `Node`, `Entry`, `Config`, a `Comparator`, a result holder.
ADD THE KEYWORD UNLESS YOU CAN NAME WHAT THE INSTANCE NEEDS FROM THE OUTER OBJECT.

PASS WHAT YOU NEED EXPLICITLY. If the nested class needs three fields from the outer object, take them
as constructor parameters. Now the dependency is visible, testable in isolation, and it retains three
fields rather than an entire object graph.

A `record` FOR DATA CARRIERS. `record Point(int x, int y) { }` nested inside a class is implicitly
static, gives you `equals`/`hashCode`/`toString`, and cannot accidentally capture anything.

A LAMBDA OR METHOD REFERENCE for a single-method callback — but ONLY IF IT DOES NOT CAPTURE `this`. A
lambda referencing no instance state compiles to a static method, is instantiated once, and retains
nothing. One that touches an instance field leaks identically to an inner class.

A WEAK REFERENCE, when a callback genuinely must be able to reach a long-lived owner:
`WeakReference<Activity>` inside a STATIC nested class is the standard Android fix — the callback can
still find its owner while the owner is alive, and does not prevent it from dying.

EXPLICIT DEREGISTRATION. The real fix for listener leaks is usually not weak references but symmetry:
whatever registered must unregister, in a `close()` or a lifecycle callback. try-with-resources makes
that structural.

A TOP-LEVEL CLASS. If a nested class is more than a screenful, or is used by more than its enclosing
class, it should probably not be nested at all. Nesting is for types that are an implementation detail
of exactly one class.

NESTED ENUMS, INTERFACES AND RECORDS ARE IMPLICITLY `static` — you cannot make them inner even by
accident, which is a hint about which default the language designers came to prefer.

WHAT TO SAY: "`static` on every nested class unless the instance genuinely needs the enclosing one — an
iterator does, a node or a builder does not. The non-static version adds a hidden `this$0` field, so
handing one to a listener registry or a scheduled executor pins the entire enclosing object graph, and
in a heap dump you see it as a `this$0` edge in the retention path. And a lambda that touches an
instance field captures `this` just as firmly, so it is not a cure."

""",

"""6. HOW TO DECIDE AND HOW TO DIAGNOSE — numbered steps

STEP 1 — ASK: DOES AN INSTANCE OF THIS CLASS NEED TO REACH THE OUTER OBJECT? If you cannot name what it
needs, write `static`.

STEP 2 — DEFAULT TO `static` AND REMOVE IT ONLY WHEN THE COMPILER FORCES YOU. The error will name the
member you are reaching for, which is exactly the justification you were asked for in step 1.

STEP 3 — IF IT NEEDS TWO OR THREE VALUES, PASS THEM IN. Constructor parameters make the dependency
visible and retain three fields instead of a whole graph.

STEP 4 — NEVER HAND A NON-STATIC NESTED INSTANCE TO SOMETHING LONGER-LIVED THAN THE OUTER OBJECT.
Registries, executors, timers, caches, static collections.

STEP 5 — TREAT A CAPTURING LAMBDA THE SAME WAY. `() -> field` and `this::method` capture `this`.

STEP 6 — MAKE REGISTRATION SYMMETRIC. Whatever adds a listener must remove it, ideally via
try-with-resources or an explicit lifecycle hook.

STEP 7 — USE A STATIC NESTED CLASS PLUS A `WeakReference` when a callback must reach a long-lived owner
it should not keep alive.

STEP 8 — PREFER A NAMED STATIC NESTED CLASS OVER AN ANONYMOUS ONE for anything non-trivial. `Outer$1` in
a stack trace tells you nothing.

STEP 9 — USE A `record` FOR NESTED DATA CARRIERS. Implicitly static, with value semantics for free.

STEP 10 — IF A FRAMEWORK CANNOT INSTANTIATE YOUR NESTED CLASS, CHECK FOR THE MISSING `static`. An inner
class has no no-arg constructor as far as reflection is concerned.

STEP 11 — WHEN DIAGNOSING A LEAK, OPEN THE DOMINATOR TREE AND LOOK FOR A `this$0` EDGE. It is the
single most recognisable retention path in Java.

STEP 12 — IF THE NESTED CLASS IS LONGER THAN A SCREEN OR USED ELSEWHERE, PROMOTE IT TO TOP LEVEL.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A static nested class is just a top-level class living in another class's namespace. It knows nothing
about any instance of the outer class. An inner class — the same declaration with `static` left off —
secretly holds a reference to the outer instance that created it. The compiler adds a hidden field,
conventionally called this$0, and a hidden constructor parameter to pass it in. That's how calling an
outer method from inside works without writing anything: it's really this$0.outerMethod().

So one keyword adds a reference to another object, and the source doesn't show it.

And that reference is the memory leak. As long as anything holds your inner-class instance, the entire
outer object — and everything IT references — can't be collected. Hand a short-lived inner class to a
listener registry, an executor or a timer, and you've pinned an object graph you never meant to keep.
The canonical case is Android: a non-static Handler holding an Activity keeps an entire screen's view
hierarchy and bitmaps alive across rotations. That's probably the most common memory leak in the
history of the platform, and it's one missing `static`.

The rule I'd state is Effective Java Item 24, and it's about as unambiguous as advice gets: if a member
class doesn't need access to an enclosing instance, ALWAYS declare it static. Because otherwise you pay
a reference field per instance, you pay the retained memory of everything reachable through it, and you
prevent collection — all for a capability you're not using.

The JDK follows its own advice, and that's the best evidence for the test to apply. HashMap.Node,
TreeNode, ConcurrentHashMap.Node, AbstractMap.SimpleEntry — all static, because a map entry doesn't need
to know which map it came from, and a million-entry HashMap would otherwise carry a million redundant
back-pointers. But ArrayList's iterator IS an inner class, deliberately, because an iterator genuinely
must see the list's modCount and elementData. So the test is: does an instance need to reach back? An
iterator does. A node, a builder, a comparator doesn't.

Two related things worth knowing. Captured LOCAL variables must be effectively final for a mechanical
reason, not a stylistic one: Java doesn't close over the variable, it COPIES the value into a synthetic
field. So the method and the inner class hold two separate copies, and if the method changed its copy
they'd silently diverge. JavaScript captures the variable instead, which is why the classic loop-closure
bug exists there and can't here.

And lambdas are not a cure. Inside an anonymous class, `this` means the anonymous instance; inside a
lambda it means the ENCLOSING instance, because lambdas don't introduce a new scope for `this`. A
non-capturing lambda is instantiated once and retains nothing. But a lambda that touches an instance
field — even just `() -> field`, or a `this::method` reference — captures `this` just as firmly and
leaks identically. It's just easier to miss.

When I'm diagnosing one, I take a heap dump and read the dominator tree looking for a this$0 edge in the
retention path. Once you've seen that once you recognise it instantly.'""",

"""8. THE CODE, LINE BY LINE

    // ── ONE KEYWORD, TWO DIFFERENT OBJECTS ──────────────────────────────
    class Outer {
        private int value = 42;
        static class Nested { void f() { /* cannot see `value` */ } }
        class Inner       { void f() { System.out.println(value); } }
    //  ^ no `static`                                   ^^^^^ this compiles to
    //                                                  this$0.value
    }
    new Outer.Nested();                // fine — no enclosing instance needed
    new Outer().new Inner();           // ← the strange syntax IS the language telling
    //                                    you an enclosing instance is REQUIRED

    // ── WHAT javac ACTUALLY GENERATES ───────────────────────────────────
    class Outer$Inner {
        final Outer this$0;                          // ← THE HIDDEN FIELD
        Outer$Inner(Outer outer) { this$0 = outer; } // ← THE HIDDEN PARAMETER
        void f() { System.out.println(this$0.value); }
    }
    // 4 bytes with compressed pointers. Trivial per instance. UNBOUNDED in what it
    // RETAINS — that 4-byte field can hold 200 MB alive.

    // ── THE LEAK ────────────────────────────────────────────────────────
    class Screen {                          // holds 50 MB of cached view state
        void start() {
            EventBus.register(new Listener() {       // ← ANONYMOUS = INNER
                public void onEvent(Event e) { redraw(); }
    //                                          ^^^^^^ an instance method, so this$0
    //          is captured. The EventBus is static and lives forever. THEREFORE SO
    //          DOES THIS Screen AND ITS 50 MB.
            });
        }
    }
    class Screen {                                    // ← the fix
        static class Handler implements Listener {    // ← STATIC: no this$0 at all
            private final WeakReference<Screen> ref;
            Handler(Screen s) { this.ref = new WeakReference<>(s); }
            public void onEvent(Event e) {
                Screen s = ref.get();                 // may be null — and that is
                if (s != null) s.redraw();            // exactly the point
            }
        }
    }

    // ── LAMBDAS ARE NOT A CURE ──────────────────────────────────────────
    executor.submit(() -> System.out.println("hi"));   // captures NOTHING. Compiled
    //                                                    to a static method,
    //                                                    instantiated ONCE, reused.
    executor.submit(() -> redraw());                   // ← CAPTURES `this`. Leaks
    executor.submit(this::redraw);                     // ← CAPTURES `this`. Leaks
    executor.submit(() -> System.out.println(field));  // ← CAPTURES `this`. Leaks
    //   All three read as "just a lambda". Two of them pin the enclosing object.

    // ── `this` MEANS DIFFERENT THINGS ───────────────────────────────────
    new Runnable() { public void run() {
        System.out.println(this);          // ← the ANONYMOUS instance
        System.out.println(Outer.this);    // ← the enclosing one
    }};
    Runnable r = () -> System.out.println(this);   // ← the ENCLOSING instance.
    //   Lambdas do not introduce a new scope for `this`, `super` or names.

    // ── WHY CAPTURED LOCALS MUST BE EFFECTIVELY FINAL ───────────────────
    void f() {
        int count = 0;
        Runnable r = () -> System.out.println(count);   // ✓ effectively final
        count++;                                        // ✗ NOW IT DOES NOT COMPILE
    //  ^ Java COPIES the value into a synthetic field. The method and the lambda
    //    would hold two separate copies and diverge silently. (JavaScript captures
    //    the VARIABLE instead — which is why its loop-closure bug exists and Java's
    //    cannot.)
        int[] box = {0};
        Runnable r2 = () -> box[0]++;      // the workaround: the ARRAY reference is
    }                                      // final; its contents are not.

    // ── AND WHAT THE JDK ITSELF DOES ────────────────────────────────────
    static class Node<K,V> { ... }         // HashMap.Node — STATIC. A million entries
    //                                        would otherwise carry a million
    //                                        redundant back-pointers to the map.
    private class Itr implements Iterator  // ArrayList.Itr — INNER, deliberately: an
    //                                        iterator genuinely needs modCount and
    //                                        elementData. THAT is the test.""",

"""9. THE TRACE — one missing keyword, followed through a heap dump

THE SETUP: a `Screen` object holding 50 MB of cached bitmaps registers a listener at startup and is then
discarded. This repeats every time the user navigates.

    WITH AN ANONYMOUS (INNER) LISTENER
    step  what happens                                   what is reachable
    ---------------------------------------------------------------------------------
    1     new Screen() — 50 MB of state                   Screen, from a local
    2     EventBus.register(new Listener(){...})          the listener is now in a
          → compiles to new Screen$1(this)                STATIC list
    3     the user navigates away; every local             Screen has NO local
          reference to Screen is dropped                   references left
    4     GC runs                                          EventBus (static, a ROOT)
                                                           → listener list
                                                           → Screen$1
                                                           → this$0
                                                           → SCREEN. STILL ALIVE.
    5     repeat 20 times                                  1 GB retained, 20 dead
                                                           Screens, OutOfMemoryError
    ---------------------------------------------------------------------------------
    EVERY STEP IS CORRECT. The GC is doing exactly its job: `Screen` is REACHABLE. Nothing in the source
    of step 2 mentions `Screen` at all — the reference was added by the compiler.

    THE HEAP DUMP, dominator tree:
        EventBus                        retained: 1,048 MB
          └─ ArrayList                  retained: 1,048 MB
             └─ Screen$1                retained:    52 MB
                └─ this$0 → Screen      retained:    52 MB   ← THE DIAGNOSIS
                   └─ Bitmap[]          retained:    50 MB
    ---------------------------------------------------------------------------------
    THE `this$0` EDGE IS THE WHOLE ANSWER, and it appears in no source file. Once you have seen this
    shape once you recognise it in seconds; until then it is baffling, because the retained object
    appears in a path that mentions a class you never wrote.

    WITH A STATIC NESTED LISTENER HOLDING A WeakReference
    step  what happens                                   what is reachable
    ---------------------------------------------------------------------------------
    1-3   identical                                       —
    4     GC runs                                          EventBus → list → Handler
                                                           → WeakReference → (weak)
                                                           SCREEN IS COLLECTED
    5     the next event arrives; ref.get() is null;       the Handler itself is a few
          the handler does nothing and can deregister      bytes and can be cleaned up
    ---------------------------------------------------------------------------------
    50 MB freed per navigation. Same registry, same lifetime, same event flow.

NOW THE LAMBDA TRACE, which is the version people believe is safe:

    expression                          captures            allocated
    ---------------------------------------------------------------------------------
    () -> System.out.println("hi")      NOTHING              ONCE, then reused —
                                                             compiled to a static
                                                             method, and the metafactory
                                                             caches the instance
    () -> System.out.println(x)         x (a local COPY)     per evaluation
    where x is an effectively final local
    () -> redraw()                      `this`               per evaluation, AND PINS
                                                             THE ENCLOSING OBJECT
    this::redraw                        `this`               same as above
    () -> field                         `this`               same as above — reading a
                                                             field is really this.field
    ---------------------------------------------------------------------------------
    ROWS 3, 4 AND 5 LEAK EXACTLY LIKE AN INNER CLASS, and all five read as "just a lambda". Row 5 is the
    subtlest: there is no `this` written anywhere in it.

AND THE PER-INSTANCE COST, at scale:

    structure                                     extra memory
    ---------------------------------------------------------------------------------
    HashMap with 1,000,000 entries, Node STATIC    0
    the same with Node as an INNER class           1,000,000 × 4 bytes = 4 MB of
                                                   back-pointers, every one of them
                                                   pointing at the SAME map
    ---------------------------------------------------------------------------------
    Which is why `HashMap.Node` is static and `ArrayList.Itr` is not: there is one iterator at a time
    and it genuinely needs the list, while there are a million nodes and not one of them needs anything.

WHAT PRODUCED WHAT:
    THE HIDDEN this$0 FIELD    produced the retention path, the OutOfMemoryError, and the 4 MB.
    REACHABILITY, NOT USE      produced "the GC is correct at every step" — see the GC entry.
    LEXICAL `this` IN LAMBDAS  produced rows 3–5 of the lambda table, and therefore produced the belief
                               that lambdas fixed this.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Static nested: no extra field, no extra constructor parameter, instantiable with `new Outer.Nested()`.
    Inner: one reference field (`this$0`, 4 bytes compressed) and a hidden constructor parameter;
    instantiable only as `outer.new Inner()`.
    RETAINED memory from that 4-byte field: unbounded — everything the outer object reaches.
    Non-capturing lambda: compiled to a static method, instantiated once, retains nothing.
    Capturing lambda or anonymous class: a new object per evaluation.
    Nested enums, interfaces and records are IMPLICITLY static.
    Java 11 nestmates removed the synthetic `access$000` bridge methods javac used to generate.

THE #1 MISTAKE: omitting `static` on a nested class that does not need the enclosing instance. Effective
Java Item 24, and the fix is one keyword.

THE #2 MISTAKE: handing a non-static nested instance to a longer-lived owner — a registry, an executor,
a timer, a static collection. The enclosing object graph is now pinned.

THE #3 MISTAKE: believing a lambda cannot leak. `() -> field` and `this::method` capture `this` exactly
as firmly as an anonymous class.

THE #4 MISTAKE: assuming `this` inside an anonymous class is the outer object. It is the anonymous
instance; you need `Outer.this`. Inside a lambda it IS the outer object — the same word, two meanings.

THE #5 MISTAKE: expecting to mutate a captured local. Java copies the value, so it must be effectively
final. The one-element array works and signals a design that wants a different shape.

THE #6 MISTAKE: serializing an inner class. The outer instance goes too, or you get
`NotSerializableException` naming a class you never mentioned.

THE #7 MISTAKE: an inner class where a framework will instantiate reflectively. There is no no-arg
constructor; the real one takes the enclosing instance.

THE #8 MISTAKE: millions of inner-class instances. One redundant pointer each, all pointing at the same
object.

THE #9 MISTAKE: anonymous classes for anything non-trivial. `Outer$1` in a stack trace or heap dump is
unidentifiable; a named static nested class is greppable and costs nothing.

THE #10 MISTAKE: relying on weak references instead of deregistering. The real fix for a listener leak
is symmetry — whatever registered must unregister.

THE #11 MISTAKE: keeping a large nested class nested. If it exceeds a screen or is used elsewhere, it
is a top-level class.

ONE-SENTENCE TAKEAWAY: leaving `static` off a nested class makes the compiler add a hidden `this$0`
field holding the enclosing instance — which is how implicit access to the outer object works, and which
means any longer-lived thing holding that inner instance (a listener registry, a scheduled executor, a
static collection) keeps the ENTIRE outer object graph alive, with the GC behaving perfectly correctly
because reachable is not the same as needed; declare every nested class `static` unless you can name
what the instance needs from its enclosing one (an iterator can, a `HashMap.Node` cannot, which is
exactly how the JDK declares each), remember that a lambda touching any instance member — even bare
`field` — captures `this` just as firmly, and when diagnosing a leak look for the `this$0` edge in the
dominator tree, because it is the most recognisable retention path in Java and it appears in no source
file.""",
]


DEEP["var, records, sealed, text blocks — what Java 10-21 actually changed"] = [
"""1. THE GOAL IN PLAIN ENGLISH — Java spent a decade deleting ceremony

Java 8 (2014) was the last release most people learned properly. Java 11, 17 and 21 are the long-term
releases since, and the changes fall into two groups: ONE that removes typing, and THREE that together
add a genuinely new way to model data.

    `var` (JAVA 10) — write `var map = new HashMap<String, List<Integer>>()` instead of saying the type
    twice. IT IS NOT DYNAMIC TYPING. The type is fixed at compile time and is exactly what it would
    have been; you just did not have to write it.

    `record` (JAVA 16) — `record Point(int x, int y) { }` gives you a constructor, accessors, `equals`,
    `hashCode` and `toString`, all correct, in one line. It replaces the sixty-line data class that
    everyone generated with an IDE and then never maintained.

    `sealed` (JAVA 17) — `sealed interface Shape permits Circle, Square` declares a CLOSED set of
    subtypes. The compiler now knows every possible implementation.

    PATTERN MATCHING FOR `switch` (JAVA 21) — switch on the TYPE, destructure the record's components
    inline, and the compiler checks EXHAUSTIVENESS.

    THOSE LAST THREE ARE ONE FEATURE. Sealed types say what the alternatives are; records say what each
    alternative carries; pattern matching takes them apart and forces you to handle every case. Together
    they are ALGEBRAIC DATA TYPES, which functional languages have had for forty years, and they let you
    model "this is one of exactly these shapes" with the compiler enforcing it.

    TEXT BLOCKS (JAVA 15) are a smaller thing: multi-line string literals with the incidental
    indentation removed, so embedded SQL and JSON stop being a wall of `\\n` and escaped quotes.

THE EVERYDAY VERSION: `var` is not repeating "chocolate cake" on both the order slip and the box.
Records are a pre-printed form instead of writing the same six fields by hand every time. Sealed types
plus pattern matching are a checklist where the form itself tells you which boxes exist — and refuses to
be filed until every one is ticked.

TERMS AS THEY APPEAR:
- TYPE INFERENCE: the compiler working out a type you did not write.
- EXHAUSTIVE: covering every possible case, checked by the compiler.
- DECONSTRUCTION PATTERN: pulling a record's components out as part of a match.""",

"""2. THE INTUITION — why these four, and why now

`var` — THE POINT IS NOT BREVITY, IT IS THE SIGNAL-TO-NOISE RATIO ON THE LEFT-HAND SIDE.

    Map<String, List<Order>> ordersByCustomer = new HashMap<String, List<Order>>();

    The type is written twice and neither copy is where your eye goes. `var` deletes the copy that adds
    nothing. THE RULE THAT MAKES IT SAFE: use `var` when the RIGHT-HAND SIDE ALREADY TELLS YOU THE TYPE.
    `var list = new ArrayList<String>()` is obvious; `var result = process(input)` is not, and there
    `var` costs the reader something.

    IT IS STATICALLY TYPED. `var x = "hello"` makes `x` a `String` forever; `x = 5` is a compile error.
    It is confined to LOCAL variables with an initialiser, for-loop variables and try-with-resources —
    never fields, parameters or return types, because those are API surface and inference there would
    make a caller's contract depend on a method body.

`record` — THE POINT IS THAT THE COMPILER CAN NOW SEE THE STATE.

    A hand-written data class is sixty lines in which the fields, the constructor, the accessors,
    `equals`, `hashCode` and `toString` all say the same thing, and any of them can drift out of sync.
    ADD A FIELD AND FORGET TO ADD IT TO `equals` AND YOU HAVE A SILENT BUG that a `HashSet` will
    eventually reveal.

    A record declares the state ONCE, in the header, and everything else is derived. It is a
    "transparent carrier for its data" — the language's phrase — and transparency is what lets pattern
    matching deconstruct it later. THAT IS WHY RECORDS AND PATTERN MATCHING ARRIVED TOGETHER.

`sealed` — THE POINT IS EXHAUSTIVENESS, WHICH POLYMORPHISM NEVER GAVE YOU.

    Traditional advice says put behaviour in the subclasses and use dynamic dispatch. That works when
    the behaviour belongs to the type. It fails when you need to add an OPERATION over a fixed set of
    types you do not control the shape of, or when the operation belongs to another module — the classic
    "expression problem". The alternative was a chain of `instanceof`, which nothing checks.

    A sealed hierarchy lets the compiler know the full list, so a `switch` over it can be checked for
    completeness. ADD A NEW SUBTYPE AND EVERY INCOMPLETE SWITCH IN THE CODEBASE FAILS TO COMPILE. That
    is a guarantee virtual dispatch cannot offer, and it is the whole reason to reach for this instead
    of an abstract method.

TEXT BLOCKS — THE POINT IS THE INDENTATION ALGORITHM, NOT THE TRIPLE QUOTES. Java computes the minimum
indentation across all non-blank lines AND the closing delimiter, and strips exactly that much. So the
literal stays aligned with your code and the string contains no leading spaces. MOVING THE CLOSING
DELIMITER CHANGES THE CONTENT, which is the one thing to remember.""",

"""3. THE MECHANISM — what each one actually compiles to

`var`: PURE COMPILE-TIME. The class file contains the inferred type; there is no runtime component and
no reflection difference. Two subtleties:

    IT INFERS THE MOST SPECIFIC TYPE, INCLUDING TYPES YOU CANNOT WRITE. `var x = new Object() { int n =
    1; };` gives `x` an anonymous class type, so `x.n` compiles — something impossible to declare
    explicitly. Likewise it can infer intersection types.
    IT NEEDS AN INITIALISER AND CANNOT BE `null`. `var x;` and `var x = null;` do not compile.
    `var list = new ArrayList<>()` infers `ArrayList<Object>`, because there is nothing to infer from —
    the diamond and `var` cancel each other out.

`record Point(int x, int y) { }` EXPANDS TO roughly:

    final class Point extends java.lang.Record {
        private final int x, y;
        Point(int x, int y) { this.x = x; this.y = y; }   // the CANONICAL constructor
        public int x() { return x; }                       // x(), NOT getX()
        public int y() { return y; }
        public boolean equals(Object o) { ... component-wise ... }
        public int hashCode()           { ... component-wise ... }
        public String toString()        { "Point[x=1, y=2]" }
    }

    IMPLICITLY `final`, extends `Record` so it cannot extend anything else, and CAN implement
    interfaces. The generated members are all overridable if you want different behaviour.

    THE COMPACT CONSTRUCTOR is the piece worth knowing:
        record Range(int lo, int hi) {
            Range {                                        // no parameter list, no assignment
                if (lo > hi) throw new IllegalArgumentException();
                hi = Math.min(hi, MAX);                    // you may REASSIGN the parameter
            }                                              // the field assignment is implicit
        }
    Validation and normalisation live here, and the field assignments happen after your code runs.

    WHAT RECORDS DO NOT GIVE YOU: DEFENSIVE COPIES. `record Team(String name, List<Player> players)` is
    SHALLOWLY immutable — the reference cannot change, the list's contents can. If you want deep
    immutability, copy in the compact constructor and copy out of the accessor.

`sealed`: the class file gets a `PermittedSubclasses` attribute, and the JVM enforces it at load time —
this is not just a compiler check. Every permitted subtype must itself be declared `final`, `sealed`, or
explicitly `non-sealed` (the only hyphenated keyword in Java), which forces the author to make a
deliberate decision about whether the hierarchy stays closed. Permitted subtypes must be in the same
module, or the same package for the unnamed module.

PATTERN MATCHING FOR `switch` (Java 21) brings four things together:

    TYPE PATTERNS         case Circle c -> c.radius()
    RECORD PATTERNS       case Circle(double r) -> r          ← deconstruction, nestable
    GUARDS                case Circle c when c.radius() > 10 -> ...
    NULL HANDLING         `case null` is now writable; without it, a switch on a reference still throws
                          NullPointerException, preserving the old behaviour.
    EXHAUSTIVENESS        over a sealed type, no `default` is needed — and omitting `default` is
                          BETTER, because adding a subtype then breaks the build instead of silently
                          falling through.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `var list = new ArrayList<>();` INFERS `ArrayList<Object>`. The diamond has nothing to infer
from and `var` has nothing to give it. Write one of the two types.

CASE 2 — `var x = null;` AND `var x;` DO NOT COMPILE. There is nothing to infer.

CASE 3 — `var` HIDING THE TYPE. `var r = svc.process(x)` tells the reader nothing. Use it when the
right-hand side is a constructor or an obvious factory, not when it is an arbitrary call.

CASE 4 — `var` INFERRING A NARROWER TYPE THAN YOU WANTED. `var list = new ArrayList<String>()` gives
`ArrayList`, not `List`, so a later reassignment to a `LinkedList` fails to compile.

CASE 5 — A RECORD HOLDING A MUTABLE COLLECTION. Shallowly immutable only. Copy in the compact
constructor and on the way out if you need real immutability.

CASE 6 — RECORD ACCESSORS ARE `x()`, NOT `getX()`. Frameworks expecting JavaBean conventions may not
bind. Jackson supports records; older reflection-based tools may not.

CASE 7 — A RECORD WITH AN ARRAY COMPONENT. `equals` and `hashCode` use the ARRAY's identity semantics,
so two records with equal array contents are not equal. Override both, or use a `List`.

CASE 8 — RECORDS CANNOT EXTEND A CLASS. They already extend `Record`. If a shared supertype is needed
it must be an interface — which is exactly why sealed INTERFACES are the usual pairing.

CASE 9 — A SEALED TYPE'S PERMITTED SUBTYPES MUST BE IN THE SAME MODULE OR PACKAGE. You cannot seal
across a library boundary, and that is deliberate.

CASE 10 — FORGETTING `final`, `sealed` OR `non-sealed` ON A PERMITTED SUBTYPE. A compile error, and a
useful one: it forces a decision about whether the hierarchy stays closed.

CASE 11 — ADDING `default` TO AN EXHAUSTIVE SWITCH OVER A SEALED TYPE. It compiles, and it THROWS AWAY
THE ENTIRE BENEFIT: adding a subtype now falls silently into `default` instead of breaking the build.

CASE 12 — `switch` ON A REFERENCE THAT IS NULL. Still throws `NullPointerException` unless you write
`case null`. Preserved for compatibility, and surprising in new code.

CASE 13 — TEXT BLOCK INDENTATION DECIDED BY THE CLOSING DELIMITER. Its position counts in the minimum,
so moving the closing delimiter left or right changes the string's content.

CASE 14 — TEXT BLOCKS STRIP TRAILING SPACES on every line. Use a backslash-s escape to keep one, and a
trailing backslash to join two lines without a newline between them.""",

"""5. THE ALTERNATIVES — what these replaced, and what they did not

`var` REPLACED nothing functionally — it is pure ergonomics. THE ALTERNATIVE IS WRITING THE TYPE, and
that remains right whenever the type is not obvious from the right-hand side. Lombok's `val` did this
first; `var` made it a language feature with no annotation processor.

`record` REPLACED:
    THE IDE-GENERATED DATA CLASS — sixty lines that drift out of sync the moment a field is added.
    LOMBOK `@Data` / `@Value` — an annotation processor rewriting your class, with the IDE and build
    tooling needing to know about it. Records are a language feature, so nothing extra is required.
    THIRD-PARTY TUPLES — `Pair` and `Triple` from Apache Commons and friends. A LOCAL RECORD inside a
    method now expresses "a name and a count, just for this stream pipeline" with real field names,
    which a `Pair` never could.

    WHAT RECORDS DO NOT REPLACE: entities with identity and a lifecycle (a JPA `@Entity` needs a
    no-arg constructor and mutable fields), classes with behaviour and invariants beyond validation,
    and anything needing inheritance.

`sealed` + PATTERN MATCHING REPLACED:
    A CHAIN OF `instanceof` WITH CASTS — verbose, and nothing checks that you covered everything.
    THE VISITOR PATTERN — the traditional answer for double dispatch over a closed hierarchy, and a
    lot of machinery: an `accept` method on every type, a visitor interface, and a new visitor class
    per operation. Sealed types plus pattern matching give the same exhaustiveness with none of it.
    AN ENUM WITH A `switch`, when the alternatives carry different DATA rather than being simple
    constants.

    WHAT THEY DO NOT REPLACE: ordinary polymorphism. If the behaviour belongs to the type and the set is
    OPEN — plugins, extensions, third-party implementations — an interface with an abstract method is
    still right. USE SEALED TYPES WHEN THE SET IS GENUINELY CLOSED AND THE OPERATIONS KEEP GROWING; use
    virtual dispatch when the set keeps growing and the operations are fixed. That trade-off has a name:
    the expression problem.

TEXT BLOCKS REPLACED string concatenation with `\\n`, and external `.sql` resource files loaded for
readability rather than for reuse.

WHAT STILL IS NOT THERE, and is worth naming: no operator overloading, no named or default parameters
(so the builder pattern survives), no non-nullable types (`Optional` is a library, not a type system
feature), and NO VALUE TYPES YET — Project Valhalla, which would let a record be flattened inline with
no header and no indirection, is still in progress.

WHAT TO SAY: "`var` where the right-hand side already states the type. Records for any data carrier —
they replace the sixty-line class and the Lombok dependency both. And sealed interfaces plus records plus
pattern matching when I have a closed set of alternatives, because that is the only way to get
EXHAUSTIVENESS CHECKING: add a subtype and every incomplete switch fails to compile, which virtual
dispatch never gave me."

""",

"""6. HOW TO ADOPT THEM — numbered steps

STEP 1 — USE `var` WHEN THE RIGHT-HAND SIDE NAMES THE TYPE. Constructors and obvious factories, yes.
Arbitrary method calls, no.

STEP 2 — DO NOT COMBINE `var` WITH THE DIAMOND. `var list = new ArrayList<>()` infers
`ArrayList<Object>`.

STEP 3 — MAKE EVERY DATA CARRIER A RECORD. DTOs, value objects, map keys, method return tuples, events.

STEP 4 — PUT VALIDATION IN THE COMPACT CONSTRUCTOR. It runs before the fields are assigned and you may
reassign the parameters to normalise.

STEP 5 — DEFENSIVELY COPY MUTABLE COMPONENTS, in AND out. A record is only shallowly immutable, and the
language will not do this for you.

STEP 6 — NEVER PUT AN ARRAY IN A RECORD without overriding `equals` and `hashCode`. Array identity
semantics silently break value equality.

STEP 7 — USE A LOCAL RECORD INSIDE A METHOD instead of a `Pair`. Real field names, zero API surface.

STEP 8 — SEAL A HIERARCHY WHEN THE SET OF SUBTYPES IS GENUINELY CLOSED and you expect to add operations
over it.

STEP 9 — DO NOT WRITE `default` IN A SWITCH OVER A SEALED TYPE. Omitting it is what makes adding a
subtype a compile error rather than a silent fallthrough.

STEP 10 — HANDLE `case null` EXPLICITLY where null is possible. Otherwise the switch throws, preserving
pre-21 behaviour.

STEP 11 — USE RECORD DECONSTRUCTION PATTERNS rather than calling accessors inside the case body. It
reads as the shape of the data.

STEP 12 — WATCH THE CLOSING DELIMITER OF A TEXT BLOCK. Its indentation participates in the strip, so
moving it changes the string.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Java 8 is the last release most people learned properly, and since then the big ones are 11, 17 and 21.
The changes split into one thing that removes typing and three that together add a genuinely new way to
model data.

`var` is local variable type inference. Write `var map = new HashMap<String, List<Order>>()` instead of
saying the type twice. It is NOT dynamic typing — the type is fixed at compile time and is exactly what
it would have been; `var x = "hello"` makes x a String forever and `x = 5` is a compile error. It's
confined to locals with an initialiser, for-loop variables and try-with-resources — never fields,
parameters or return types, because those are API surface and inference there would make a caller's
contract depend on a method body. My rule is: use it when the RIGHT-hand side already tells you the
type. `var list = new ArrayList<String>()` is obvious; `var result = process(input)` costs the reader
something.

Records give you the constructor, accessors, equals, hashCode and toString from a one-line header. The
real argument for them isn't brevity — it's that a hand-written data class says the same thing six times
and any of them can drift. Add a field, forget to add it to equals, and you have a silent bug a HashSet
will eventually reveal. A record declares the state ONCE and derives everything else. The language calls
it a "transparent carrier for its data", and that transparency is exactly what lets pattern matching
deconstruct it later — which is why records and patterns arrived together.

The thing I'd emphasise is that sealed types, records and pattern matching are ONE feature. Sealed types
say what the alternatives ARE, records say what each alternative CARRIES, and pattern matching takes
them apart and forces you to handle every case. Together they're algebraic data types, which functional
languages have had for forty years.

And the payoff is EXHAUSTIVENESS, which polymorphism never gave you. Traditional advice is put behaviour
in the subclasses and use dynamic dispatch — that works when the behaviour belongs to the type. It fails
when you need to add an OPERATION over a fixed set of shapes, and then the alternative was a chain of
instanceof that nothing checks. With a sealed hierarchy the compiler knows the full list, so a switch
can be checked for completeness: add a new subtype and every incomplete switch in the codebase fails to
compile.

Which gives one rule I'd state carefully: DON'T write `default` in a switch over a sealed type. It
compiles, and it throws away the entire benefit — adding a subtype then falls silently into default
instead of breaking the build.

Two practical cautions on records. They're only SHALLOWLY immutable, so a record holding a List has a
list whose contents anyone can change; copy in the compact constructor and out of the accessor if you
need real immutability. And an array component makes equals use array IDENTITY, so two records with
identical contents aren't equal — that one bites silently.

Text blocks are smaller: multi-line literals where Java computes the minimum indentation across all
non-blank lines AND the closing delimiter, and strips that much. The thing to remember is that moving
the closing delimiter changes the string's content.'""",

"""8. THE CODE, LINE BY LINE

    // ── var: inference, not dynamic typing ──────────────────────────────
    var map = new HashMap<String, List<Order>>();   // the type is written ONCE
    var x = "hello";
    // x = 5;                          ✗ COMPILE ERROR — x is a String, permanently
    // var y;                          ✗ nothing to infer from
    // var z = null;                   ✗ same
    var list = new ArrayList<>();      // ← infers ArrayList<OBJECT>. The diamond has
    //                                    nothing to infer from and var has nothing
    //                                    to give it. Write one of the two types.
    var o = new Object() { int n = 1; };
    System.out.println(o.n);           // ← compiles! var inferred the ANONYMOUS CLASS
    //                                    type, which you cannot write down yourself.

    // ── record: state declared once, everything else derived ────────────
    record Point(int x, int y) { }
    // expands to a FINAL class extending java.lang.Record, with:
    //   Point(int x, int y)          the CANONICAL constructor
    //   int x()  int y()             accessors — x(), NOT getX()
    //   equals / hashCode            COMPONENT-WISE
    //   toString                     "Point[x=1, y=2]"

    record Range(int lo, int hi) {
        Range {                        // ← THE COMPACT CONSTRUCTOR: no parameter list
            if (lo > hi) throw new IllegalArgumentException(lo + " > " + hi);
            hi = Math.min(hi, MAX);    // you may REASSIGN a parameter to normalise
        }                              // the field assignments happen AFTER this runs
    }

    // ── THE TWO RECORD TRAPS ────────────────────────────────────────────
    record Team(String name, List<Player> players) { }
    var t = new Team("A", myList);
    myList.add(newPlayer);             // ← THE RECORD JUST CHANGED. Records are only
    //                                    SHALLOWLY immutable: the reference is final,
    //                                    the contents are not.
    record Team(String name, List<Player> players) {
        Team { players = List.copyOf(players); }    // ← copy IN
    }

    record Key(byte[] bytes) { }
    new Key(new byte[]{1}).equals(new Key(new byte[]{1}));   // FALSE
    //   equals uses the ARRAY's identity semantics. Use a List, or override both.

    // ── sealed + records + patterns: ONE feature ────────────────────────
    sealed interface Shape permits Circle, Square, Triangle { }
    record Circle(double radius)              implements Shape { }
    record Square(double side)                implements Shape { }
    record Triangle(double base, double h)    implements Shape { }
    // Every permitted subtype must be final, sealed, or non-sealed — which forces a
    // deliberate decision. Records are implicitly final, so they satisfy it for free.

    double area(Shape s) {
        return switch (s) {
            case Circle(double r)         -> Math.PI * r * r;
    //           ^^^^^^^^^^^^^^^^ a RECORD DECONSTRUCTION PATTERN — the component is
    //           bound as part of the match. Nestable.
            case Square(double side)      -> side * side;
            case Triangle(double b, double h) when b > 0 -> 0.5 * b * h;
    //                                        ^^^^ a GUARD
            case Triangle t               -> 0;
        };
    //  NO `default`. The compiler knows the full list, so it CHECKS EXHAUSTIVENESS.
    //  Add `record Hexagon(...) implements Shape` and THIS METHOD STOPS COMPILING —
    //  which is the entire point, and something virtual dispatch never gave you.
    }

    // ── THE ONE LINE THAT THROWS THE BENEFIT AWAY ───────────────────────
    switch (s) {
        case Circle c -> ...;
        default       -> 0;            // ← compiles, and now adding a subtype falls
    }                                  //   SILENTLY into default instead of breaking
    //                                     the build. Do not write this.

    // ── null in a switch ────────────────────────────────────────────────
    switch (s) {
        case null     -> "nothing";    // ← Java 21 lets you write this
        case Circle c -> "round";
        default       -> "other";
    }
    // WITHOUT `case null`, a switch on a reference STILL throws NullPointerException —
    // preserved from before, and surprising in new code.

    // ── text blocks: the indentation algorithm is the feature ───────────
    //   String sql = <TQ>                    ← <TQ> is three double-quote chars
    //           SELECT id, name
    //           FROM users
    //           WHERE active = true
    //           <TQ>;
    //
    // Java takes the MINIMUM indentation across all non-blank lines AND the closing
    // delimiter, and strips exactly that much from every line. So the literal stays
    // aligned with your code and the string contains no leading spaces.
    //
    // MOVING THE CLOSING DELIMITER CHANGES THE STRING: put it flush left and nothing
    // is stripped, so every line keeps its 10 spaces of indentation.
    //
    // Trailing spaces are stripped from every line: use a backslash-s escape to keep
    // one, and a trailing backslash to join two lines with no newline between them.""",

"""9. THE TRACE — the same model, before and after

THE PROBLEM: represent a shape, compute its area, and add a `describe` operation later.

    BEFORE — ABSTRACT CLASS AND VIRTUAL DISPATCH
    ---------------------------------------------------------------------------------
    abstract class Shape { abstract double area(); }
    class Circle extends Shape { ... 40 lines: fields, constructor, getters,
                                  equals, hashCode, toString ... }
    ×3 subtypes                                            ≈ 130 lines
    adding `describe()`                                    edit ALL FOUR classes
    forgetting one subtype                                 IMPOSSIBLE — abstract
                                                            method, compile error ✓
    an operation that belongs elsewhere (rendering,        cannot be added without
    serialisation, pricing)                                 touching every class
    ---------------------------------------------------------------------------------
    VIRTUAL DISPATCH IS EXCELLENT AT ADDING TYPES and poor at adding operations. Every new operation
    edits every class, and operations that belong to another module cannot live here at all.

    BEFORE — instanceof CHAINS, the usual workaround
    ---------------------------------------------------------------------------------
    if (s instanceof Circle) { Circle c = (Circle) s; ... }
    else if (s instanceof Square) { ... }
    adding a subtype                                       NOTHING BREAKS. The chain
                                                            silently falls through to
                                                            the else, forever.
    ---------------------------------------------------------------------------------
    THIS IS THE FAILURE MODE THE FEATURE EXISTS TO REMOVE.

    AFTER — SEALED + RECORDS + PATTERNS
    ---------------------------------------------------------------------------------
    sealed interface Shape permits Circle, Square, Triangle { }
    record Circle(double radius) implements Shape { }
    ×3 subtypes                                            4 lines total
    equals / hashCode / toString                           generated, component-wise,
                                                            and cannot drift
    adding `describe()`                                    ONE new method, anywhere,
                                                            even in another class
    adding a subtype                                       EVERY incomplete switch in
                                                            the codebase FAILS TO
                                                            COMPILE ✓
    ---------------------------------------------------------------------------------
    130 LINES TO 4, and — more importantly — the compile-time guarantee moved. Before, forgetting a
    TYPE was impossible and forgetting an OPERATION site was easy. Now both are checked.

NOW TRACE WHAT ADDING `Hexagon` DOES, in each design:

    design                        what the compiler says
    ---------------------------------------------------------------------------------
    abstract class + virtual      "Hexagon is not abstract and does not override
                                   area()" — you are told exactly once, at the class.
    instanceof chain              NOTHING. Every chain silently returns its else
                                   branch. The bug ships.
    sealed + exhaustive switch    every switch over Shape that does not handle Hexagon
                                   fails to compile, listing each one. You are told
                                   about EVERY SITE.
    sealed + switch with default  NOTHING. `default` swallowed it. Identical to the
                                   instanceof chain — which is why that one line
                                   matters so much.
    ---------------------------------------------------------------------------------
    ROWS 3 AND 4 DIFFER BY ONE `default` CLAUSE and produce opposite outcomes: a complete list of every
    place needing attention, or silence.

AND THE `var` TRACE — what is actually inferred:

    written                                      inferred type
    ---------------------------------------------------------------------------------
    var s = "hi"                                 String
    var list = new ArrayList<String>()           ArrayList<String>   ← not List
    var list = new ArrayList<>()                 ArrayList<Object>   ← the trap
    var o = new Object() { int n = 1; }          an ANONYMOUS class type — so `o.n`
                                                 compiles, and no explicit declaration
                                                 could have expressed it
    var i = 1                                    int (not Integer)
    var d = 1.0                                  double
    ---------------------------------------------------------------------------------
    ROW 2 IS THE ONE THAT SURPRISES: `var` infers the CONCRETE type, so a later reassignment to a
    `LinkedList` will not compile. That is usually fine for a local and occasionally not what you meant.

WHAT PRODUCED WHAT:
    SEALING              produced the compiler knowing the full list — and therefore everything else.
    RECORDS' TRANSPARENCY produced deconstruction patterns, which is why the two features shipped
                         together.
    OMITTING `default`   produced the build failure that makes the guarantee real.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `var`: compile-time only. No runtime cost, no reflection difference, no bytecode difference.
    `record`: a `final` class extending `java.lang.Record`. Component-wise `equals`/`hashCode`,
    accessors named `x()`. Shallowly immutable.
    `sealed`: a `PermittedSubclasses` class-file attribute, enforced by the JVM at load time, not only
    by the compiler. Permitted subtypes must be `final`, `sealed` or `non-sealed`, in the same module
    or package.
    Pattern-matching `switch`: type patterns, record deconstruction, `when` guards, `case null`, and
    EXHAUSTIVENESS over sealed types with no `default`.
    Text blocks: minimum indentation across non-blank lines AND the closing delimiter is stripped;
    trailing spaces removed.

THE #1 MISTAKE: writing `default` in a switch over a sealed type. It compiles and it discards the
exhaustiveness guarantee that was the entire reason to seal.

THE #2 MISTAKE: `var list = new ArrayList<>()`. Infers `ArrayList<Object>`.

THE #3 MISTAKE: `var` where the right-hand side is an arbitrary method call. The reader now has to go
and look.

THE #4 MISTAKE: assuming a record is deeply immutable. A mutable component is mutable; copy in and out.

THE #5 MISTAKE: an array component in a record. `equals` uses array identity, so equal contents are not
equal records.

THE #6 MISTAKE: expecting `getX()` on a record. The accessor is `x()`, which some JavaBean-based tooling
does not bind.

THE #7 MISTAKE: reaching for a record where an entity belongs. JPA needs a no-arg constructor and
mutable fields; a record has neither.

THE #8 MISTAKE: sealing an OPEN set. If third parties should be able to implement it, an ordinary
interface is right — sealing is for closed sets where operations keep growing.

THE #9 MISTAKE: forgetting `case null`. A switch on a reference still throws
`NullPointerException` without it.

THE #10 MISTAKE: moving a text block's closing delimiter without realising it changes the string. Its
indentation participates in the strip.

THE #11 MISTAKE: treating these as four unrelated conveniences. Records, sealed types and pattern
matching are ONE feature, and using records without sealing loses most of the point.

ONE-SENTENCE TAKEAWAY: `var` is compile-time inference for locals only and belongs where the right-hand
side already names the type, while records, sealed types and pattern matching are a SINGLE feature —
sealed types declare what the alternatives are, records declare what each carries (transparently, which
is precisely what makes deconstruction patterns possible), and `switch` takes them apart with the
compiler checking EXHAUSTIVENESS, so adding a subtype breaks the build at every site that needs
attention instead of silently falling through an `instanceof` chain; that guarantee is the thing virtual
dispatch never offered, it is destroyed by a single `default` clause, and the two cautions that bite
silently are that records are only shallowly immutable and that an array component makes `equals` use
identity.""",
]


DEEP["Class initialization order — static blocks, instance blocks, constructors"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two separate ceremonies, run at different times

There are TWO initialisations in Java and people mix them up constantly.

    CLASS INITIALISATION happens ONCE, ever, the first time the class is actually USED. It runs the
    static field initialisers and the static blocks, in the order they appear in the source. The JVM
    calls this `<clinit>`.

    INSTANCE INITIALISATION happens EVERY TIME you write `new`. It runs the superclass's instance
    initialisation first, then this class's instance field initialisers and instance blocks in source
    order, then the constructor body. The JVM calls this `<init>`.

    SO THE FULL ORDER FOR `new Child()` — with nothing yet loaded — IS:

        1. Parent's static initialisers            ← once, ever
        2. Child's static initialisers             ← once, ever
        3. Parent's instance initialisers + blocks ┐
        4. Parent's constructor body               ┘ every `new`
        5. Child's instance initialisers + blocks  ┐
        6. Child's constructor body                ┘ every `new`

    ALL STATICS BEFORE ANY INSTANCE, AND ALL PARENT BEFORE ANY CHILD. That is the whole ordering rule,
    and almost every surprising behaviour is a consequence of step 4 happening before step 5.

WHY IT MATTERS BEYOND TRIVIA: the gap between steps 4 and 5 is where a constructor calling an
overridable method sees the subclass's fields as null. And "the first time the class is USED" hides two
genuinely load-bearing details — one that produces a deployment bug where changing a constant has no
effect, and one that produces the most confusing error message in Java, where a class that is
demonstrably present reports `NoClassDefFoundError`.

THE EVERYDAY VERSION: opening a shop. Unlocking the building, turning on the power and setting the tills
up happens once, on the first day anyone comes in — that is class initialisation. Serving each customer
happens every time — that is instance initialisation. And the building is always opened before the
first customer is served, never the other way round.

TERMS AS THEY APPEAR:
- `<clinit>`: the compiler-generated method holding all static initialisation.
- `<init>`: the generated method holding instance initialisation plus a constructor body.
- INITIALISATION vs LOADING: a class can be loaded and linked long before it is initialised.""",

"""2. THE INTUITION — what "first used" actually means, and the two surprises hiding in it

CLASS INITIALISATION IS LAZY AND PRECISELY SPECIFIED. It is triggered by:

    creating an instance (`new`);
    calling a static METHOD;
    reading or writing a NON-CONSTANT static field;
    reflection — `Class.forName(name)` with the default `initialize = true`;
    initialising a SUBCLASS (which forces the superclass first).

IT IS NOT TRIGGERED BY:

    declaring a variable of the type;
    creating an ARRAY of the type — `new Foo[10]` initialises nothing;
    `Class.forName(name, false, loader)`;
    accessing a COMPILE-TIME CONSTANT.

THAT LAST ONE IS THE FIRST SURPRISE, AND IT IS A REAL DEPLOYMENT BUG:

    `static final int MAX = 100;` — a `static final` primitive or String initialised with a constant
    expression is a COMPILE-TIME CONSTANT. Its value is COPIED INTO THE CALLER'S CLASS FILE at compile
    time. Reading it does not touch the declaring class at all, and its static block never runs.

    NOW CHANGE `MAX` TO 200 AND REBUILD ONLY THE LIBRARY. Every already-compiled caller still contains
    the literal 100. The library says 200, the application behaves as 100, and nothing anywhere is
    wrong — the old value was baked in. THE FIX IS A FULL REBUILD, and knowing this is the difference
    between five minutes and an afternoon.

    (`static final Foo X = new Foo();` is NOT a constant — only primitives and Strings with constant
    initialisers are — so reading it does initialise the class.)

THE SECOND SURPRISE IS WHAT HAPPENS WHEN A STATIC INITIALISER THROWS:

    The exception is wrapped in `ExceptionInInitializerError`, and — this is the part people do not
    know — THE CLASS IS PERMANENTLY MARKED ERRONEOUS. Initialisation is attempted exactly once. Every
    subsequent use of that class, for the life of the JVM, throws `NoClassDefFoundError: Could not
    initialize class Foo`.

    SO THE SECOND ERROR MESSAGE SAYS THE CLASS CANNOT BE FOUND, AND THE CLASS IS RIGHT THERE. People
    spend hours on classpath theories. The real cause is a single `ExceptionInInitializerError` that
    happened earlier — often in a different thread, often already swallowed by a catch block. ALWAYS
    LOOK FOR THE FIRST OCCURRENCE IN THE LOG, NOT THE ONE YOU ARE STARING AT.

AND THE THIRD THING THAT MAKES `<clinit>` SPECIAL: THE JVM GUARANTEES IT RUNS EXACTLY ONCE AND IS
THREAD-SAFE. It takes a per-class initialisation lock, so concurrent threads block until the first one
finishes. That guarantee — free, built in, no synchronisation to write — is what the
INITIALIZATION-ON-DEMAND HOLDER idiom exploits to get a lazy thread-safe singleton with no locking in
your code at all.""",

"""3. THE MECHANISM — what the compiler generates, and the two orders

`<clinit>`, THE CLASS INITIALISER. The compiler collects EVERY static field initialiser and EVERY static
block, in SOURCE ORDER, into one synthetic method:

    class Config {
        static int a = 1;                 ┐
        static { a = 2; b = 5; }          │  all of this becomes one <clinit>,
        static int b = 3;                 │  executed top to bottom
        static { System.out.println(b); } ┘  → prints 3, not 5
    }

    READ THAT OUTPUT AGAIN. The block sets `b = 5`, then the DECLARATION `static int b = 3` runs after
    it and overwrites. Source order is the only order, and a declaration that appears later wins over a
    block that appears earlier. THIS IS WHY MIXING BLOCKS AND INITIALISERS IS DISCOURAGED.

    A static block MAY ASSIGN a field declared later (as above) but may NOT READ it by simple name —
    that is an "illegal forward reference" and a compile error. The asymmetry is deliberate: writing is
    harmless, reading would observe a default value that looks like a bug.

`<init>`, THE INSTANCE INITIALISER. For every constructor the compiler emits, in this order:

    1. the `super(...)` call (implicit `super()` if you wrote neither `super` nor `this`)
    2. ALL instance field initialisers and instance blocks, in SOURCE ORDER
    3. the constructor's own body

    STEP 2 IS THE ONE PEOPLE FORGET. Field initialisers do not run "with the field"; they run
    immediately after `super()` returns and BEFORE your constructor body. If a constructor delegates
    with `this(...)`, step 2 runs only in the constructor that eventually calls `super` — so field
    initialisers run exactly once per object, not once per constructor in the chain.

THE CONSEQUENCE THAT CAUSES REAL BUGS — a superclass constructor calling an overridable method:

    Parent's constructor runs at step 4 of the overall order. The Child's field initialisers are step 5.
    So if Parent's constructor calls a method the Child overrides, THE OVERRIDE RUNS WITH EVERY CHILD
    FIELD STILL AT ITS DEFAULT — null, 0, false — including `final` fields. Dynamic dispatch is working
    perfectly; the object simply does not exist yet from the Child's point of view.

THE INITIALIZATION-ON-DEMAND HOLDER IDIOM, which turns the `<clinit>` guarantee into a feature:

    class Singleton {
        private Singleton() { }
        private static class Holder { static final Singleton INSTANCE = new Singleton(); }
        static Singleton get() { return Holder.INSTANCE; }
    }

    `Holder` is not initialised until `get()` touches `Holder.INSTANCE`. At that moment the JVM's
    per-class lock guarantees `new Singleton()` runs exactly once, even under concurrent access. LAZY,
    THREAD-SAFE, AND NOT ONE LINE OF SYNCHRONISATION — because the JVM already had to solve this
    problem for `<clinit>`.

ENUMS use the same machinery: the constants are created in the enum's `<clinit>`, which is why
`enum Singleton { INSTANCE }` is thread-safe, serialization-safe and reflection-safe for free.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — A `static final` PRIMITIVE OR STRING CONSTANT CHANGED IN A LIBRARY. Callers keep the old value
baked into their class files until they are recompiled. Nothing errors; the behaviour is just stale.

CASE 2 — `ExceptionInInitializerError`, THEN `NoClassDefFoundError` FOREVER. Initialisation is attempted
once; failure marks the class erroneous for the life of the JVM. The second message is the one you see
and it names the wrong problem.

CASE 3 — A STATIC BLOCK OVERWRITTEN BY A LATER DECLARATION. Source order is the only order; a block
above a field initialiser loses.

CASE 4 — ILLEGAL FORWARD REFERENCE. A static block may assign a field declared later but may not read
it by simple name. Compile error.

CASE 5 — A SUPERCLASS CONSTRUCTOR CALLING AN OVERRIDABLE METHOD. The override runs before the subclass's
field initialisers, so it sees nulls and zeros — including in `final` fields.

CASE 6 — CLASS INITIALISATION DEADLOCK. Two classes whose static initialisers reference each other,
touched from two threads simultaneously. Each holds one class's init lock and wants the other's. The
thread dump shows threads blocked in `<clinit>` and `jstack` will not call it a deadlock, because the
locks are internal to the JVM.

CASE 7 — CIRCULAR STATIC INITIALISATION IN ONE THREAD. `A.<clinit>` reads `B.X`, and `B.<clinit>` reads
`A.Y`. No deadlock — the JVM sees the same thread already initialising `A` and lets it proceed — so one
of the values is simply the DEFAULT. Silent, and it produces a null or a zero that no code explains.

CASE 8 — `new Foo[10]` DOES NOT INITIALISE `Foo`. Array creation is not a trigger, so a static block
you expected to have run has not.

CASE 9 — `Class.forName(name, false, loader)` DOES NOT INITIALISE either. The two-argument versus
three-argument difference matters when a driver registers itself in a static block.

CASE 10 — EXPENSIVE WORK IN A STATIC BLOCK. It runs while holding the class init lock, on whichever
thread touched the class first — often an unlucky request thread. Loading a 50 MB file there stalls
everything that needs the class.

CASE 11 — A STATIC BLOCK WITH SIDE EFFECTS OUTSIDE THE CLASS. Registering with a global registry from
`<clinit>` means the registration happens only if something else touched the class first, which is not
a property you control.

CASE 12 — CONSTRUCTOR CHAINING WITH `this(...)`. Field initialisers run ONCE, in the constructor that
reaches `super`, not in each constructor in the chain.

CASE 13 — INSTANCE INITIALISER BLOCKS IN ANONYMOUS CLASSES (the "double brace" idiom,
`new ArrayList<>() {{ add("a"); }}`). It creates a SUBCLASS holding a `this$0` reference to the
enclosing instance, so it leaks and it breaks serialization.""",

"""5. THE ALTERNATIVES — how to avoid needing to know the order

CONSTRUCTOR PARAMETERS OVER INITIALISATION CEREMONY. If every field is assigned in the constructor from
arguments, there is no order to reason about. Records take this to its conclusion.

STATIC FACTORY METHODS instead of static blocks that build complicated state. A named method is
testable, can fail with a normal exception rather than an `ExceptionInInitializerError`, and runs when
you call it rather than when someone happens to touch the class.

THE INITIALIZATION-ON-DEMAND HOLDER for lazy singletons — lazy, thread-safe, lock-free, and it works
because `<clinit>` already guarantees it.

`enum Singleton { INSTANCE; }` — Effective Java's preferred singleton. Thread-safe, serialization-safe,
and immune to the reflection attack that breaks a private constructor.

EXPLICIT LIFECYCLE over static initialisation for anything with real setup: a dependency injection
container, a `@PostConstruct`, an explicit `init()` called from `main`. YOU CONTROL WHEN IT RUNS, WHAT
THREAD IT RUNS ON, AND WHAT HAPPENS WHEN IT FAILS — none of which is true of a static block.

`final` FIELDS ASSIGNED EXACTLY ONCE, in the declaration or in every constructor. This removes the "did
it get initialised" question entirely and gives you the JMM's final-field freeze guarantee for safe
publication.

FOR CONSTANTS THAT MAY CHANGE: avoid `static final` primitives and Strings in a library's public API if
callers compile against it separately, because inlining makes them unchangeable without a full rebuild.
A static ACCESSOR METHOD returning the value is not inlined and stays correct.

`Objects.requireNonNull` IN THE CONSTRUCTOR to fail loudly at construction rather than with a mysterious
NPE later.

DO NOT CALL OVERRIDABLE METHODS FROM A CONSTRUCTOR. If subclasses must contribute, take the value as a
constructor parameter, or use a static factory that constructs then configures.

WHAT TO SAY: "Statics before instance, parent before child, and within each, source order. I would avoid
depending on it: constructor parameters or a record for state, a static factory or an explicit lifecycle
instead of static blocks, and the holder idiom for a lazy singleton — which works precisely because the
JVM already guarantees `<clinit>` runs once under a class lock."

""",

"""6. HOW TO REASON ABOUT IT — numbered steps

STEP 1 — REMEMBER THE SIX-STEP ORDER: parent statics, child statics, parent instance initialisers,
parent constructor, child instance initialisers, child constructor.

STEP 2 — WITHIN A CATEGORY, IT IS SOURCE ORDER. A static block above a field declaration runs before
that declaration's initialiser, and can be overwritten by it.

STEP 3 — REMEMBER FIELD INITIALISERS RUN AFTER `super()` AND BEFORE THE CONSTRUCTOR BODY. Not "with the
field".

STEP 4 — NEVER CALL AN OVERRIDABLE METHOD FROM A CONSTRUCTOR. The override sees the subclass's fields at
their defaults.

STEP 5 — KEEP STATIC BLOCKS TINY AND INFALLIBLE. They run under a class lock, on an arbitrary thread,
and a failure poisons the class for the life of the JVM.

STEP 6 — WHEN YOU SEE `NoClassDefFoundError: Could not initialize class X`, SEARCH THE LOG FOR THE
FIRST `ExceptionInInitializerError`. That is the real error; this one is its echo.

STEP 7 — AVOID PUBLIC `static final` PRIMITIVE AND STRING CONSTANTS IN A LIBRARY whose callers compile
separately. They are inlined and cannot be changed without recompiling everyone.

STEP 8 — USE THE HOLDER IDIOM FOR LAZY SINGLETONS, or an enum for eager ones. Not double-checked
locking.

STEP 9 — DO NOT LET TWO CLASSES' STATIC INITIALISERS REFERENCE EACH OTHER. One thread gives you a silent
default value; two threads give you a deadlock `jstack` cannot name.

STEP 10 — REMEMBER `new Foo[10]` AND `Class.forName(n, false, cl)` DO NOT INITIALISE. If a static block
must run, touch a non-constant static member.

STEP 11 — PREFER AN EXPLICIT `init()` OR A DI CONTAINER for anything with real setup, so you control the
timing, the thread and the failure mode.

STEP 12 — AVOID THE DOUBLE-BRACE INITIALISATION IDIOM. It creates an anonymous subclass with a `this$0`
back-reference, so it leaks and breaks serialization.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'There are two initialisations and people mix them up. CLASS initialisation happens once ever, the first
time the class is actually used — it runs the static field initialisers and static blocks in source
order, and the JVM calls that <clinit>. INSTANCE initialisation happens on every `new` — superclass
first, then this class's instance field initialisers and blocks in source order, then the constructor
body, and that's <init>.

So for `new Child()` with nothing loaded yet: Parent statics, Child statics, Parent instance
initialisers, Parent constructor, Child instance initialisers, Child constructor. All statics before any
instance, all parent before any child. That's the whole rule.

The bit people forget is that field initialisers don't run "with the field" — they run right after
super() returns and BEFORE your constructor body. Which is what makes the classic bug: if a superclass
constructor calls a method the subclass overrides, the override runs before the subclass's field
initialisers, so it sees nulls and zeros — including in final fields. Dynamic dispatch is working
perfectly; the object just doesn't exist yet from the subclass's point of view.

Now, "the first time the class is used" hides two things that are genuinely load-bearing.

The first is a deployment bug. A `static final` primitive or String initialised with a constant
expression is a COMPILE-TIME CONSTANT, and its value gets copied into the CALLER's class file. So
reading it doesn't touch the declaring class at all, and its static block never runs. Change the
constant, rebuild only the library, and every already-compiled caller still has the old literal baked
in. The library says 200, the application behaves as 100, and nothing anywhere is wrong. The fix is a
full rebuild.

The second is the most confusing error message in Java. If a static initialiser throws, you get
ExceptionInInitializerError — and the class is permanently marked ERRONEOUS. Initialisation is attempted
exactly ONCE. So every subsequent use, for the life of the JVM, throws "NoClassDefFoundError: Could not
initialize class Foo". The message says the class can't be found and the class is right there. People
spend hours on classpath theories. Always look for the FIRST occurrence in the log, not the one you're
staring at — and it's often in another thread, often already swallowed.

The third thing about <clinit> is that the JVM guarantees it runs exactly once and takes a per-class
lock to do it. That's a free thread-safety guarantee, and it's what the initialization-on-demand HOLDER
idiom exploits: a private static nested Holder class whose static field creates the instance. It isn't
initialised until someone touches it, and the class lock makes that exactly-once. Lazy, thread-safe,
zero synchronisation you wrote. Enums get the same guarantee, which is why `enum Singleton { INSTANCE }`
is the recommended singleton.

Practically, I'd avoid depending on any of this. Constructor parameters or a record for state, a static
factory instead of a complicated static block — because a static block runs on an arbitrary thread,
under a lock, and a failure poisons the class permanently.'""",

"""8. THE CODE, LINE BY LINE

    // ── SOURCE ORDER IS THE ONLY ORDER ──────────────────────────────────
    class Config {
        static int a = 1;
        static { a = 2; b = 5; }          // ← may ASSIGN b, declared below
        static int b = 3;                 // ← RUNS NOW, and OVERWRITES the 5
        static { System.out.println(b); } // ← prints 3
    }
    // A block above a declaration LOSES to that declaration's initialiser. And a
    // block may assign a later field but may NOT READ it by simple name — "illegal
    // forward reference", a compile error. Writing is harmless; reading would observe
    // a default that looks like a bug.

    // ── THE SIX-STEP ORDER ──────────────────────────────────────────────
    class Parent {
        static { print("1 parent static"); }
        { print("3 parent instance block"); }
        Parent() { print("4 parent constructor"); }
    }
    class Child extends Parent {
        static { print("2 child static"); }
        { print("5 child instance block"); }
        Child() { print("6 child constructor"); }
    }
    new Child();   // 1, 2, 3, 4, 5, 6 — then a SECOND `new Child()` prints only 3,4,5,6
    //                                    because statics run ONCE, ever.

    // ── WHAT THE COMPILER EMITS FOR A CONSTRUCTOR ───────────────────────
    Child() {
        super();                    // ← 1. implicit if you write neither super nor this
        /* all instance field initialisers and blocks, in SOURCE ORDER */  // ← 2.
        print("6 child constructor");                                     // ← 3.
    }
    // Step 2 is what people forget. And with `this(...)` delegation, step 2 runs ONLY
    // in the constructor that eventually reaches super — once per OBJECT, not once
    // per constructor in the chain.

    // ── THE BUG THAT ORDER CAUSES ───────────────────────────────────────
    class Parent { Parent() { init(); } void init() { } }
    class Child extends Parent {
        private final List<String> items = new ArrayList<>();
        @Override void init() { items.add("x"); }   // ← NullPointerException
    //                          ^^^^^ Parent's constructor is step 4; this field
    //   initialiser is step 5. The override runs with `items` STILL NULL — and it is
    //   a `final` field, which makes it look impossible.
    }

    // ── THE DEPLOYMENT BUG ──────────────────────────────────────────────
    // library:      public static final int MAX = 100;
    // application:  if (n > Library.MAX) { ... }
    //
    // `MAX` is a COMPILE-TIME CONSTANT (a static final primitive with a constant
    // initialiser), so the value 100 is COPIED INTO THE APPLICATION'S CLASS FILE.
    // Reading it never touches Library — its static block never runs.
    // Change MAX to 200, rebuild ONLY the library: the app still behaves as 100.
    // Nothing errors. The fix is a FULL REBUILD.
    public static int max() { return MAX; }        // ← a method is NOT inlined

    // ── THE ERROR MESSAGE THAT NAMES THE WRONG PROBLEM ──────────────────
    class Registry { static final Config C = load(); }   // load() throws
    Registry.C;   // 1st use → ExceptionInInitializerError, caused by the real failure
    Registry.C;   // EVERY LATER USE → NoClassDefFoundError: Could not initialize
    //                                 class Registry
    // Initialisation is attempted exactly ONCE; failure marks the class ERRONEOUS for
    // the life of the JVM. The second message says the class cannot be found and the
    // class is right there. FIND THE FIRST ExceptionInInitializerError IN THE LOG.

    // ── THE GUARANTEE, TURNED INTO A FEATURE ────────────────────────────
    class Singleton {
        private Singleton() { }
        private static class Holder { static final Singleton INSTANCE = new Singleton(); }
        static Singleton get() { return Holder.INSTANCE; }
    //                                  ^^^^^^^^^^^^^^^ Holder is not initialised until
    //   THIS LINE runs. The JVM's per-class init lock makes `new Singleton()` happen
    //   exactly once even under concurrent access. LAZY, THREAD-SAFE, AND NOT ONE LINE
    //   OF SYNCHRONISATION — because the JVM already had to solve this for <clinit>.
    }
    enum Better { INSTANCE }   // same guarantee, plus serialization- and
    //                            reflection-safety. Effective Java's preferred form.""",

"""9. THE TRACE — three programs, three different lessons

PROGRAM 1 — THE FULL ORDER. `new Child(); new Child();`

    call        what runs                              why
    ---------------------------------------------------------------------------------
    first new   Parent.<clinit>                         Child's init forces Parent's
                Child.<clinit>                          the class is being used
                Parent instance blocks                  step 2 of Parent's <init>
                Parent constructor body                 step 3
                Child instance blocks                   step 2 of Child's <init>
                Child constructor body                  step 3
    second new  Parent instance blocks                  <clinit> ALREADY RAN — statics
                Parent constructor body                 are once, ever, per class
                Child instance blocks                   loader
                Child constructor body
    ---------------------------------------------------------------------------------
    THE SECOND `new` SKIPS BOTH STATIC SECTIONS ENTIRELY. That is the one asymmetry to hold on to:
    statics are once per class, everything else is once per object.

PROGRAM 2 — THE CONSTANT THAT WAS NOT THERE.

    step                                        what happens
    ---------------------------------------------------------------------------------
    compile App against Library v1 (MAX = 100)  javac copies the literal 100 INTO
                                                App.class. No reference to Library
                                                remains for that read.
    ship Library v2 (MAX = 200), do not         App.class still contains 100
    recompile App
    run                                         App behaves as 100. Library.<clinit>
                                                never runs for this read at all.
    inspect Library.MAX in a debugger           200. It genuinely is 200.
    ---------------------------------------------------------------------------------
    NOTHING IS BROKEN AND NOTHING WILL TELL YOU. The value in the source, the value in the jar and the
    value in the running program disagree, and each is individually correct. A full rebuild fixes it;
    a static accessor method would have prevented it, because method calls are not inlined across a
    compilation boundary.

PROGRAM 3 — THE ERROR THAT NAMES THE WRONG PROBLEM.

    time  what happens                                  what is logged
    ---------------------------------------------------------------------------------
    t0    a background thread touches Registry           ExceptionInInitializerError
          Registry.<clinit> throws (config file          Caused by: FileNotFoundException
          missing)
    t1    that thread's catch(Exception) SWALLOWS it     nothing — an Error is not an
          — except it does not, because Error is not     Exception, so it propagates and
          an Exception. It propagates and kills the      is logged by the thread's
          thread.                                        default handler, possibly to
                                                         stderr nobody reads
    t2    a request thread touches Registry              NoClassDefFoundError: Could
                                                         not initialize class Registry
    t3    every subsequent request                       the same, forever
    ---------------------------------------------------------------------------------
    THE ONLY MESSAGE ANYONE SEES SAYS "CANNOT FIND THE CLASS", AND THE CLASS IS IN THE JAR. The real
    cause — a missing config file — appeared once, at t0, in a different thread, possibly hours
    earlier. THE DIAGNOSTIC RULE IS THEREFORE: grep the whole log for the FIRST
    `ExceptionInInitializerError` and read its `Caused by`.

AND THE CIRCULAR-STATICS TRACE, which is the quiet one:

    ONE THREAD                                   TWO THREADS
    ---------------------------------------------------------------------------------
    A.<clinit> starts, reads B.X                 T1 starts A.<clinit>, holds A's lock
    → B.<clinit> starts, reads A.Y               T2 starts B.<clinit>, holds B's lock
    → A is ALREADY BEING INITIALISED BY THIS     T1 needs B's lock → blocks
      THREAD, so the JVM lets the read           T2 needs A's lock → blocks
      proceed → A.Y is its DEFAULT (0/null)      DEADLOCK
    → B finishes with a wrong value              jstack shows both threads in <clinit>
    → A finishes                                 and does NOT report a deadlock, because
    NO ERROR. NO WARNING.                        the locks are internal to the JVM
    ---------------------------------------------------------------------------------
    The single-threaded column is worse in practice: a field is silently zero, no exception is thrown,
    and nothing in the source explains it.

WHAT PRODUCED WHAT:
    LAZY, ONCE-EVER <clinit>   produced program 1's asymmetry and the holder idiom.
    CONSTANT INLINING          produced program 2 — a compile-time decision surviving into runtime.
    ERRONEOUS CLASS STATE      produced program 3's misleading message.
    THE PER-CLASS INIT LOCK    produced both the free thread safety and the deadlock.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Order: parent statics → child statics → parent instance initialisers → parent constructor → child
    instance initialisers → child constructor. Within each group, SOURCE ORDER.
    Statics run ONCE per class per class loader. Instance initialisation runs on every `new`.
    `<clinit>` runs under a per-class JVM lock — free, exactly-once, thread-safe.
    Triggers: `new`, a static method call, a NON-CONSTANT static field access, `Class.forName(name)`,
    subclass initialisation.
    NOT triggers: array creation, a compile-time constant read, `Class.forName(n, false, cl)`.
    A failed `<clinit>` marks the class erroneous PERMANENTLY; later uses throw `NoClassDefFoundError`.

THE #1 MISTAKE: calling an overridable method from a constructor. The override runs before the
subclass's field initialisers and sees nulls and zeros, `final` fields included.

THE #2 MISTAKE: assuming field initialisers run "with the field". They run after `super()` and before
the constructor body.

THE #3 MISTAKE: chasing a classpath problem when you see `NoClassDefFoundError: Could not initialize
class X`. Find the earlier `ExceptionInInitializerError`.

THE #4 MISTAKE: public `static final` primitive or String constants in a library compiled separately
from its callers. They are inlined and cannot be changed without a full rebuild.

THE #5 MISTAKE: real work in a static block. It runs under a class lock, on whichever thread arrived
first, and a failure is permanent.

THE #6 MISTAKE: mutual references between two classes' static initialisers. One thread gives a silent
default; two threads deadlock in a way `jstack` will not name.

THE #7 MISTAKE: expecting `new Foo[10]` to run `Foo`'s static block. Array creation is not a trigger.

THE #8 MISTAKE: `Class.forName(name, false, loader)` where a driver registers itself in `<clinit>`.

THE #9 MISTAKE: interleaving static blocks and static field declarations. A later declaration silently
overwrites an earlier block's assignment.

THE #10 MISTAKE: double-checked locking for a lazy singleton. The holder idiom is simpler, lock-free and
correct by construction.

THE #11 MISTAKE: double-brace initialisation. It creates an anonymous subclass carrying a `this$0`
back-reference — a leak and a serialization failure.

ONE-SENTENCE TAKEAWAY: statics run ONCE, ever, the first time a class is genuinely used, and instance
initialisation runs on every `new` in the order super-call → field initialisers and instance blocks →
constructor body — which is why a superclass constructor calling an overridable method sees the
subclass's `final` fields still null; "genuinely used" excludes array creation and COMPILE-TIME
CONSTANTS, whose values are copied into the caller's class file and therefore go stale until a full
rebuild, and a static initialiser that throws marks the class erroneous permanently, so the message you
actually see is `NoClassDefFoundError: Could not initialize class X` for a class that is plainly present
— always hunt for the first `ExceptionInInitializerError` instead; and the JVM's per-class
initialisation lock is a free exactly-once thread-safety guarantee, which is exactly what the
holder-class singleton idiom is built on.""",
]


DEEP["finally, try-with-resources, and the return that eats an exception"] = [
"""1. THE GOAL IN PLAIN ENGLISH — code that runs no matter what happens

`finally` is the block that runs whether the `try` succeeded, threw, or returned. It exists for cleanup:
close the file, release the lock, restore the state, stop the timer.

    IT RUNS ON EVERY EXIT PATH. Normal completion, a `return`, a `break`, a `continue`, or an exception
    propagating outward. That is a strong guarantee, and it is why `lock()` / `try` / `finally
    { unlock() }` is the only safe shape for an explicit lock.

    THE FOUR THINGS THAT DEFEAT IT: `System.exit()`, the JVM crashing or being killed, an infinite loop
    or deadlock inside the `try`, and a daemon thread being terminated at shutdown. Everything else runs
    the block.

AND YET `finally` IS ALSO WHERE TWO OF THE MOST DESTRUCTIVE BUGS IN JAVA LIVE, both of which SILENTLY
DELETE INFORMATION:

    A `return` INSIDE `finally` DISCARDS AN IN-FLIGHT EXCEPTION. Not "logs it" — deletes it. The method
    returns normally, with no evidence that anything went wrong. It also discards any earlier `return`
    value.

    A `finally` BLOCK THAT THROWS REPLACES THE ORIGINAL EXCEPTION. So a `close()` failing during cleanup
    hides the actual error that caused the failure, and you are left debugging "connection already
    closed" instead of the real cause.

    THAT SECOND ONE IS SO COMMON THAT THE LANGUAGE ADDED A FEATURE TO FIX IT. try-with-resources (Java
    7) closes resources automatically, in reverse order, and if both the body and `close()` throw, THE
    BODY'S EXCEPTION WINS and `close()`'s is attached to it as a SUPPRESSED exception. Nothing is lost.

THE EVERYDAY VERSION: `finally` is "turn the lights off on your way out, whatever happened". The bug is
turning the lights off and, in the process, throwing away the note explaining why the building had to be
evacuated — so the next person finds a dark, tidy room and no idea what occurred.

TERMS AS THEY APPEAR:
- SUPPRESSED EXCEPTION: a secondary failure attached to the primary one instead of replacing it.
- `AutoCloseable`: the interface try-with-resources requires. `close()` may throw anything.
- `Closeable`: the older subinterface whose `close()` throws only `IOException`.""",

"""2. THE INTUITION — why `return` in `finally` deletes things

THE RULE IS SIMPLE ONCE STATED: `finally` COMPLETES LAST, AND WHATEVER WAY IT COMPLETES WINS.

    If the `try` block is propagating an exception and the `finally` block completes NORMALLY, the
    exception continues. Good.
    If the `finally` block completes ABRUPTLY — by returning, throwing, breaking or continuing — THAT
    ABRUPT COMPLETION REPLACES WHATEVER THE `try` WAS DOING. The original is discarded, silently and
    completely.

    So `try { throw new IOException("disk full"); } finally { return 42; }` returns 42. The
    IOException is not logged, not wrapped, not chained. It ceases to exist. THE COMPILER WARNS, AND
    THE CODE COMPILES AND RUNS.

THE SECOND SUBTLETY IS ABOUT THE RETURN VALUE, and it catches people who think `finally` runs "before"
the return:

    int f() { int x = 1; try { return x; } finally { x = 99; } }   // returns 1

    THE RETURN VALUE IS COMPUTED AND STASHED BEFORE `finally` RUNS. `return x` evaluates `x` to 1, puts
    that 1 aside, then runs the `finally`, then returns the stashed 1. Mutating the variable afterwards
    changes nothing.

    BUT `try { return list; } finally { list.add("x"); }` DOES include the added element — because what
    was stashed is the REFERENCE, and the object it points at was mutated. The value is frozen; the
    object is not. Both behaviours follow from the same rule and look contradictory until you see it.

WHY try-with-resources HAD TO EXIST — look at what correct manual cleanup actually requires:

    InputStream in = null;
    try { in = open(); use(in); }
    finally { if (in != null) in.close(); }

    THAT IS STILL WRONG. If `use(in)` throws AND `close()` throws, the close exception replaces the real
    one. You lose the cause and keep the symptom.

    AND WITH TWO RESOURCES IT GETS WORSE: `finally { in.close(); out.close(); }` never closes `out` if
    `in.close()` throws. The genuinely correct manual version is a nested try-finally with a saved
    primary exception and an `addSuppressed` call — about fifteen lines, which nobody wrote correctly,
    which is precisely why the JDK's own code was full of this bug before Java 7.

    try-with-resources GENERATES THAT CORRECT CODE. Resources close in REVERSE order of declaration
    (because later ones may depend on earlier ones), each close is guarded, the body's exception is
    primary, and every close failure is attached via `addSuppressed`. NOTHING IS LOST AND NOTHING IS
    LEAKED.""",

"""3. THE MECHANISM — what the compiler generates, and where suppression lives

`try (var in = open(); var out = create()) { body(); }` EXPANDS TO ROUGHLY:

    var in = open();
    Throwable primary = null;
    try {
        var out = create();
        try {
            body();
        } catch (Throwable t) { primary = t; throw t; }
        finally {
            if (primary != null) { try { out.close(); } catch (Throwable s) { primary.addSuppressed(s); } }
            else out.close();
    //      ^^^^ NOTE THE ASYMMETRY: if nothing went wrong, a close() failure is thrown
    //           NORMALLY, because there is no primary exception to attach it to.
        }
    } ... the same again for `in` ...

    THREE THINGS TO READ OUT OF THAT:
    RESOURCES CLOSE IN REVERSE ORDER — `out` before `in` — because a later resource typically wraps an
    earlier one, and closing the wrapper first is the only correct order.
    A CLOSE FAILURE NEVER REPLACES A BODY FAILURE. It is attached with `addSuppressed`, retrievable via
    `getSuppressed()`, and printed by the default stack trace printer under "Suppressed:".
    IF THE BODY SUCCEEDED, A CLOSE FAILURE IS THE ONLY EXCEPTION and propagates normally — which is
    correct, because a failed `close()` on a writer means your data may not have been flushed.

`AutoCloseable` vs `Closeable`:
    `AutoCloseable.close() throws Exception` — the general interface, added in Java 7 for
    try-with-resources.
    `Closeable extends AutoCloseable`, narrowing `close()` to `throws IOException`, and its contract
    says close is IDEMPOTENT — calling it twice is harmless. `AutoCloseable` makes no such promise, and
    implementations are strongly encouraged to be idempotent anyway.

JAVA 9 IMPROVEMENT: a resource that is already an EFFECTIVELY FINAL variable can be used directly —
`try (existingResource) { ... }` — instead of the Java 7 requirement to re-declare it, which produced
pointless `try (var r2 = r1)` lines.

WHAT `finally` COMPILES TO: before Java 6 the bytecode used `jsr`/`ret` subroutines; modern compilers
DUPLICATE the finally block into every exit path plus a catch-all handler. That duplication is why a
large `finally` block inflates method size and can push a method past the JIT's inlining threshold — a
small, real reason to keep them short.

TWO PLACES try-with-resources DOES NOT APPLY, where `finally` remains the answer:
    LOCKS. `lock.lock(); try { ... } finally { lock.unlock(); }` — a `Lock` is not `AutoCloseable`.
    (You can write a tiny `AutoCloseable` wrapper, and some teams do.)
    RESTORING STATE — a thread name, an MDC entry, a `ThreadLocal`, a system property, an interrupt
    flag. Anything where cleanup is "put it back" rather than "close it".""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `return` INSIDE `finally`. Discards any in-flight exception AND any earlier return value. The
method reports success and there is no trace of the failure anywhere.

CASE 2 — `finally` THAT THROWS. Replaces the original exception. The classic instance is a `close()`
that fails during cleanup, hiding the error that caused the failure.

CASE 3 — TWO RESOURCES IN ONE `finally`. `finally { in.close(); out.close(); }` never closes `out` if
`in.close()` throws. A resource leak hiding inside cleanup code.

CASE 4 — `break` OR `continue` INSIDE `finally`. Same as `return` — abrupt completion of the `finally`
wins, and the exception is discarded.

CASE 5 — EXPECTING `finally` TO SEE MUTATIONS AFFECT THE RETURN VALUE. `try { return x; } finally
{ x = 99; }` returns the OLD x. The value was stashed before the block ran.

CASE 6 — AND THE OPPOSITE. `try { return list; } finally { list.add("x"); }` DOES include the addition,
because the stashed thing is the reference and the object was mutated.

CASE 7 — `System.exit()` INSIDE `try`. `finally` does not run. Neither does it on a JVM crash, a
`SIGKILL`, an infinite loop, or a daemon thread killed at shutdown.

CASE 8 — SWALLOWING `InterruptedException` IN A `finally`. Clears the interrupt flag, so the thread can
never be cancelled again.

CASE 9 — DECLARING THE RESOURCE OUTSIDE THE `try` PARENTHESES. `var in = open(); try (in) { }` on Java 8
does not compile; before Java 9 you had to re-declare it inside.

CASE 10 — A CONSTRUCTOR THAT THROWS AFTER OPENING THE FIRST RESOURCE.
`try (var a = openA(); var b = openB())` — if `openB()` throws, `a` IS still closed. The generated code
handles it. The equivalent hand-written version usually does not.

CASE 11 — IGNORING SUPPRESSED EXCEPTIONS IN LOGS. They print under "Suppressed:" and people skim past
them. A suppressed `IOException` on close can mean unflushed data.

CASE 12 — A `close()` THAT FAILS ON A SUCCESSFUL BODY. It propagates as the primary exception, which is
correct and surprises people — a failed close on a buffered writer means the data may never have
reached the disk.

CASE 13 — A HUGE `finally` BLOCK. It is duplicated into every exit path in the bytecode, inflating the
method and potentially pushing it past the JIT's inlining threshold.

CASE 14 — NESTED try-with-resources WHERE ONE WRAPS ANOTHER.
`try (var r = new BufferedReader(new FileReader(f)))` — if the `BufferedReader` constructor throws, the
`FileReader` is NEVER CLOSED, because it was never assigned to a resource variable. Declare both.""",

"""5. THE ALTERNATIVES — what to use for which kind of cleanup

try-with-resources FOR ANYTHING `AutoCloseable`. Streams, readers, writers, sockets, JDBC connections,
statements and result sets, `ExecutorService` (Java 19+), locks via a wrapper, `Scanner`, `ZipFile`.
This is the default and there is essentially no reason to hand-write the equivalent.

`finally` FOR STATE RESTORATION, which is not closing:
    `lock.unlock()` — a `Lock` is not `AutoCloseable`;
    restoring a thread name, an MDC context, a `ThreadLocal` (`remove()` in a finally, always);
    restoring a system property or a `Locale` in a test;
    stopping a timer or emitting a metric on every path.

`Cleaner` (Java 9) instead of `finalize()` for native-resource safety nets. `finalize` is deprecated for
removal: it runs on an unspecified thread at an unspecified time, can RESURRECT the object, and delays
collection by at least one extra GC cycle. A `Cleaner` is a backstop for the case where a caller forgot
to close — NEVER the primary mechanism.

A `PhantomReference` + reference queue if you need to build that backstop yourself. `Cleaner` is built on
exactly this.

CONNECTION AND OBJECT POOLS, where `close()` means RETURN TO THE POOL rather than destroy. HikariCP works
this way, which is why try-with-resources on a pooled `Connection` is correct and cheap — and why
forgetting it exhausts the pool rather than leaking a socket.

STRUCTURED LIFETIMES over manual cleanup where the language offers them: `StructuredTaskScope` for
tasks, `ExecutorService` as `AutoCloseable` since Java 19, `Arena` in the Foreign Function & Memory API
for off-heap memory. THE PATTERN IS THE SAME EVERY TIME — bind the lifetime to a syntactic block so
the compiler enforces the cleanup instead of the reviewer.

AND THE ALTERNATIVE THAT IS OFTEN BEST: DO NOT ACQUIRE A RESOURCE THAT NEEDS CLEANUP.
`Files.readString(path)` and `Files.lines(path)` (the latter still needs closing) hide the stream
entirely. A method that returns a `List` rather than an open `Stream` has no lifetime for the caller to
get wrong.

WHAT TO SAY: "try-with-resources for anything closeable — it closes in reverse order and attaches a
close failure as SUPPRESSED rather than letting it replace the real exception, which the hand-written
version almost never got right. `finally` for restoring state, like unlocking or clearing a ThreadLocal.
And never a `return` inside a `finally`, because it silently deletes an in-flight exception."

""",

"""6. HOW TO WRITE CLEANUP CORRECTLY — numbered steps

STEP 1 — USE try-with-resources FOR EVERY `AutoCloseable`. There is no situation where the hand-written
version is better.

STEP 2 — DECLARE EVERY RESOURCE SEPARATELY, EVEN WHEN NESTED. `try (var f = new FileReader(p); var b =
new BufferedReader(f))`. If you wrap them in one expression and the outer constructor throws, the inner
one is never closed.

STEP 3 — NEVER `return`, `break` OR `continue` FROM A `finally`. Abrupt completion of the block replaces
whatever the `try` was doing, including an exception.

STEP 4 — NEVER LET A `finally` THROW. If cleanup can fail, catch and log inside it, or let
try-with-resources handle the suppression for you.

STEP 5 — USE `finally` ONLY FOR STATE RESTORATION: unlocking, clearing a `ThreadLocal`, restoring a
thread name or an MDC entry, stopping a timer.

STEP 6 — PUT `lock.lock()` IMMEDIATELY BEFORE THE `try`, NEVER INSIDE IT. If `lock()` throws and it was
inside, the `finally` calls `unlock()` on a lock you never acquired.

STEP 7 — READ THE "Suppressed:" SECTION OF A STACK TRACE. A suppressed `IOException` from `close()` on a
writer can mean your data never reached the disk.

STEP 8 — REMEMBER A SUCCESSFUL BODY WITH A FAILING `close()` STILL THROWS. That is correct, and code
that assumes "the body worked, so we are fine" is not.

STEP 9 — RESTORE THE INTERRUPT FLAG rather than swallowing `InterruptedException` in a `finally`.

STEP 10 — KEEP `finally` BLOCKS SHORT. They are duplicated into every exit path in the bytecode.

STEP 11 — TREAT `Cleaner` AS A BACKSTOP, NEVER THE MECHANISM. And never use `finalize()`, which is
deprecated for removal.

STEP 12 — PREFER AN API THAT HAS NO LIFETIME TO MANAGE. `Files.readString` over an open stream, whenever
the data fits.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'`finally` runs on every exit path — normal completion, a return, a break, an exception propagating
outward. Four things defeat it: System.exit, the JVM dying, an infinite loop or deadlock inside the try,
and a daemon thread killed at shutdown. Everything else runs it.

The rule that explains all the surprising behaviour is: `finally` completes LAST, and however it
completes WINS. If the try is propagating an exception and the finally completes normally, the exception
continues. But if the finally completes ABRUPTLY — returns, throws, breaks — that replaces whatever the
try was doing. Silently and completely.

So `try { throw new IOException("disk full"); } finally { return 42; }` returns 42. The exception isn't
logged, wrapped or chained. It ceases to exist, and the method reports success. The compiler warns and
the code runs.

There's a second subtlety about return VALUES. `int f() { int x = 1; try { return x; } finally { x = 99;
} }` returns 1 — the value is computed and stashed BEFORE finally runs, so mutating the variable
afterwards changes nothing. But `try { return list; } finally { list.add("x"); }` DOES include the added
element, because what was stashed is the REFERENCE and the object was mutated. Both follow from the same
rule and look contradictory until you see it.

The reason try-with-resources had to exist is that correct manual cleanup is genuinely hard. The obvious
version — a null check and a close in finally — is still wrong: if the body throws AND close throws, the
close exception REPLACES the real one, so you lose the cause and keep the symptom. And with two
resources, `finally { in.close(); out.close(); }` never closes out if in.close() throws. The genuinely
correct hand-written version is a nested try-finally with a saved primary exception and an addSuppressed
call — about fifteen lines that nobody wrote correctly, which is why the JDK's own code was full of this
bug before Java 7.

try-with-resources generates that correct code. Resources close in REVERSE order of declaration, because
a later one usually wraps an earlier one. Each close is guarded. The body's exception is primary, and
any close failure is attached with addSuppressed, so nothing is lost — you see it in the stack trace
under "Suppressed:".

Two things worth knowing on top. If the body SUCCEEDED and close throws, that propagates as the primary
exception — which is correct, because a failed close on a buffered writer means your data may never have
reached the disk. And you should declare every resource SEPARATELY even when nested: `try (var r = new
BufferedReader(new FileReader(f)))` never closes the FileReader if the BufferedReader constructor throws,
because it was never assigned to a resource variable.

`finally` still has a job — state RESTORATION rather than closing. Unlocking a Lock, which isn't
AutoCloseable. Clearing a ThreadLocal. Restoring a thread name or an MDC entry. And the lock() call goes
immediately before the try, never inside it, or the finally unlocks something you never acquired.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE RETURN THAT DELETES AN EXCEPTION ────────────────────────────
    int f() {
        try { throw new IOException("disk full"); }
        finally { return 42; }
    //           ^^^^^^^^^ ABRUPT COMPLETION OF finally WINS. The IOException is not
    //   logged, not wrapped, not chained — it CEASES TO EXIST. The method reports
    //   success. The compiler warns; the code compiles and runs.
    }

    // ── THE VALUE IS STASHED BEFORE finally RUNS ────────────────────────
    int g() { int x = 1; try { return x; } finally { x = 99; } }
    // returns 1. `return x` evaluates x to 1, PUTS THAT 1 ASIDE, runs the finally,
    // then returns the stashed 1.
    List<String> h() { var l = new ArrayList<String>(); try { return l; }
                       finally { l.add("x"); } }
    // returns ["x"]. What was stashed is the REFERENCE; the OBJECT was mutated.
    // Same rule, opposite-looking outcome.

    // ── WHY THE MANUAL PATTERN IS WRONG ─────────────────────────────────
    InputStream in = null;
    try { in = open(); use(in); }
    finally { if (in != null) in.close(); }
    //                        ^^^^^^^^^^ if use(in) threw AND close() throws, THE
    //   CLOSE EXCEPTION REPLACES THE REAL ONE. You keep the symptom ("stream already
    //   closed") and lose the cause.

    try { ... } finally { in.close(); out.close(); }
    //                    ^^^^^^^^^^ if THIS throws, `out` IS NEVER CLOSED.
    //   A resource leak hiding inside the cleanup code.

    // ── WHAT try-with-resources GENERATES FOR YOU ───────────────────────
    try (var in = open(); var out = create()) { body(); }
    // roughly:
    //   Throwable primary = null;
    //   try { body(); }
    //   catch (Throwable t) { primary = t; throw t; }
    //   finally {
    //       if (primary != null) { try { out.close(); }
    //                              catch (Throwable s) { primary.addSuppressed(s); } }
    //       else out.close();          // ← no primary to attach to, so it propagates
    //   }                              //   NORMALLY — and that is correct
    //   ... the same again for `in` ...
    //
    // CLOSES IN REVERSE ORDER (out before in) because a later resource usually WRAPS
    // an earlier one. A close failure is SUPPRESSED, never a replacement.

    // ── READING THE RESULT ──────────────────────────────────────────────
    // java.lang.IllegalStateException: the real problem      ← PRIMARY
    //     at Service.process(Service.java:42)
    //     Suppressed: java.io.IOException: disk full         ← the close failure,
    //         at java.io.BufferedWriter.close(...)              NOT lost
    catch (Exception e) { for (Throwable s : e.getSuppressed()) log.warn("close", s); }

    // ── THE NESTING TRAP ────────────────────────────────────────────────
    try (var r = new BufferedReader(new FileReader(f))) { ... }
    //                              ^^^^^^^^^^^^^^^^^ if the BufferedReader
    //   constructor throws (out of memory, for instance), THE FileReader IS NEVER
    //   CLOSED — it was never assigned to a resource variable.
    try (var f1 = new FileReader(f); var r = new BufferedReader(f1)) { ... }
    //   ^ declare BOTH. Now both are closed, in reverse order.

    // ── WHERE finally IS STILL THE ANSWER ───────────────────────────────
    lock.lock();                       // ← IMMEDIATELY BEFORE the try, never inside:
    try { ... }                        //   if lock() threw and it were inside, the
    finally { lock.unlock(); }         //   finally would unlock a lock you never took
    String old = Thread.currentThread().getName();
    Thread.currentThread().setName("job-" + id);
    try { ... } finally { Thread.currentThread().setName(old); }
    try { ... } finally { CONTEXT.remove(); }   // ← ThreadLocal in a pooled thread""",

"""9. THE TRACE — one failing body, four cleanup strategies

THE SETUP: `body()` throws `IllegalStateException("real problem")`, and `close()` on the writer throws
`IOException("disk full")` because the buffer cannot be flushed.

    STRATEGY 1 — MANUAL finally
    step  what happens                                what the caller sees
    ---------------------------------------------------------------------------------
    1     body() throws IllegalStateException          —
    2     finally runs                                 —
    3     close() throws IOException                   the IOException REPLACES the
                                                       IllegalStateException
    4     propagates                                   IOException: disk full
                                                       at BufferedWriter.close(...)
    ---------------------------------------------------------------------------------
    THE REAL PROBLEM IS GONE. Not logged, not chained — the object was discarded when the second
    exception was thrown out of the finally block. The team debugs a disk-space issue for a day.

    STRATEGY 2 — MANUAL finally WITH A return
    step  what happens                                what the caller sees
    ---------------------------------------------------------------------------------
    1     body() throws IllegalStateException          —
    2     finally { return DEFAULT; }                  —
    3     abrupt completion of finally WINS            a normal return of DEFAULT
    ---------------------------------------------------------------------------------
    WORSE. No exception at all. The method reports success, the caller carries on with a default value,
    and the failure has left no trace anywhere in the system. This is the shape that produces "the data
    is silently wrong in production and nothing in the logs mentions it".

    STRATEGY 3 — try-with-resources
    step  what happens                                what the caller sees
    ---------------------------------------------------------------------------------
    1     body() throws IllegalStateException          captured as `primary`
    2     generated finally sees primary != null       —
    3     close() throws IOException                   caught, and attached with
                                                       primary.addSuppressed(io)
    4     primary is rethrown                          IllegalStateException: real
                                                         problem
                                                         at Service.process:42
                                                         Suppressed: IOException:
                                                           disk full
    ---------------------------------------------------------------------------------
    BOTH FAILURES SURVIVE, in the right priority order. And the disk-full information is genuinely
    valuable — it means the write may not have completed — so losing it in strategy 1 was bad in two
    directions at once.

    STRATEGY 4 — try-with-resources, BODY SUCCEEDS
    step  what happens                                what the caller sees
    ---------------------------------------------------------------------------------
    1     body() returns normally                      primary is null
    2     close() throws IOException                   nothing to attach it to
    3     it propagates as the ONLY exception          IOException: disk full
    ---------------------------------------------------------------------------------
    THIS SURPRISES PEOPLE AND IS CORRECT. The body "worked", but a failed close on a buffered writer
    means the buffered data may never have reached the disk. Code that assumes success because the body
    returned is wrong.

NOW THE TWO-RESOURCE TRACE, showing the leak the manual version hides:

    finally { in.close(); out.close(); }
    step  what happens
    ---------------------------------------------------------------------------------
    1     in.close() throws
    2     the finally block completes ABRUPTLY
    3     out.close() IS NEVER REACHED                 ← A LEAKED FILE HANDLE, inside
                                                         the code written to prevent
                                                         leaks
    ---------------------------------------------------------------------------------
    try (var in = ...; var out = ...) { }
    1     out.close() runs first (REVERSE order — out usually wraps in)
    2     it throws → suppressed
    3     in.close() STILL RUNS, in its own guarded block
    4     both failures attached to the primary
    ---------------------------------------------------------------------------------

AND THE RETURN-VALUE TRACE, which explains the apparent contradiction:

    int f() { int x = 1; try { return x; } finally { x = 99; } }
    step  what the bytecode does                       stack / locals
    ---------------------------------------------------------------------------------
    1     iload x                                      stack: [1]
    2     istore into a hidden temp                    temp = 1     ← THE STASH
    3     run the finally block: x = 99                x = 99, temp = 1
    4     iload temp; ireturn                          returns 1
    ---------------------------------------------------------------------------------
    List<String> h() { ... try { return l; } finally { l.add("x"); } }
    2     the stash holds THE REFERENCE                temp = @0x1000
    3     l.add("x") mutates the object AT @0x1000
    4     returns @0x1000 — which now contains "x"
    ---------------------------------------------------------------------------------
    THE VALUE IS FROZEN; THE OBJECT IS NOT. One rule, two outcomes, and it is only confusing if you
    think `finally` runs "before the return" rather than "after the return value is computed".

WHAT PRODUCED WHAT:
    ABRUPT COMPLETION WINS   produced strategies 1 and 2 — one loses a cause, the other loses
                             everything.
    addSuppressed            produced strategy 3, and is the entire reason the feature exists.
    THE STASHED RETURN VALUE produced the last table, and the apparent contradiction between its two
                             halves.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `finally` runs on every exit path except `System.exit`, a JVM crash or kill, an infinite loop or
    deadlock in the `try`, and a daemon thread terminated at shutdown.
    Abrupt completion of `finally` — return, throw, break, continue — REPLACES whatever the `try` was
    doing.
    The return value is computed and stashed BEFORE `finally` runs; the object it references is not
    frozen.
    try-with-resources closes in REVERSE declaration order, guards each close, makes the body's
    exception primary, and attaches close failures via `addSuppressed`.
    A close failure on a SUCCESSFUL body propagates as the primary exception. That is correct.
    `finally` blocks are duplicated into every exit path in the bytecode, so large ones inflate methods.

THE #1 MISTAKE: `return` inside `finally`. It silently deletes an in-flight exception and any earlier
return value.

THE #2 MISTAKE: a `finally` that can throw. It replaces the original exception — you keep the symptom
and lose the cause.

THE #3 MISTAKE: closing two resources in one `finally`. If the first close throws, the second never
happens. A leak inside the leak-prevention code.

THE #4 MISTAKE: hand-writing resource cleanup at all. The correct version is fifteen lines with a saved
primary and `addSuppressed`, and essentially nobody wrote it correctly before Java 7.

THE #5 MISTAKE: `try (var r = new BufferedReader(new FileReader(f)))`. If the outer constructor throws,
the inner resource is never closed. Declare both.

THE #6 MISTAKE: assuming a mutation in `finally` changes the returned value. Primitives and references
are stashed; objects can still be mutated.

THE #7 MISTAKE: `lock.lock()` inside the `try`. If it throws, the `finally` unlocks a lock you never
acquired.

THE #8 MISTAKE: ignoring the "Suppressed:" section of a stack trace. A suppressed close failure can mean
unflushed data.

THE #9 MISTAKE: assuming a successful body means success. A failing `close()` still throws, and it means
something.

THE #10 MISTAKE: swallowing `InterruptedException` in a `finally`. It clears the flag and makes the
thread uncancellable.

THE #11 MISTAKE: forgetting `ThreadLocal.remove()` in a `finally` on a pooled thread. The thread never
dies, so the value never goes.

THE #12 MISTAKE: `finalize()` as a cleanup safety net. Deprecated for removal; use `Cleaner`, and only
as a backstop.

ONE-SENTENCE TAKEAWAY: `finally` runs on every exit path and COMPLETES LAST — so however it completes
WINS, which is why a `return` inside it silently deletes an in-flight exception and why a `finally` that
throws replaces the real cause with the cleanup symptom; try-with-resources exists because the correct
hand-written version is a nested try-finally with a saved primary exception and an `addSuppressed` call
that almost nobody wrote, and it closes resources in REVERSE declaration order with each close guarded
and every close failure attached as SUPPRESSED rather than substituted — leaving `finally` for state
restoration (unlocking, clearing a `ThreadLocal`, restoring a thread name) where "put it back" is the
cleanup rather than "close it".""",
]


DEEP["OutOfMemoryError — five different messages, five different causes"] = [
"""1. THE GOAL IN PLAIN ENGLISH — "out of memory" is not one problem

Everyone reads `OutOfMemoryError` as "the heap is full, raise `-Xmx`". That is right for ONE of the
messages and actively wrong for most of the others. THE TEXT AFTER THE COLON IS THE DIAGNOSIS, and
ignoring it is how teams spend a week raising a limit that was never the constraint.

    `Java heap space`                      the heap really is full
    `GC overhead limit exceeded`           the heap is effectively full, reported earlier
    `Metaspace`                            CLASS metadata, a different region entirely
    `unable to create new native thread`   the OPERATING SYSTEM refused. The heap is fine.
    `Direct buffer memory`                 OFF-heap NIO buffers. The heap is fine.
    `Requested array size exceeds VM limit` you asked for an array bigger than an `int` can index
    `Compressed class space`               the fixed region holding class pointers
    `Out of swap space?`                   a native allocation failed. Usually not Java's fault at all

    NUMBERS FOUR, FIVE, SIX AND EIGHT ALL OCCUR WITH A HEAP THAT IS BARELY USED. Raising `-Xmx` makes
    number four WORSE, because a bigger heap leaves less address space for thread stacks.

AND THERE IS A NINTH FAILURE THAT IS NOT AN `OutOfMemoryError` AT ALL, and is now the most common one in
practice: THE CONTAINER OOM-KILL. In Kubernetes the kernel kills the process when its total resident
memory exceeds the container limit. Exit code 137, no Java error, no stack trace, no heap dump — just a
process that vanished. THE JVM NEVER GOT TO COMPLAIN, because the heap was not full; everything else
was.

THE EVERYDAY VERSION: "the kitchen has run out" can mean out of ingredients, out of clean plates, out of
oven space, out of staff, or the building's power being cut. Ordering more ingredients helps in exactly
one case and is irrelevant in the rest — and in one of them it makes things worse, because the new
delivery takes up the space the plates needed.

TERMS AS THEY APPEAR:
- HEAP: where objects live. Bounded by `-Xmx`.
- METASPACE: native memory holding class metadata. Bounded by `-XX:MaxMetaspaceSize`, unbounded by
  default.
- NATIVE / OFF-HEAP: memory the JVM allocates outside the heap — thread stacks, direct buffers, the
  code cache, GC bookkeeping.
- RSS: resident set size — what the operating system thinks your process is using. THIS is what a
  container limit measures, and it is much more than the heap.""",

"""2. THE INTUITION — a JVM's memory is at least seven separate pools

`-Xmx` BOUNDS ONE OF THEM. This is the single most useful thing to internalise, because it explains why
a container with a 2 GB limit and `-Xmx2g` is guaranteed to be killed:

    HEAP                    objects. `-Xmx`.
    METASPACE               class metadata. Native. UNBOUNDED BY DEFAULT.
    COMPRESSED CLASS SPACE  a 1 GB region for compressed class pointers, when compressed oops are on.
    THREAD STACKS           ~1 MB RESERVED per thread (`-Xss`). 500 threads is 500 MB of reservation.
    CODE CACHE              JIT-compiled machine code. ~240 MB default reserved.
    GC STRUCTURES           card tables, remembered sets, mark bitmaps — roughly 5–10% of heap size.
    DIRECT BUFFERS / NATIVE what NIO, Netty, compression libraries and JNI allocate.

    TOTAL RSS ≈ HEAP + EVERYTHING ELSE, and "everything else" is routinely 500 MB to 1 GB on a real
    service. So `-Xmx` should be roughly 50–75% of the container limit, and the standard way to say
    that is `-XX:MaxRAMPercentage=70` rather than a hard-coded `-Xmx`.

NOW THE SECOND INTUITION, WHICH DECIDES YOUR ENTIRE INVESTIGATION: IS IT A LEAK OR A LEGITIMATE NEED?

    THE TEST IS NOT THE OOM ITSELF. It is the GC log: LOOK AT OLD-GENERATION OCCUPANCY IMMEDIATELY
    AFTER EACH FULL COLLECTION.

    IF THAT NUMBER CLIMBS MONOTONICALLY — 400 MB, then 700 MB, then 1.1 GB after successive full GCs —
    YOU HAVE A LEAK. Something is retaining objects, more memory will only delay the failure, and no
    tuning flag will help.
    IF IT RETURNS TO ROUGHLY THE SAME FLOOR EACH TIME AND THE PEAKS ARE SIMPLY TOO HIGH, YOU HAVE A
    CAPACITY OR ALLOCATION-RATE PROBLEM. More heap, or less allocation, genuinely helps.

    THAT ONE CHART ANSWERS "SHOULD I RAISE -Xmx OR TAKE A HEAP DUMP", and it takes thirty seconds.

AND THE THIRD: `GC overhead limit exceeded` IS A GIFT, NOT A DIFFERENT PROBLEM. The JVM throws it when
more than 98% of recent time went into GC while recovering less than 2% of the heap. WITHOUT IT, the
application would not fail — it would grind, spending nearly all its CPU collecting, serving almost no
requests, and looking "slow" rather than "broken" for hours. The check converts an indefinite hang into
a diagnosable crash. Disabling it with `-XX:-UseGCOverheadLimit` is almost always the wrong instinct.

A NOTE ON CATCHING IT: `OutOfMemoryError` is an `Error`, not an `Exception`, and you should not catch it.
The allocation that failed may be unrelated to the code that caused the problem, other threads are
probably about to fail too, and the JVM is in no state to be reasoned about. The correct response is
`-XX:+HeapDumpOnOutOfMemoryError` plus `-XX:+ExitOnOutOfMemoryError` — capture the evidence and die
cleanly so the orchestrator restarts you.""",

"""3. THE MECHANISM — what each message actually means, and how to confirm it

`Java heap space` — a `new` could not be satisfied and GC could not free enough.
    CAUSES: a retention leak; a genuinely too-small heap; or one enormous allocation (loading a 2 GB
    file into a byte array, an unbounded query result, `list.addAll` of everything).
    CONFIRM: heap dump plus the DOMINATOR TREE in Eclipse MAT — it answers "what is keeping this alive",
    which is the only question that matters. `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps`.

`GC overhead limit exceeded` — >98% of time in GC, <2% of heap recovered.
    SAME UNDERLYING CAUSE as heap space, detected earlier. Treat identically.

`Metaspace` (pre-Java 8: `PermGen space`) — class metadata, in NATIVE memory, UNBOUNDED by default.
    CAUSES: heavy dynamic class generation — CGLIB/ByteBuddy proxies, scripting engines, some ORM and
    mocking frameworks; or, classically, a CLASSLOADER LEAK, where redeploying a web application leaves
    the old loader reachable so every class it ever loaded is retained. Ten redeploys, ten copies of
    the application's classes.
    CONFIRM: `jcmd <pid> VM.metaspace`, and count loaded classes over time with `jstat -class`. A
    monotonically rising class count with a stable workload is the tell.

`unable to create new native thread` — the OS refused to create a thread. THE HEAP IS USUALLY FINE.
    CAUSES: a genuine thread leak (a pool created per request, an unshut-down executor); `ulimit -u` or
    a container PID limit; or — the counter-intuitive one — A HEAP SO LARGE THERE IS NO ADDRESS SPACE
    OR RAM LEFT FOR STACKS, since each thread RESERVES about 1 MB.
    CONFIRM: `jstack` and count threads, grouped by name. RAISING `-Xmx` MAKES THIS WORSE.

`Direct buffer memory` — `ByteBuffer.allocateDirect` exceeded `-XX:MaxDirectMemorySize` (which defaults
to roughly `-Xmx`).
    CAUSES: Netty, NIO, or any library buffering off-heap without releasing. Direct buffers are freed
    only when their `Cleaner` runs, which requires the buffer object to be COLLECTED — so a heap that
    is comfortable can starve off-heap memory by never bothering to collect.
    CONFIRM: `-XX:NativeMemoryTracking=summary` then `jcmd <pid> VM.native_memory summary`.

`Requested array size exceeds VM limit` — an array larger than roughly `Integer.MAX_VALUE - 8`. This is
NOT a heap problem; the array simply cannot be indexed by an `int`. The fix is chunking or a different
data structure.

`Compressed class space` — the fixed 1 GB region for compressed class pointers is full. Raise
`-XX:CompressedClassSpaceSize`, or fix the class explosion causing it.

`Out of swap space?` — a native `malloc` failed. The JVM is often the victim rather than the cause; look
at whole-machine memory, other processes, and native libraries.

AND THE CONTAINER KILL, WHICH LOOKS LIKE NONE OF THESE: exit code 137, no Java output at all. The kernel
killed the process because RSS exceeded the cgroup limit. `kubectl describe pod` shows `OOMKilled`. The
fix is `-XX:MaxRAMPercentage=70` and accounting for the non-heap pools — NOT raising `-Xmx`, which is
what everyone tries first and which makes it happen sooner.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — RAISING `-Xmx` FOR A RETENTION LEAK. It delays the failure and makes the eventual heap dump
larger and slower to analyse. The old-gen-after-full-GC chart tells you not to.

CASE 2 — RAISING `-Xmx` FOR `unable to create new native thread`. Actively harmful: less memory remains
for the ~1 MB each thread reserves.

CASE 3 — `-Xmx` EQUAL TO THE CONTAINER LIMIT. Guarantees an OOM-kill, because metaspace, stacks, code
cache, GC structures and direct buffers all live outside `-Xmx`.

CASE 4 — RAISING `-Xmx` ABOVE ~32 GB. Compressed ordinary object pointers are lost, every reference
doubles from 4 to 8 bytes, and EFFECTIVE CAPACITY CAN FALL. A 31 GB heap can hold more objects than a
33 GB one.

CASE 5 — CATCHING `OutOfMemoryError`. The allocation that failed is often unrelated to the cause, other
threads are about to fail, and the handler itself may need to allocate.

CASE 6 — DISABLING `UseGCOverheadLimit`. Converts a diagnosable crash into an application that spends
98% of its CPU in GC and looks merely "slow" for hours.

CASE 7 — A CLASSLOADER LEAK AFTER REDEPLOY. One `ThreadLocal`, one static registry entry, or one
un-deregistered JDBC driver holds the old loader, retaining every class it loaded. Metaspace fills after
N redeploys, and the heap looks fine throughout.

CASE 8 — DIRECT BUFFERS FREED ONLY BY GC. A `Cleaner` runs when the buffer object is collected, so a
comfortable heap that rarely collects can starve off-heap memory. `System.gc()` is the traditional
desperate remedy, which tells you how awkward the coupling is.

CASE 9 — NO HEAP DUMP CONFIGURED. The OOM happened, the pod restarted, and the evidence is gone.
`-XX:+HeapDumpOnOutOfMemoryError` costs nothing until it fires.

CASE 10 — A HEAP DUMP THAT WILL NOT FIT. Dumping a 32 GB heap needs 32 GB of disk and a machine with
enough memory to open it. Plan the path and the tooling before you need them.

CASE 11 — READING `size()` OR `Runtime.freeMemory()` AS TRUTH. `freeMemory` is free space in the CURRENT
heap, not the maximum; it drops and recovers constantly and tells you almost nothing on its own.

CASE 12 — AN OLD JVM IN A CONTAINER. Pre-8u191 JVMs size the heap from the HOST's memory, ignoring the
cgroup limit entirely, and are killed with no Java-level error.

CASE 13 — ASSUMING A THREAD DUMP SHOWS MEMORY. It shows threads. For memory you need a heap dump, GC
logs, or Native Memory Tracking — three different tools for three different pools.""",

"""5. THE ALTERNATIVES — the tool for each pool

FOR HEAP: a heap dump plus ECLIPSE MAT. Open the DOMINATOR TREE and the LEAK SUSPECTS report. The
dominator tree answers "what is retaining this", which is the only useful question — "what is largest"
almost never is. `jcmd <pid> GC.heap_dump /path`, or `jmap` on older JVMs.

FOR ALLOCATION RATE: JFR (`-XX:StartFlightRecording`) or async-profiler in allocation mode. These tell
you WHICH CALL SITE is producing garbage, which is what you fix when the problem is churn rather than
retention.

FOR GC BEHAVIOUR: `-Xlog:gc*:file=gc.log:time,uptime,level,tags` and GCeasy or GCViewer. The one chart
that matters is old-generation occupancy after each full collection.

FOR NATIVE MEMORY: `-XX:NativeMemoryTracking=summary` then `jcmd <pid> VM.native_memory summary`. It
breaks RSS down by category — heap, class, thread, code, GC, internal — and is the only way to explain
"the heap is 1 GB and RSS is 3 GB".

FOR CLASSES AND METASPACE: `jcmd <pid> VM.metaspace`, `jstat -class <pid> 1s`, and MAT's duplicate-class
analysis, which finds the same class loaded by several loaders — the classloader-leak signature.

FOR THREADS: `jstack` or `jcmd Thread.print`, grouped by thread name. Which is why naming your threads
matters.

PREVENTIVE FLAGS TO SET EVERYWHERE, BEFORE YOU NEED THEM:
    -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps
    -XX:+ExitOnOutOfMemoryError            (so the orchestrator restarts a broken JVM)
    -XX:MaxRAMPercentage=70                (instead of a hard-coded -Xmx, in a container)
    -Xlog:gc*:file=gc.log:...              (nearly free, and you cannot reconstruct it later)

DESIGN-LEVEL FIXES, WHICH BEAT ALL OF THE ABOVE:
    STREAM INSTEAD OF MATERIALISING. Paginate queries, stream file processing, write to an
    `OutputStream` rather than building a 500 MB `String`. THIS CONVERTS AN O(n) MEMORY REQUIREMENT
    INTO O(1) AND IS USUALLY THE REAL FIX.
    BOUND EVERY CACHE. Caffeine or Guava with `maximumSize` and expiry. An unbounded cache is a memory
    leak with a schedule.
    BOUND EVERY QUEUE. An unbounded work queue turns overload into an OOM instead of backpressure.
    CLEAR `ThreadLocal`s IN A `finally`. Pooled threads never die.
    DEREGISTER LISTENERS. Symmetry between register and unregister is the fix for most retention leaks.

WHAT TO SAY: "First I read the message after the colon, because four of the eight mean the heap is fine.
Then I check old-gen occupancy after successive full GCs — if it climbs, it is a leak and no flag helps,
so I take a heap dump and read the dominator tree. And in a container I would check for an OOM-kill
first, because exit 137 with no Java error is not an OutOfMemoryError at all."

""",

"""6. HOW TO DIAGNOSE ONE — numbered steps

STEP 1 — READ THE TEXT AFTER THE COLON. Four of the eight messages mean the heap is not the problem.

STEP 2 — IF THERE IS NO JAVA ERROR AT ALL, CHECK FOR AN OOM-KILL. Exit 137, `kubectl describe pod`,
`dmesg`. The kernel killed the process; the JVM never got to complain.

STEP 3 — FOR A HEAP MESSAGE, PLOT OLD-GEN OCCUPANCY AFTER EACH FULL GC. Climbing means a leak; a stable
floor means capacity or allocation rate.

STEP 4 — FOR A LEAK, TAKE A HEAP DUMP AND OPEN THE DOMINATOR TREE. Ask what RETAINS the largest object,
not what is largest.

STEP 5 — FOR CAPACITY, LOOK AT ALLOCATION RATE BEFORE RAISING THE LIMIT. JFR or async-profiler in
allocation mode names the call site.

STEP 6 — FOR `unable to create new native thread`, COUNT THREADS AND CHECK `ulimit -u`. Do NOT raise
`-Xmx`; it makes this worse.

STEP 7 — FOR `Metaspace`, WATCH THE LOADED-CLASS COUNT OVER TIME. A rising count under a stable workload
means a classloader leak or runtime class generation.

STEP 8 — FOR `Direct buffer memory`, TURN ON NATIVE MEMORY TRACKING and look at the "Internal" and
"Other" categories.

STEP 9 — IN A CONTAINER, SET `-XX:MaxRAMPercentage=70` RATHER THAN A HARD `-Xmx`, and account for
stacks, metaspace, code cache and GC structures.

STEP 10 — NEVER CATCH `OutOfMemoryError`. Configure `-XX:+HeapDumpOnOutOfMemoryError` and
`-XX:+ExitOnOutOfMemoryError` instead: capture the evidence, die cleanly, let the orchestrator restart.

STEP 11 — CHECK WHETHER THE FIX IS TO STREAM. Paginating a query or streaming a file turns an O(n)
memory requirement into O(1) and is usually the real answer.

STEP 12 — BOUND EVERY CACHE AND EVERY QUEUE. Both are leaks with a schedule.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The first thing I'd say is that "out of memory" isn't one problem, and the text AFTER the colon is the
diagnosis. Everyone reads OutOfMemoryError as "heap full, raise -Xmx", and that's right for one message
and actively wrong for most of the others.

"Java heap space" and "GC overhead limit exceeded" are the heap — the second is the same problem
detected earlier, when more than 98% of recent time went into GC while recovering less than 2% of the
heap. That check is a GIFT, by the way: without it the application wouldn't fail, it would grind for
hours looking merely slow. Disabling it is almost always the wrong instinct.

But "Metaspace" is class metadata in native memory, unbounded by default. "unable to create new native
thread" means the OPERATING SYSTEM refused — the heap is fine, and raising -Xmx makes it WORSE, because
each thread reserves about a megabyte and a bigger heap leaves less room. "Direct buffer memory" is
off-heap NIO. "Requested array size exceeds VM limit" just means you asked for an array bigger than an
int can index. Four of the eight messages occur with a heap that's barely used.

The mental model I'd offer is that -Xmx bounds ONE of at least seven pools. Heap, metaspace, compressed
class space, thread stacks at ~1 MB reserved each, the code cache at ~240 MB reserved, GC structures at
5-10% of heap, and direct buffers. Total RSS is heap PLUS all of that, and "all of that" is routinely
500 MB to a gigabyte on a real service. Which is why -Xmx equal to the container limit guarantees an
OOM-kill, and why the answer in a container is MaxRAMPercentage around 70 rather than a hard -Xmx.

And there's a ninth failure that isn't an OutOfMemoryError at all, and is the most common one now: the
container OOM-kill. The kernel kills the process when RSS exceeds the cgroup limit. Exit 137, no Java
error, no stack trace, no heap dump — just a process that vanished. The JVM never got to complain,
because the heap wasn't full; everything else was.

For diagnosis, the single most useful thing takes thirty seconds: look at old-generation occupancy
IMMEDIATELY AFTER each full GC. If that number climbs monotonically across successive full collections,
you have a retention leak — more memory only delays it and no flag helps, so take a heap dump and read
the DOMINATOR TREE, which answers "what is retaining this" rather than "what is largest". If it returns
to the same floor each time and the peaks are just too high, it's capacity or allocation rate, and more
heap or less allocation genuinely helps.

Two practical things. Never catch OutOfMemoryError — the allocation that failed is often unrelated to
the cause, other threads are about to fail, and your handler may need to allocate. Configure
HeapDumpOnOutOfMemoryError and ExitOnOutOfMemoryError instead: capture the evidence and die cleanly. And
before tuning anything, check whether the fix is to STREAM — paginating a query or streaming a file
turns an O(n) memory requirement into O(1), and that's usually the real answer.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE MESSAGE IS THE DIAGNOSIS ────────────────────────────────────
    // java.lang.OutOfMemoryError: Java heap space            ← the heap
    // java.lang.OutOfMemoryError: GC overhead limit exceeded ← the heap, earlier
    // java.lang.OutOfMemoryError: Metaspace                  ← CLASS metadata, native
    // java.lang.OutOfMemoryError: unable to create new native thread
    //                                                        ← the OS refused. Heap fine.
    // java.lang.OutOfMemoryError: Direct buffer memory       ← OFF-heap NIO. Heap fine.
    // java.lang.OutOfMemoryError: Requested array size exceeds VM limit
    //                                                        ← > Integer.MAX_VALUE-ish
    // java.lang.OutOfMemoryError: Compressed class space     ← the fixed 1 GB region
    // java.lang.OutOfMemoryError: Out of swap space?         ← a native malloc failed
    //
    // (and) exit code 137, NO Java output at all             ← the KERNEL killed you

    // ── WHY -Xmx == CONTAINER LIMIT ALWAYS DIES ─────────────────────────
    // container limit: 2048 MB
    // -Xmx2g          → heap alone may reach 2048 MB
    //   + metaspace           ~100 MB
    //   + 200 threads × 1 MB  ~200 MB reserved stacks
    //   + code cache          up to 240 MB reserved
    //   + GC structures       ~5-10% of heap
    //   + direct buffers      whatever Netty wants
    //   = RSS well past 2048 → OOMKilled, exit 137, no heap dump, no stack trace
    // -XX:MaxRAMPercentage=70   ← say this instead of a hard-coded -Xmx

    // ── THE THIRTY-SECOND DIAGNOSIS ─────────────────────────────────────
    // [gc] Pause Full ... 1900M->420M(2G)     ← after full GC: 420 MB
    // [gc] Pause Full ... 1950M->710M(2G)     ← after full GC: 710 MB
    // [gc] Pause Full ... 1990M->1180M(2G)    ← after full GC: 1180 MB
    //                              ^^^^ THE FLOOR IS CLIMBING → RETENTION LEAK.
    //   More heap only delays it. No flag helps. Take a heap dump.
    // [gc] Pause Full ... 1900M->418M(2G)
    // [gc] Pause Full ... 1930M->421M(2G)     ← STABLE FLOOR → capacity or allocation
    //   rate. More heap, or less allocation, genuinely helps.

    // ── THE ONE THAT GETS RAISED THE WRONG WAY ──────────────────────────
    // OutOfMemoryError: unable to create new native thread
    for (Request r : requests) {
        Executors.newFixedThreadPool(4).submit(() -> handle(r));
    //  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ A NEW POOL PER REQUEST, never shut down.
    //  4 non-daemon threads each, forever. The heap is barely touched.
    }
    // RAISING -Xmx MAKES THIS WORSE: each thread RESERVES ~1 MB outside the heap, so
    // a bigger heap leaves less room for stacks. Count threads with jstack instead.

    // ── THE CLASSLOADER LEAK ────────────────────────────────────────────
    // OutOfMemoryError: Metaspace, after the 9th redeploy
    static final ThreadLocal<Ctx> CTX = new ThreadLocal<>();   // never remove()d
    // ^ a pooled container thread holds a Ctx → whose class → whose CLASSLOADER →
    //   which retains EVERY CLASS THE OLD WEBAPP EVER LOADED. Ten redeploys, ten
    //   complete copies of the application's classes in metaspace. The heap looks
    //   fine the whole time.
    // Tell: jstat -class <pid> 1s shows the loaded-class count RISING under a stable
    //       workload.

    // ── DIRECT BUFFERS: freed only when the GC bothers ──────────────────
    ByteBuffer buf = ByteBuffer.allocateDirect(64 * 1024 * 1024);
    // ^ 64 MB OFF the heap. It is released when buf's Cleaner runs — which requires
    //   buf to be COLLECTED. A comfortable heap that rarely collects can therefore
    //   starve off-heap memory while showing plenty of free heap.
    // -XX:MaxDirectMemorySize=512m, and -XX:NativeMemoryTracking=summary to see it.

    // ── DO NOT DO THIS ──────────────────────────────────────────────────
    try { ... } catch (OutOfMemoryError e) { log.error("oom", e); }
    //                 ^^^^^^^^^^^^^^^^^ the allocation that failed is often unrelated
    //   to the cause, other threads are about to fail, and log.error may itself need
    //   to allocate. Configure this instead:
    // -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps
    // -XX:+ExitOnOutOfMemoryError      ← capture the evidence, die, let the
    //                                     orchestrator restart a JVM you cannot trust""",

"""9. THE TRACE — the same symptom, four different causes

A SERVICE FAILS AFTER SIX HOURS. Four investigations, all starting from "it ran out of memory":

    INVESTIGATION 1 — `Java heap space`, floor climbing
    evidence                                          conclusion
    ---------------------------------------------------------------------------------
    post-full-GC old gen: 420 → 710 → 1180 MB          RETENTION LEAK
    heap dump, dominator tree: a static ConcurrentHashMap
      retains 1.1 GB across 2.4 million entries
    the map is a cache with no eviction                the fix is `maximumSize`, not
                                                       `-Xmx`
    ---------------------------------------------------------------------------------
    RAISING -Xmx WOULD HAVE MOVED THE FAILURE FROM SIX HOURS TO TWELVE and doubled the size of the heap
    dump you eventually had to analyse.

    INVESTIGATION 2 — `unable to create new native thread`, heap at 12%
    evidence                                          conclusion
    ---------------------------------------------------------------------------------
    heap usage 240 MB of 2 GB                          THE HEAP IS NOT THE PROBLEM
    jstack: 8,400 threads named "pool-N-thread-1"       a pool created per request and
                                                        never shut down
    each reserves ~1 MB of stack                        ~8 GB of stack reservation
    ---------------------------------------------------------------------------------
    THE INSTINCTIVE FIX MAKES IT WORSE. Raising `-Xmx` takes address space and RAM away from exactly
    the thing that failed. The real fix is one shared executor and a `shutdown()`.

    INVESTIGATION 3 — `Metaspace`, after the ninth redeploy
    evidence                                          conclusion
    ---------------------------------------------------------------------------------
    heap steady at 600 MB throughout                   NOT the heap
    jstat -class: loaded classes 42k → 61k → 79k …      classes accumulating
    MAT duplicate-class analysis: 9 copies of           CLASSLOADER LEAK — nine old
      com.example.Service, each from a different        webapp loaders still reachable
      loader
    the retaining path: a pooled thread's ThreadLocal
    ---------------------------------------------------------------------------------
    NINE COMPLETE COPIES OF THE APPLICATION'S CLASSES. One un-removed `ThreadLocal` on a thread that
    never dies retained a whole class loader, which retains every class it ever defined.

    INVESTIGATION 4 — no Java error at all
    evidence                                          conclusion
    ---------------------------------------------------------------------------------
    the pod restarted; exit code 137                   THE KERNEL KILLED IT
    no stack trace, no heap dump, no GC log entry      the JVM never got to react
    kubectl describe pod: OOMKilled                    RSS exceeded the cgroup limit
    -Xmx2g with a 2 GB container limit                 heap + metaspace + 200 stacks +
                                                       code cache + GC structures
    ---------------------------------------------------------------------------------
    THERE IS NO `OutOfMemoryError` HERE AND THERE NEVER WILL BE. The heap was never full; everything
    outside it was. Searching the application logs for "OutOfMemoryError" finds nothing, which is why
    this one is so often misdiagnosed as a crash or a liveness-probe failure.

NOW THE POOL BREAKDOWN THAT EXPLAINS INVESTIGATION 4 — `jcmd VM.native_memory summary` on a healthy
service with `-Xmx1g`:

    category            reserved     committed    what it is
    ---------------------------------------------------------------------------------
    Java Heap           1024 MB      1024 MB      -Xmx. The only pool most people know.
    Class               1100 MB       120 MB      metaspace + compressed class space
    Thread               420 MB        30 MB      ~1 MB reserved per thread
    Code                 240 MB        60 MB      JIT-compiled machine code
    GC                    80 MB        70 MB      card tables, mark bitmaps
    Internal / Other     variable     variable    direct buffers, JNI, symbols
    ---------------------------------------------------------------------------------
    RSS ≈ 1024 + 120 + 30 + 60 + 70 + … ≈ 1.4 GB FOR A 1 GB HEAP. Committed is what counts against the
    container; reserved is address space. THE GAP BETWEEN `-Xmx` AND RSS IS NOT A LEAK, IT IS THE
    NORMAL SHAPE OF A JVM, and budgeting for it is the whole content of `MaxRAMPercentage`.

WHAT PRODUCED WHAT:
    SEPARATE POOLS         produced investigations 2, 3 and 4 — three failures with a healthy heap.
    THE POST-FULL-GC FLOOR produced the leak-versus-capacity answer in thirty seconds.
    REACHABILITY           produced the classloader leak: one ThreadLocal, nine copies of everything.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `-Xmx` bounds the HEAP only. RSS ≈ heap + metaspace + thread stacks (~1 MB reserved each) + code
    cache (~240 MB reserved) + GC structures (5–10% of heap) + direct buffers.
    Metaspace is native and UNBOUNDED by default; `-XX:MaxMetaspaceSize` bounds it.
    Compressed class space is a fixed 1 GB region when compressed oops are on.
    Above ~32 GB compressed oops are lost and every reference doubles in size.
    `GC overhead limit exceeded`: >98% of time in GC recovering <2% of heap.
    Max array length is roughly `Integer.MAX_VALUE - 8`.
    Container OOM-kill: exit 137, no Java error, no heap dump.

THE #1 MISTAKE: reading `OutOfMemoryError` without the message after the colon. Four of eight mean the
heap is fine.

THE #2 MISTAKE: raising `-Xmx` for a retention leak. It delays failure and enlarges the dump.

THE #3 MISTAKE: raising `-Xmx` for `unable to create new native thread`. Actively harmful.

THE #4 MISTAKE: `-Xmx` equal to the container limit. Guarantees an OOM-kill.

THE #5 MISTAKE: raising `-Xmx` past ~32 GB. Compressed oops are lost and effective capacity can fall.

THE #6 MISTAKE: catching `OutOfMemoryError`. The failed allocation is often unrelated to the cause and
the handler may need to allocate.

THE #7 MISTAKE: disabling `UseGCOverheadLimit`. It turns a diagnosable crash into hours of grinding.

THE #8 MISTAKE: not configuring `-XX:+HeapDumpOnOutOfMemoryError`. It costs nothing until it fires, and
without it the pod restarts and the evidence is gone.

THE #9 MISTAKE: searching for the LARGEST object in a heap dump. Ask what RETAINS it — that is what the
dominator tree is for.

THE #10 MISTAKE: ignoring the loaded-class count. A rising count under a stable workload is a
classloader leak, and the heap will look healthy throughout.

THE #11 MISTAKE: treating a thread dump as a memory tool. Three pools, three tools: heap dump, GC log,
Native Memory Tracking.

THE #12 MISTAKE: tuning before checking whether the fix is to STREAM. Paginating or streaming converts
O(n) memory into O(1).

ONE-SENTENCE TAKEAWAY: `OutOfMemoryError` is eight different failures wearing one name, and the text
after the colon is the diagnosis — `Metaspace`, `unable to create new native thread`, `Direct buffer
memory` and `Requested array size` all occur with a nearly-empty heap, and raising `-Xmx` makes the
thread one WORSE because each thread reserves about a megabyte outside the heap; `-Xmx` bounds only one
of at least seven pools, so total RSS is routinely 40% above it, which is why `-Xmx` equal to a container
limit guarantees a kernel OOM-kill that produces exit 137 and no Java error at all; and the thirty-second
triage is to plot OLD-GENERATION OCCUPANCY AFTER EACH FULL GC — climbing means a retention leak that no
flag will fix, so take a heap dump and read the dominator tree, while a stable floor means capacity or
allocation rate, where more heap or less allocation genuinely helps.""",
]


DEEP["Class loading and the parent-delegation model"] = [
"""1. THE GOAL IN PLAIN ENGLISH — how a class gets from a file into the running program

Java does not load your whole program at startup. A class arrives the first time it is actually needed,
in three phases:

    LOADING          find the bytes for `com.example.Foo`, and turn them into a `Class` object.
    LINKING          VERIFY the bytecode is well-formed and safe, PREPARE static fields with their
                     default values, and RESOLVE symbolic references to other types.
    INITIALISATION   run the static initialisers — `<clinit>`. Once, ever.

    THE VERIFY STEP IS WHY JAVA IS MEMORY-SAFE. Before any bytecode runs, the verifier checks that the
    stack cannot underflow, that types match, that jumps land inside the method, and that a local
    holding an `int` is never used as a reference. That check is what makes it impossible for pure Java
    bytecode to corrupt memory the way C can — the safety is in the LOADER, not only in the language.

THE PART WITH THE NAME — PARENT DELEGATION — IS ABOUT WHO FINDS THE BYTES:

    WHEN A CLASS LOADER IS ASKED FOR A CLASS, IT ASKS ITS PARENT FIRST, and only looks itself if the
    parent cannot supply it. The chain runs Application → Platform → Bootstrap, and the bootstrap loader
    holds the JDK's own classes.

    SO IF YOU PUT YOUR OWN `java/lang/String.class` ON THE CLASSPATH, IT IS NEVER USED. The request
    reaches the bootstrap loader first, which has a `String`, and returns it. YOUR VERSION IS NEVER
    CONSULTED. That is the security property: a jar on the classpath cannot replace a core class, so it
    cannot rewrite `String` to leak passwords or `ClassLoader` to disable its own checks.

THE EVERYDAY VERSION: an office where any request for a form goes up the chain of command first. If head
office has that form, theirs is used, full stop. A local team can invent new forms nobody upstairs has,
but they can never override the official one — which is annoying occasionally and is exactly the point.

TERMS AS THEY APPEAR:
- BOOTSTRAP LOADER: native, loads the core JDK. `getClassLoader()` on `String` returns `null`.
- PLATFORM LOADER: JDK modules outside the core. (Before Java 9 it was the "extension" loader.)
- APPLICATION / SYSTEM LOADER: your classpath.
- DEFINING LOADER: the loader that actually created the `Class` object. Remember this one — it is half
  of a class's identity.""",

"""2. THE INTUITION — a class's identity includes its loader, and that explains everything strange

HERE IS THE FACT THAT MAKES SENSE OF EVERY CONFUSING CLASSLOADER ERROR:

    A CLASS IS IDENTIFIED BY (FULLY QUALIFIED NAME, DEFINING CLASS LOADER). Not by name alone.

    So `com.example.Foo` loaded by loader A and `com.example.Foo` loaded by loader B are TWO DIFFERENT
    CLASSES. Not two copies — two distinct types, as unrelated as `String` and `Integer`. They have
    separate static fields. An instance of one cannot be assigned to a variable of the other.

    WHICH PRODUCES THE MOST BAFFLING ERROR MESSAGE IN JAVA:

        java.lang.ClassCastException: com.example.Foo cannot be cast to com.example.Foo

    People assume the logs are broken. They are not — those are genuinely different classes with the
    same name, and the JVM has no better way to say so. The fix is always to work out which two loaders
    are involved and why one of them saw the class it should have delegated for.

NOW THE THREE THINGS DELEGATION BUYS, in order of importance:

    SECURITY. Core classes cannot be shadowed. A malicious jar cannot supply its own `java.lang.String`,
    `java.lang.ClassLoader`, or `java.security.*`. (The JVM ALSO refuses to define any class in a
    `java.*` package from a non-bootstrap loader, so the protection is belt and braces.)
    CONSISTENCY. Everyone gets the SAME `java.lang.String` class, so instances pass freely between
    libraries. Without delegation, two libraries could each load their own `String` and nothing would
    interoperate.
    NON-DUPLICATION. A class is loaded once per loader, and delegation makes "once" the common case.

AND THE PLACES DELEGATION IS DELIBERATELY BROKEN, which is where the interesting engineering is:

    APPLICATION SERVERS INVERT IT. Tomcat's webapp loader is CHILD-FIRST for application classes: it
    looks in `WEB-INF/lib` BEFORE asking its parent, so your bundled version of a library wins over the
    server's. Without that, every webapp would be forced onto the container's dependency versions. It
    still delegates `java.*` upward, because that part is not negotiable.
    OSGi AND THE MODULE SYSTEM use a graph rather than a chain, so a bundle sees exactly the packages it
    declares — allowing two versions of the same library to coexist in one JVM.
    SERVICE PROVIDER INTERFACES BREAK IT FROM THE OTHER DIRECTION, and this is the subtle one. JDBC's
    `DriverManager` is a BOOTSTRAP class, and it must load a driver that lives on the APPLICATION
    classpath — but the bootstrap loader can only delegate upward, and there is nothing above it. THE
    ESCAPE HATCH IS THE THREAD CONTEXT CLASS LOADER: a per-thread loader reference that a core class can
    reach down through. `ServiceLoader`, JNDI, JAXP and most frameworks depend on it, and "it works in
    my IDE and not in the container" is very often a context-loader problem.""",

"""3. THE MECHANISM — the hierarchy, the two errors, and the leak

THE HIERARCHY SINCE JAVA 9:

    BOOTSTRAP (null)      java.base and the core modules. Written in native code, which is why
                          `String.class.getClassLoader()` returns `null` rather than an object.
       ↑
    PLATFORM              other JDK modules — `java.sql`, `java.xml`, and so on. Replaced the old
                          "extension" loader, which used to load anything dropped into `lib/ext` and
                          was removed precisely because that was a security hazard.
       ↑
    APPLICATION / SYSTEM  your classpath and module path. `getSystemClassLoader()`.
       ↑
    CUSTOM                yours, or a framework's.

`loadClass` IS FIVE LINES, and reading them is the whole model:

    protected Class<?> loadClass(String name, boolean resolve) {
        Class<?> c = findLoadedClass(name);        // 1. already loaded by ME?
        if (c == null) {
            try { c = parent.loadClass(name); }     // 2. ASK THE PARENT FIRST
            catch (ClassNotFoundException ignored) { }
            if (c == null) c = findClass(name);     // 3. only now, look myself
        }
        return c;
    }

    TO WRITE A CUSTOM LOADER YOU OVERRIDE `findClass`, NOT `loadClass` — which keeps delegation intact.
    Overriding `loadClass` is how you deliberately invert it, and it is what an application server does.

THE TWO ERRORS PEOPLE CONFUSE, and the distinction is precise:

    `ClassNotFoundException` — a CHECKED EXCEPTION, thrown when code EXPLICITLY asks for a class by name
    and it is not there: `Class.forName("com.foo.Bar")`, `loader.loadClass(...)`. YOU asked; the answer
    is no.
    `NoClassDefFoundError` — an ERROR, thrown by the JVM when a class that was present AT COMPILE TIME
    is missing at RUNTIME... OR, and this is the case that wastes days, when the class was FOUND but its
    initialisation ALREADY FAILED EARLIER. The message reads `Could not initialize class Foo` and the
    real cause was a single `ExceptionInInitializerError`, possibly hours ago, possibly on another
    thread. ALWAYS SEARCH FOR THE FIRST OCCURRENCE.

THE CLASSLOADER LEAK, which is the operational reason this topic matters:

    A `Class` object holds a reference to its DEFINING LOADER. A loader holds every class it has
    defined. So ANY ONE reference to ANY ONE class from a loader keeps the ENTIRE loader — and every
    class it ever loaded — alive.

    REDEPLOY A WEB APPLICATION AND THE OLD LOADER SHOULD BECOME GARBAGE. It does not if anything outside
    it still points in. The usual culprits are all core-JDK statics that outlive the webapp:
        a `ThreadLocal` on a pooled container thread holding an application object;
        a JDBC driver still registered with `DriverManager`;
        a shutdown hook, a `Timer`, or a thread the application started and never stopped;
        a listener in a static registry;
        an application class used as a key in a JDK-level cache.
    TEN REDEPLOYS, TEN COMPLETE COPIES OF THE APPLICATION'S CLASSES, and an `OutOfMemoryError:
    Metaspace` with a perfectly healthy heap.

HIDDEN CLASSES (Java 15) are the modern mechanism for runtime-generated classes — lambdas, records'
generated members, and frameworks. They are not discoverable by name, are tied to a host class, and can
be unloaded independently, which avoids exactly the retention problem above.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `ClassCastException: com.example.Foo cannot be cast to com.example.Foo`. Two loaders, two
distinct classes with the same name. The message is correct and looks like a logging bug.

CASE 2 — `NoClassDefFoundError: Could not initialize class X`. The class exists. Its `<clinit>` failed
earlier and the class is permanently marked erroneous. Find the first `ExceptionInInitializerError`.

CASE 3 — `ClassNotFoundException` VS `NoClassDefFoundError` TREATED AS THE SAME THING. The first means
you asked by name and it is absent; the second means the JVM needed it and it was absent OR poisoned.

CASE 4 — A CLASSLOADER LEAK ON REDEPLOY. One `ThreadLocal`, one registered driver, one un-stopped
thread, and every class the old application loaded is retained.

CASE 5 — TWO VERSIONS OF THE SAME LIBRARY ON THE CLASSPATH. The classpath is ORDER-DEPENDENT: the first
match wins, silently. `NoSuchMethodError` at runtime for a method that plainly exists in the jar you
think you are using is the signature of this.

CASE 6 — A LIBRARY BUNDLED IN A WEBAPP THAT THE CONTAINER ALSO PROVIDES. Child-first delegation gives
you yours; a different container may delegate parent-first and give you theirs. Same war file, different
behaviour.

CASE 7 — `Class.forName(name)` VS `Class.forName(name, false, loader)`. The first INITIALISES the class;
the three-argument version does not. If a driver registers itself in a static block, the difference is
whether it registers at all.

CASE 8 — THE THREAD CONTEXT CLASS LOADER BEING WRONG. A framework calls
`Thread.currentThread().getContextClassLoader()` and gets a loader that cannot see your classes. Very
often the cause of "works in my IDE, fails in the container".

CASE 9 — CALLING `getClassLoader()` ON A CORE CLASS AND GETTING `null`. That is the bootstrap loader,
not an error. `String.class.getClassLoader()` is `null` by specification.

CASE 10 — LOADING A RESOURCE WITH THE WRONG LEADING SLASH.
`getClass().getResourceAsStream("config.properties")` is relative to the class's PACKAGE;
`"/config.properties"` is from the classpath root; and `getClassLoader().getResourceAsStream(...)` never
takes a leading slash. Three near-identical calls with three different meanings.

CASE 11 — FAT JARS AND SHADED DEPENDENCIES. Two shaded copies of the same library under different
package names are two unrelated sets of classes, and objects cannot pass between them.

CASE 12 — SPLIT PACKAGES UNDER THE MODULE SYSTEM. The same package supplied by two modules is an error
at startup, where the old classpath silently picked one.

CASE 13 — ASSUMING CLASSES ARE UNLOADED. A class is only unloaded when its ENTIRE loader is unreachable.
For the application loader, that is never.""",

"""5. THE ALTERNATIVES — when you actually need a custom loader, and what to do instead

MOST CODE SHOULD NEVER WRITE A CLASS LOADER. The legitimate reasons are few:

    PLUGIN ISOLATION — each plugin in its own loader, so plugins can carry conflicting library versions
    and can be unloaded by dropping the loader.
    HOT RELOAD — load a new version into a new loader and discard the old one. This is what an
    application server's redeploy is, and why the leak above matters so much.
    INSTRUMENTATION — `java.lang.instrument` agents transforming bytecode as it loads. This is how
    profilers, APM tools and coverage tools work, and it is the supported route rather than a custom
    loader.
    LOADING FROM SOMEWHERE UNUSUAL — a database, an encrypted archive, over a network.

IF YOU DO WRITE ONE: OVERRIDE `findClass`, NOT `loadClass`, so delegation is preserved. Override
`loadClass` only when you deliberately want child-first, and even then always delegate `java.*` upward.

BETTER ANSWERS FOR THE COMMON PROBLEMS:

    "TWO LIBRARY VERSIONS CONFLICT" → fix the dependency tree first. `mvn dependency:tree` or
    `gradle dependencies`, then exclusions or a BOM. SHADING (relocating a library into your own package
    namespace) is the next option, and separate loaders is the last.
    "I WANT PLUGINS" → `ServiceLoader` plus the module system, or an established framework. `ServiceLoader`
    handles the context-loader question for you.
    "I WANT TO RELOAD CODE IN DEVELOPMENT" → Spring DevTools, JRebel, or simply restarting. Hand-rolled
    hot reload is a large amount of subtle work.
    "I NEED TO GENERATE CLASSES AT RUNTIME" → ByteBuddy or the ASM library, and prefer HIDDEN CLASSES
    (Java 15+) so the generated class can be unloaded with its host rather than retained forever.

FOR RESOURCES, THE THREE FORMS, since this is where people actually get bitten:
    `getClass().getResourceAsStream("x.properties")`   relative to the class's PACKAGE
    `getClass().getResourceAsStream("/x.properties")`  from the classpath ROOT
    `getClass().getClassLoader().getResourceAsStream("x.properties")`   root, and NO leading slash

FOR THE SPI PROBLEM: use `ServiceLoader`, or accept a `ClassLoader` parameter in your API rather than
reaching for the thread context loader implicitly. Making the loader an explicit argument turns a
mysterious environment-dependent failure into a visible one.

WHAT TO SAY: "Delegation means a loader asks its parent first, which is why you cannot replace
`java.lang.String` and why every library sees the same one. The fact that matters operationally is that
a class's identity is (name, defining loader) — so the same class from two loaders is two unrelated
types, which is where `Foo cannot be cast to Foo` comes from, and it is why a single lingering
`ThreadLocal` after a redeploy retains an entire application's worth of classes."

""",

"""6. HOW TO DIAGNOSE CLASSLOADING PROBLEMS — numbered steps

STEP 1 — DISTINGUISH THE TWO ERRORS. `ClassNotFoundException` means you asked by name and it was absent.
`NoClassDefFoundError` means the JVM needed it and it was absent — or its initialisation already failed.

STEP 2 — IF THE MESSAGE SAYS "Could not initialize class", STOP LOOKING AT THE CLASSPATH. Search the log
for the first `ExceptionInInitializerError`; that is the real failure.

STEP 3 — FOR `Foo cannot be cast to Foo`, PRINT THE LOADERS.
`obj.getClass().getClassLoader()` on both sides, and `System.identityHashCode` on each. You are looking
for two different loaders.

STEP 4 — FOR "WHICH JAR DID THIS COME FROM", USE
`Foo.class.getProtectionDomain().getCodeSource().getLocation()`, or run with `-verbose:class`.

STEP 5 — FOR `NoSuchMethodError` ON A METHOD THAT PLAINLY EXISTS, YOU HAVE TWO VERSIONS ON THE CLASSPATH.
The first match wins, silently. Check the dependency tree.

STEP 6 — FOR "WORKS IN MY IDE, FAILS IN THE CONTAINER", SUSPECT THE THREAD CONTEXT CLASS LOADER. Print
it and compare with `getClass().getClassLoader()`.

STEP 7 — FOR A METASPACE OOM AFTER REDEPLOYS, LOOK FOR A CLASSLOADER LEAK. MAT's duplicate-class
analysis shows the same class defined by several loaders; then find what retains the oldest one.

STEP 8 — CHECK THE USUAL RETAINERS: `ThreadLocal`s on pooled threads, registered JDBC drivers, threads
and timers the application started, shutdown hooks, entries in static registries.

STEP 9 — WHEN WRITING A LOADER, OVERRIDE `findClass`. Override `loadClass` only to invert delegation
deliberately, and always delegate `java.*` upward.

STEP 10 — PREFER `ServiceLoader` OVER `Class.forName` FOR PLUGGABILITY. It handles the context-loader
question and it is checked at build time by the module system.

STEP 11 — GET THE RESOURCE PATH FORM RIGHT. Leading slash with `Class`, no leading slash with
`ClassLoader`, and relative-to-package with neither.

STEP 12 — USE HIDDEN CLASSES OR AN ESTABLISHED LIBRARY FOR RUNTIME CODE GENERATION, so generated classes
can be unloaded rather than accumulating.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'A class arrives the first time it's needed, in three phases. LOADING finds the bytes and makes a Class
object. LINKING verifies the bytecode, prepares static fields with defaults, and resolves references.
INITIALISATION runs the static initialisers, once ever.

The verify step is worth pausing on, because it's why Java is memory-safe. Before any bytecode runs the
verifier checks the stack can't underflow, that types match, that jumps land inside the method, and that
a local holding an int is never used as a reference. That's what makes it impossible for pure Java
bytecode to corrupt memory the way C can — the safety is in the LOADER, not just the language.

Parent delegation is about who finds the bytes. When a loader is asked for a class it asks its PARENT
first, and only looks itself if the parent can't supply it. The chain is Application, then Platform,
then Bootstrap, and bootstrap has the JDK's own classes.

So if you put your own java/lang/String.class on the classpath, it's never used. The request reaches
bootstrap first, which has a String, and returns it. Yours is never consulted. That's the security
property: a jar can't replace a core class, so it can't rewrite String to leak passwords. And the
consistency property comes free — everyone gets the SAME String class, so instances pass freely between
libraries.

Now the fact that makes sense of every confusing classloader error: A CLASS IS IDENTIFIED BY ITS NAME
*AND* ITS DEFINING LOADER. Not by name alone. So com.example.Foo from loader A and com.example.Foo from
loader B are two DIFFERENT classes — not two copies, two distinct types, as unrelated as String and
Integer, with separate static fields. Which produces the most baffling message in Java:
"ClassCastException: com.example.Foo cannot be cast to com.example.Foo". People assume the logs are
broken. They aren't — those genuinely are different classes and the JVM has no better way to say it.

Delegation gets deliberately broken in two directions, and both are interesting. Application servers
INVERT it: Tomcat's webapp loader is child-first for application classes, so your bundled library
version wins over the container's — otherwise every webapp would be forced onto the container's
dependency versions. It still delegates java.* upward, because that part isn't negotiable. And service
provider interfaces break it from the other side: JDBC's DriverManager is a bootstrap class that has to
load a driver from the APPLICATION classpath, but bootstrap can only delegate upward and there's nothing
above it. The escape hatch is the THREAD CONTEXT CLASS LOADER — a per-thread reference a core class can
reach down through. "Works in my IDE, fails in the container" is very often that.

Operationally, the thing that bites is the classloader leak. A Class holds a reference to its defining
loader, and a loader holds every class it defined. So ONE reference to ONE class keeps the whole loader
and everything it ever loaded alive. Redeploy a webapp and the old loader should become garbage — it
doesn't if a ThreadLocal on a pooled container thread, or a registered JDBC driver, or a thread the app
started still points in. Ten redeploys, ten complete copies of the application's classes, and an
OutOfMemoryError: Metaspace with a perfectly healthy heap.'""",

"""8. THE CODE, LINE BY LINE

    // ── loadClass IS THE WHOLE MODEL, IN FIVE LINES ─────────────────────
    protected Class<?> loadClass(String name, boolean resolve) {
        Class<?> c = findLoadedClass(name);       // 1. have I already loaded it?
        if (c == null) {
            try { c = parent.loadClass(name); }   // 2. ASK THE PARENT FIRST
            catch (ClassNotFoundException ignored) { }
            if (c == null) c = findClass(name);   // 3. only now, look myself
        }
        return c;
    }
    // OVERRIDE findClass, NOT loadClass — that keeps delegation intact.
    // Override loadClass ONLY to invert it deliberately, as an app server does.

    // ── WHY YOU CANNOT REPLACE String ───────────────────────────────────
    // put your own java/lang/String.class on the classpath:
    //   app loader → asks PLATFORM → asks BOOTSTRAP → bootstrap HAS String → returns
    //   it. YOUR VERSION IS NEVER CONSULTED. (And the JVM separately refuses to
    //   define any class in a java.* package from a non-bootstrap loader.)
    System.out.println(String.class.getClassLoader());   // null — that is BOOTSTRAP,
    //                                                      not an error

    // ── THE MESSAGE THAT LOOKS LIKE A LOGGING BUG ───────────────────────
    // java.lang.ClassCastException:
    //     com.example.Foo cannot be cast to com.example.Foo
    //
    // A class's identity is (NAME, DEFINING LOADER). Two loaders → TWO DISTINCT
    // TYPES, as unrelated as String and Integer, with SEPARATE static fields.
    System.out.println(a.getClass().getClassLoader());   // ← print both
    System.out.println(b.getClass().getClassLoader());   //   to confirm

    // ── THE TWO ERRORS, PRECISELY ───────────────────────────────────────
    Class.forName("com.foo.Missing");     // → ClassNotFoundException (CHECKED)
    //                                       YOU asked by name. The answer is no.
    new SomeClassThatWasOnTheCompileClasspath();
    //                                    // → NoClassDefFoundError (an ERROR)
    //                                       the JVM needed it and it is absent...
    // ... OR the class is PRESENT and its <clinit> already failed:
    // NoClassDefFoundError: Could not initialize class Registry
    //   ^ STOP LOOKING AT THE CLASSPATH. Search the log for the FIRST
    //     ExceptionInInitializerError — possibly hours ago, possibly another thread.

    // ── THE SPI ESCAPE HATCH ────────────────────────────────────────────
    // DriverManager is a BOOTSTRAP class. It must load a driver from the APPLICATION
    // classpath. But bootstrap can only delegate UPWARD, and nothing is above it.
    ClassLoader cl = Thread.currentThread().getContextClassLoader();
    //               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ a per-thread loader
    //   reference a core class can reach DOWN through. ServiceLoader, JNDI and JAXP
    //   all rely on it, and a wrong one is the usual cause of "works in my IDE".
    ServiceLoader.load(Driver.class);      // ← prefer this; it handles the question

    // ── THE LEAK ────────────────────────────────────────────────────────
    // A Class holds its DEFINING LOADER. A loader holds EVERY class it defined.
    // So ONE reference to ONE class retains the ENTIRE loader and all its classes.
    static final ThreadLocal<AppContext> CTX = new ThreadLocal<>();  // never removed
    // ^ on a POOLED container thread that outlives the webapp:
    //   pooled thread → ThreadLocal value → AppContext → its Class → its LOADER →
    //   every class the old webapp ever loaded.
    // Ten redeploys → ten complete copies → OutOfMemoryError: Metaspace, with a
    // perfectly healthy HEAP.
    // Other usual retainers: a registered JDBC driver, a Timer or thread the app
    // started, a shutdown hook, an entry in a static registry.

    // ── THE THREE RESOURCE FORMS, WHICH ARE ALL DIFFERENT ───────────────
    getClass().getResourceAsStream("config.properties")    // relative to the PACKAGE
    getClass().getResourceAsStream("/config.properties")   // classpath ROOT
    getClass().getClassLoader().getResourceAsStream("config.properties")
    //                                              ^ root, and NO leading slash

    // ── WHERE DID THIS CLASS COME FROM? ─────────────────────────────────
    Foo.class.getProtectionDomain().getCodeSource().getLocation();
    // or run with -verbose:class""",

"""9. THE TRACE — one class request, and three ways it goes wrong

THE HAPPY PATH: application code references `com.example.Service` for the first time.

    step  who                          what happens
    ---------------------------------------------------------------------------------
    1     app loader                   findLoadedClass → not mine yet
    2     app loader → platform        delegate upward
    3     platform → bootstrap         delegate upward
    4     bootstrap                    searches java.base etc. → not found
    5     platform                     searches JDK modules → not found
    6     app loader                   findClass → reads Service.class from the jar
    7     LINK: verify                 stack shapes, type consistency, jump targets
    8     LINK: prepare                static fields set to defaults (0, null, false)
    9     LINK: resolve                symbolic references resolved (lazily, in HotSpot)
    10    INITIALISE                   <clinit> runs. Once, ever.
    ---------------------------------------------------------------------------------
    NOTE STEPS 2–5. The class was found by the loader that was asked FIRST, but only after two loaders
    above it declined. That upward trip is the security guarantee: bootstrap always gets right of first
    refusal, so no jar can shadow a core class.

    NOW `java.lang.String`, with a malicious copy on the classpath:
    step 3 reaches bootstrap, which HAS String, and returns it at once. The classpath copy is never
    read. Steps 6 onward do not happen. THAT IS THE WHOLE PROTECTION, and it is one `if` in five lines
    of code.

FAILURE 1 — `Foo cannot be cast to Foo`

    context: a webapp with CHILD-FIRST delegation, and the same library in both
             WEB-INF/lib and the container's lib directory
    ---------------------------------------------------------------------------------
    the container creates a Foo   → defined by the SHARED loader        → type Foo@A
    the webapp creates a Foo      → child-first, so WEB-INF/lib wins    → type Foo@B
    the container passes its Foo into the webapp
    the webapp assigns it to a Foo variable
    → ClassCastException: com.example.Foo cannot be cast to com.example.Foo
    ---------------------------------------------------------------------------------
    BOTH SIDES ARE BEHAVING AS DESIGNED. Child-first exists so a webapp can carry its own library
    versions; the price is that a class crossing the boundary is a different type. The fix is to remove
    the duplicate — pick one side to own that library — not to fight the loader.

FAILURE 2 — `NoSuchMethodError` FOR A METHOD THAT IS PLAINLY IN THE JAR

    classpath: lib-1.2.jar, lib-2.0.jar   (both present, 1.2 listed first)
    ---------------------------------------------------------------------------------
    compile against 2.0     → your code calls Util.newMethod()
    at runtime, the loader scans the classpath IN ORDER
    → finds Util in lib-1.2.jar FIRST → loads that one → stops looking
    → NoSuchMethodError: Util.newMethod()
    ---------------------------------------------------------------------------------
    THE CLASSPATH IS ORDER-DEPENDENT AND SILENT ABOUT IT. Nothing warns that two jars supply the same
    class. `-verbose:class` or `getProtectionDomain().getCodeSource()` tells you which one won;
    `mvn dependency:tree` tells you why both are there.

FAILURE 3 — `Metaspace` AFTER THE NINTH REDEPLOY

    time      what happens                                    metaspace
    ---------------------------------------------------------------------------------
    deploy 1  loader L1 defines 18,000 classes                 ~90 MB
    redeploy  webapp stopped; L1 SHOULD become garbage
              but a pooled container thread still holds a
              ThreadLocal → an AppContext → its Class → L1     ~90 MB RETAINED
    deploy 2  loader L2 defines 18,000 classes again           ~180 MB
    ...
    deploy 9                                                   ~810 MB → OOM: Metaspace
    heap throughout                                            healthy, ~600 MB
    ---------------------------------------------------------------------------------
    THE HEAP NEVER LOOKED WRONG. The tell is `jstat -class` showing the loaded-class count rising under
    a stable workload, and MAT's duplicate-class analysis showing nine definitions of the same class by
    nine loaders. ONE `ThreadLocal.remove()` IN A `finally` PREVENTS ALL OF IT.

WHAT PRODUCED WHAT:
    DELEGATION UPWARD          produced steps 2–5, and therefore the impossibility of shadowing String.
    (NAME, DEFINING LOADER)    produced failure 1's message, which is accurate and unbelievable.
    ORDERED CLASSPATH SEARCH   produced failure 2, silently.
    Class → LOADER → ALL CLASSES produced failure 3: one small reference, an entire application
                               retained.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Three phases: load, link (verify / prepare / resolve), initialise. Verification is what makes
    bytecode memory-safe.
    Delegation: ask the parent first. Application → Platform → Bootstrap.
    A class's identity is (fully qualified name, DEFINING loader). Same name, two loaders = two
    unrelated types with separate statics.
    A `Class` retains its defining loader; a loader retains every class it defined. Unloading requires
    the WHOLE loader to be unreachable.
    `ClassNotFoundException` is checked and comes from an explicit lookup; `NoClassDefFoundError` is an
    Error from the JVM — including when initialisation previously failed.
    `String.class.getClassLoader()` is `null`: that is the bootstrap loader.

THE #1 MISTAKE: reading `Foo cannot be cast to Foo` as a logging bug. Two loaders, two distinct types.

THE #2 MISTAKE: chasing the classpath for `NoClassDefFoundError: Could not initialize class X`. The
class is there; its static initialiser failed earlier.

THE #3 MISTAKE: treating `ClassNotFoundException` and `NoClassDefFoundError` as interchangeable. They
have different causes and different fixes.

THE #4 MISTAKE: leaving a `ThreadLocal`, a registered driver, or a started thread behind on undeploy.
Each one retains an entire application's classes.

THE #5 MISTAKE: two versions of a library on the classpath. First match wins, silently, and the symptom
is `NoSuchMethodError` for a method that is plainly present.

THE #6 MISTAKE: overriding `loadClass` when you meant to extend the search. Override `findClass`, and
keep delegating `java.*` upward regardless.

THE #7 MISTAKE: assuming the thread context class loader is the one you expect. It is the usual cause of
"works in my IDE, fails in the container".

THE #8 MISTAKE: `Class.forName(name, false, loader)` where a class must register itself in a static
block. It does not initialise.

THE #9 MISTAKE: getting the resource path form wrong. Leading slash with `Class`, none with
`ClassLoader`, relative-to-package with neither.

THE #10 MISTAKE: expecting classes to be unloaded. Only when the entire defining loader is unreachable —
which, for the application loader, is never.

THE #11 MISTAKE: writing a custom loader for a dependency conflict. Fix the dependency tree, then shade,
and only then reach for a loader.

ONE-SENTENCE TAKEAWAY: a loader asks its PARENT before looking itself, which is why no jar can shadow
`java.lang.String` and why every library sees the same one — and the fact that explains every strange
error in this area is that a class's identity is (NAME, DEFINING LOADER), so the same class from two
loaders is two unrelated types with separate static fields, producing `Foo cannot be cast to Foo`; that
same coupling means a `Class` retains its loader and a loader retains every class it defined, so one
lingering `ThreadLocal` or registered driver after a redeploy keeps an entire application's classes
alive and produces `OutOfMemoryError: Metaspace` with a perfectly healthy heap, while delegation is
deliberately inverted by application servers (child-first, so a webapp's own library version wins) and
bypassed downward by the thread context class loader, which is how a bootstrap class like
`DriverManager` reaches an application-classpath driver at all.""",
]


DEEP["Stack vs heap, and how a Java memory leak is even possible"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two memories with completely different rules

THE STACK is per-thread scratch space for method calls. Every call pushes a FRAME holding that method's
local variables and its working values; every return pops it. Reclamation is automatic and instant —
the frame is gone the moment the method returns, with no bookkeeping and no collector involved.

THE HEAP is one shared region where all objects live. It is shared by every thread, and nothing is
reclaimed until the garbage collector decides nothing can reach it any more.

    THE DIVISION IS SIMPLE ONCE STATED: EVERY OBJECT IS ON THE HEAP. EVERY LOCAL VARIABLE IS ON THE
    STACK. And a local variable of a reference type holds a REFERENCE on the stack, pointing at an
    object on the heap.

    SO `int x = 5` inside a method puts the 5 on the stack. `Point p = new Point()` puts the OBJECT on
    the heap and the reference to it on the stack. AND — this is the part people get wrong — `Point`'s
    own `int x` field is on the HEAP, inside the object, not on the stack. WHETHER A PRIMITIVE IS ON
    THE STACK DEPENDS ON WHETHER IT IS A LOCAL, NOT ON ITS TYPE.

WHY THIS ENTRY EXISTS: because those two rules explain both of Java's memory failures, and they are
completely different problems.

    `StackOverflowError` — one thread's stack ran out of frames. Almost always runaway recursion. The
    heap is untouched.
    `OutOfMemoryError: Java heap space` — the heap is full of REACHABLE objects.

    AND THE SECOND ONE IS WHY A LANGUAGE WITH GARBAGE COLLECTION STILL LEAKS. THE COLLECTOR FREES WHAT
    IS UNREACHABLE, NOT WHAT IS UNUSED. It cannot tell that you are finished with an object; it can only
    tell whether you can still GET to it. Keep a reference you have forgotten about and the object lives
    forever, with the collector doing exactly its job.

THE EVERYDAY VERSION: the stack is your desk — you take out what you need for the current task and it is
cleared the moment you finish. The heap is the building's storage room, shared by everyone, where things
are only removed when nobody anywhere has a note saying where they are. Forget you left a note in a
drawer and that box stays forever, and the person clearing the room is behaving perfectly correctly.

TERMS AS THEY APPEAR:
- FRAME: one method call's slice of the stack — locals, operand stack, return address.
- REACHABLE: there is a chain of references from a GC ROOT (a thread's stack, a static field, a JNI
  reference) to the object.
- OBSOLETE REFERENCE: a reference you still hold to something you will never use again. This is what a
  Java memory leak IS.""",

"""2. THE INTUITION — reachable is not the same as needed

THE COLLECTOR'S QUESTION IS "CAN ANY RUNNING CODE STILL REACH THIS?" — never "will any code still USE
this?" The second question is undecidable; the first is a graph traversal.

    SO EVERY JAVA MEMORY LEAK HAS THE SAME SHAPE: A REFERENCE THAT OUTLIVES ITS USEFULNESS. Not a
    missing `free`, not a double allocation — a chain from a GC root to something you are done with.

    AND SINCE GC ROOTS ARE PRECISELY "thread stacks, static fields, JNI references", the leak sources
    are predictable:

    A `static` COLLECTION THAT ONLY GROWS. A static field is a root, so a cache with no eviction retains
    everything ever put in it. THE MOST COMMON LEAK IN JAVA, and it is usually called a cache.
    A LISTENER OR CALLBACK NEVER DEREGISTERED. The registry outlives the listener, and the listener
    holds whatever it captured — often an entire enclosing object.
    A `ThreadLocal` ON A POOLED THREAD. The thread is a root and it NEVER DIES, so the value is never
    cleared. Classic in servlet containers and executors.
    AN INNER CLASS INSTANCE HELD BY SOMETHING LONG-LIVED. It carries a hidden `this$0` to the enclosing
    object.

AND THE ONE FROM `Effective Java` THAT IS WORTH KNOWING BECAUSE IT LOOKS CORRECT:

    public Object pop() {
        if (size == 0) throw new EmptyStackException();
        return elements[--size];          // ← the slot still holds the reference
    }

    The array slot at the old top still points at the popped object. `size` says the stack is shorter;
    the ARRAY does not care. That object — and everything IT references — is reachable forever, or at
    least until the slot is overwritten by a later push. THE FIX IS ONE LINE, `elements[size] = null;`,
    and the reason it is worth knowing is that the leak is in code that looks obviously right.

    THE PRINCIPLE GENERALISES: WHENEVER A CLASS MANAGES ITS OWN MEMORY, IT MUST NULL OUT OBSOLETE
    REFERENCES. `ArrayList.remove` does exactly this internally.

NOW THE STACK SIDE, WHICH HAS A DIFFERENT CHARACTER ENTIRELY:

    Each thread gets its OWN stack, typically ~1 MB reserved (`-Xss`), which is roughly 10,000–20,000
    frames of ordinary depth. When it runs out you get `StackOverflowError`.
    THE CAUSE IS ALMOST ALWAYS RECURSION WITHOUT A BASE CASE, or recursion over data far deeper than
    expected — a linked list of a million nodes traversed recursively, a deeply nested JSON document, a
    cyclic object graph in a naive `toString`.
    AND JAVA HAS NO TAIL-CALL OPTIMISATION. A tail-recursive method in Scheme or Scala runs in constant
    stack; in Java it consumes a frame per call, exactly like any other call. THAT IS A REAL DESIGN
    CONSTRAINT, not a detail: recursion depth in Java is bounded by memory, so any recursion over
    user-supplied data is a potential denial of service. Convert it to iteration with an explicit stack.

THE ONE PLACE THE CLEAN DIVISION BLURS: ESCAPE ANALYSIS. If the JIT can prove an object never escapes a
compiled region, it can SCALAR REPLACE it — the object is never allocated at all and its fields become
registers. So "objects are always on the heap" is true of the LANGUAGE and not always of the RUNTIME,
which is why "avoid allocation" advice is often obsolete.""",

"""3. THE MECHANISM — what a frame contains, what a root is, and where everything actually lives

A STACK FRAME contains three things, and their sizes are FIXED AT COMPILE TIME:

    THE LOCAL VARIABLE TABLE — slot 0 is `this` for an instance method, then the parameters, then the
    locals. `long` and `double` take two slots.
    THE OPERAND STACK — the working space for the bytecode. `iadd` pops two, pushes one.
    A REFERENCE TO THE CONSTANT POOL, and the return address.

    `max_locals` AND `max_stack` ARE IN THE CLASS FILE. The JVM knows exactly how big every frame will
    be before the method runs, which is why frame allocation is a pointer bump and why the verifier can
    prove the operand stack never underflows.

WHERE EVERYTHING LIVES, precisely:

    a local primitive             THE STACK, in the frame
    a local reference             THE STACK — the reference itself
    the object it points at       THE HEAP, always
    an instance field, primitive  THE HEAP, inside the object — NOT the stack
    an instance field, reference  THE HEAP, inside the object
    a static field                the heap, reachable from the class
    the array object              THE HEAP, even `int[]` — arrays are objects
    the class's metadata          METASPACE, which is native memory, not the heap
    a String literal              the string pool, which since Java 7 is in the heap

    THE ROW PEOPLE GET WRONG IS THE FOURTH. `class Point { int x; }` — that `x` is on the heap. A
    primitive is on the stack only when it is a LOCAL.

GC ROOTS — the starting points for the reachability traversal, and therefore the complete list of places
a leak can start:

    every live thread's STACK (all locals in all frames);
    STATIC fields of loaded classes;
    JNI global references;
    objects held by the JVM itself — the string pool, class objects, active monitors.

    A LEAK IS A PATH FROM ONE OF THOSE TO SOMETHING YOU ARE DONE WITH. That is the entire definition,
    and it is why a heap dump's DOMINATOR TREE is the right tool: it answers "what is retaining this",
    which is exactly "which root, by which path".

THE FIVE-LEVEL REFERENCE STRENGTH LADDER, since it is how you tell the collector about intent:

    STRONG      an ordinary reference. Never collected while reachable.
    SOFT        collected only when memory is tight. A memory-sensitive cache — though in practice a
                bounded LRU cache behaves better and is easier to reason about.
    WEAK        collected as soon as nothing STRONG points at the object. What `WeakHashMap` uses, and
                the right tool for keying metadata by an object you do not own.
    PHANTOM     for cleanup after collection, via a reference queue. `Cleaner` is built on this.
    UNREACHABLE collected.

    NOTE THE `WeakHashMap` TRAP: it holds keys weakly and VALUES STRONGLY. If a value references its own
    key — directly or through a chain — the entry is immortal, and the class designed to prevent leaks
    causes one.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `StackOverflowError` FROM UNBOUNDED RECURSION. The default ~1 MB stack gives roughly
10,000–20,000 frames. The heap is untouched and raising `-Xmx` does nothing.

CASE 2 — RECURSION OVER USER DATA. A deeply nested JSON document or a long linked list traversed
recursively is a denial-of-service vector, because Java has no tail-call optimisation.

CASE 3 — MUTUAL RECURSION BETWEEN `equals`, `hashCode` AND `toString` ON A CYCLIC OBJECT GRAPH. A
`StackOverflowError` from code containing no visible loop or recursion.

CASE 4 — RAISING `-Xss` TO "FIX" DEEP RECURSION. It multiplies across every thread — 1,000 threads at
2 MB is 2 GB of reservation — and it delays the failure rather than removing it.

CASE 5 — THE `static` CACHE WITH NO EVICTION. A static field is a GC root. Everything ever inserted is
retained. Usually called a cache and usually never bounded.

CASE 6 — THE UNREGISTERED LISTENER. The registry outlives the listener, which holds everything it
captured.

CASE 7 — `ThreadLocal` ON A POOLED THREAD. The thread never dies, so the value is never cleared. Always
`remove()` in a `finally`.

CASE 8 — THE OBSOLETE ARRAY SLOT. Decrementing a size without nulling the slot retains the popped
object. Looks obviously correct.

CASE 9 — A NON-STATIC INNER CLASS HANDED TO SOMETHING LONG-LIVED. The hidden `this$0` retains the whole
enclosing object graph.

CASE 10 — `WeakHashMap` WHOSE VALUES REFERENCE THEIR KEYS. Keys are weak, VALUES ARE STRONG, so the
entry becomes immortal. The leak-prevention tool causing a leak.

CASE 11 — `SoftReference` AS A CACHE STRATEGY. The collector decides when to clear them, so behaviour is
unpredictable and it can clear everything under pressure and then refill. A bounded cache is more
predictable.

CASE 12 — ASSUMING SETTING A VARIABLE TO `null` HELPS. Inside a method it almost never does — the JIT
already knows the variable is dead. It matters only for long-lived FIELDS and for array slots you
manage yourself.

CASE 13 — `System.gc()` TO "FREE" MEMORY. A hint, and under some collectors a full stop-the-world pause
you did not want. It cannot free anything reachable, which is what a leak is.

CASE 14 — A HEAP DUMP READ BY LOOKING FOR THE LARGEST OBJECT. The question is what RETAINS it. That is
what the dominator tree answers.""",

"""5. THE ALTERNATIVES — preventing leaks by construction

BOUND EVERYTHING THAT ACCUMULATES. Caffeine or Guava with `maximumSize` and expiry for caches; a bounded
`ArrayBlockingQueue` for work; a page size on every query. AN UNBOUNDED COLLECTION IS A MEMORY LEAK WITH
A SCHEDULE, and this single rule prevents most real leaks.

MAKE REGISTRATION SYMMETRIC. Whatever registers must unregister, ideally through try-with-resources or a
lifecycle callback so the compiler or the framework enforces it rather than the reviewer.

CLEAR `ThreadLocal`s IN A `finally`. Non-negotiable on any pooled thread.

DECLARE NESTED CLASSES `static` UNLESS THEY NEED THE ENCLOSING INSTANCE. That removes the hidden
`this$0` and the whole class of leak that comes with it.

NULL OUT OBSOLETE REFERENCES WHEN YOU MANAGE YOUR OWN ARRAY. Only when you manage your own storage —
inside an ordinary method it is noise.

USE THE REFERENCE TYPES DELIBERATELY: `WeakReference` when you want to observe an object without keeping
it alive; `WeakHashMap` for metadata keyed by an object you do not own — remembering that its values are
strong. `Cleaner` for a native-resource backstop, never as the primary mechanism, and never `finalize()`,
which is deprecated for removal.

CONVERT RECURSION TO ITERATION for anything unbounded — an explicit `ArrayDeque` as your own stack. THE
HEAP IS FAR LARGER THAN THE STACK AND GROWS, and this also removes the DoS vector from user-supplied
depth.

INCREASE `-Xss` ONLY FOR A GENUINELY DEEP ALGORITHM ON A SMALL NUMBER OF THREADS, and know that it
multiplies by thread count.

FOR VERY LARGE DATA, CONSIDER OFF-HEAP — `ByteBuffer.allocateDirect` or the Foreign Function & Memory
API — so the collector never walks it. Right for huge caches and I/O buffers, wrong almost everywhere
else, because you have reintroduced manual lifetime management.

THE TOOLS, IN THE ORDER YOU SHOULD REACH FOR THEM:
    `-Xlog:gc*` first — is old-gen occupancy after full GCs climbing? That answers leak-versus-capacity.
    A heap dump plus Eclipse MAT's DOMINATOR TREE and LEAK SUSPECTS report — "what retains this".
    JFR or async-profiler in allocation mode for CHURN rather than retention.
    `jstack` for a `StackOverflowError` — the repeating frame pattern names the recursion immediately.

WHAT TO SAY: "The collector frees what is UNREACHABLE, not what is unused — it cannot tell you are
finished with an object, only whether you can still get to it. So every Java leak is a reference that
outlived its usefulness, and since the roots are thread stacks, statics and JNI, the sources are
predictable: unbounded static caches, un-deregistered listeners, ThreadLocals on pooled threads, and
inner classes. Bounding every accumulating collection prevents most of them by construction."

""",

"""6. HOW TO FIND AND PREVENT A LEAK — numbered steps

STEP 1 — SEPARATE THE TWO FAILURES FIRST. `StackOverflowError` is one thread's recursion; heap OOM is
retention. They share nothing.

STEP 2 — FOR A STACK OVERFLOW, READ THE STACK TRACE. The repeating frame pattern names the recursion in
seconds. Look for a missing base case, or data deeper than you assumed.

STEP 3 — CONVERT UNBOUNDED RECURSION TO ITERATION WITH AN EXPLICIT `ArrayDeque`. Java has no tail-call
optimisation, so depth is bounded by memory and user-supplied depth is a DoS vector.

STEP 4 — FOR A HEAP PROBLEM, CHECK OLD-GEN OCCUPANCY AFTER SUCCESSIVE FULL GCs. Climbing means a leak;
a stable floor means capacity.

STEP 5 — TAKE A HEAP DUMP AND OPEN THE DOMINATOR TREE. Ask what RETAINS the largest object, not what is
largest.

STEP 6 — TRACE THE PATH BACK TO A GC ROOT. It will end at a static field, a thread's stack, or a JNI
reference — those are the only starting points there are.

STEP 7 — CHECK THE FOUR USUAL SUSPECTS BY NAME: static collections, listener registries, `ThreadLocal`s
on pooled threads, non-static inner classes held by something long-lived.

STEP 8 — BOUND EVERY CACHE AND EVERY QUEUE. This one rule prevents most leaks before they exist.

STEP 9 — MAKE EVERY `register` HAVE A MATCHING `unregister`, enforced by try-with-resources or a
lifecycle hook.

STEP 10 — `remove()` EVERY `ThreadLocal` IN A `finally`.

STEP 11 — NULL OBSOLETE ARRAY SLOTS ONLY WHEN YOU MANAGE YOUR OWN STORAGE. Setting a local to null
inside a method is noise; the JIT already knows.

STEP 12 — DO NOT REACH FOR `System.gc()`. It cannot free anything reachable, and a leak is by definition
reachable.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The stack is per-thread scratch space for method calls: every call pushes a FRAME with that method's
locals and working values, every return pops it, and reclamation is instant with no collector involved.
The heap is one shared region where all objects live, and nothing is reclaimed until the GC decides
nothing can reach it.

The division: every OBJECT is on the heap, every LOCAL VARIABLE is on the stack, and a local of
reference type holds a reference on the stack pointing at an object on the heap. The row people get
wrong is instance FIELDS — `class Point { int x; }` puts that `x` on the HEAP, inside the object.
Whether a primitive is on the stack depends on whether it's a local, not on its type.

That gives two completely different failures. StackOverflowError is one thread's stack running out of
frames — almost always runaway recursion, and the heap is untouched, so raising -Xmx does nothing.
OutOfMemoryError heap space is the heap being full of REACHABLE objects.

And the second one is why a garbage-collected language still leaks. THE COLLECTOR FREES WHAT IS
UNREACHABLE, NOT WHAT IS UNUSED. It can't tell you're finished with an object — it can only tell whether
you can still GET to it. That question is a graph traversal; the other one is undecidable.

So every Java leak has the same shape: a reference that outlived its usefulness. And since the GC roots
are exactly thread stacks, static fields and JNI references, the sources are predictable. A static
collection that only grows — usually called a cache and usually unbounded, and it's the most common one.
A listener never deregistered. A ThreadLocal on a POOLED thread, where the thread never dies so the
value is never cleared. And a non-static inner class held by something long-lived, carrying its hidden
this$0.

The example I like is from Effective Java, because it looks obviously correct. A stack implemented over
an array, where pop does `return elements[--size]`. The array slot at the old top still points at the
popped object. Size says the stack is shorter; the ARRAY doesn't care. That object and everything it
references is retained until the slot is overwritten. The fix is one line — null the slot — and the
principle generalises: whenever a class manages its own memory, it has to null out obsolete references.
ArrayList.remove does exactly this internally.

On the stack side, the thing worth saying is that Java has NO TAIL-CALL OPTIMISATION. A tail-recursive
method in Scala or Scheme runs in constant stack; in Java it consumes a frame per call like anything
else. Which makes recursion depth bounded by memory — so any recursion over user-supplied data, a deeply
nested JSON document say, is a potential denial of service. Convert it to iteration with an explicit
ArrayDeque; the heap is far larger than the stack and it grows.

One nuance: "objects are always on the heap" is true of the LANGUAGE, not always the runtime. If the JIT
can prove an object never escapes, it scalar-replaces it — the object is never allocated and its fields
become registers. Which is why a lot of "avoid allocation" advice is obsolete.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHERE THINGS ACTUALLY LIVE ──────────────────────────────────────
    class Point { int x; Point next; }          // ← BOTH fields are on the HEAP,
    //                                             inside the object
    void m() {
        int a = 5;                              // STACK — a local primitive
        Point p = new Point();                  // the OBJECT is on the HEAP;
        //                                         `p`, the REFERENCE, is on the stack
        p.x = 7;                                // written into the HEAP object
        int[] arr = new int[100];               // the ARRAY is on the heap — arrays
        //                                         are objects, even int[]
    }   // ← the frame pops. `a` and `p` vanish instantly, no collector involved.
        //   The Point survives until nothing can reach it.

    // ── STACK OVERFLOW: the heap is untouched ───────────────────────────
    int depth(Node n) { return n == null ? 0 : 1 + depth(n.next); }
    // ^ on a 1,000,000-node list: ~1 MB of stack gives ~10,000-20,000 frames →
    //   StackOverflowError. Raising -Xmx does NOTHING; this is -Xss, and raising THAT
    //   multiplies across every thread (1,000 threads × 2 MB = 2 GB reserved).
    int depth(Node n) {                          // ← the fix: an explicit stack on the
        int d = 0;                               //   HEAP, which is far larger and grows
        for (Node c = n; c != null; c = c.next) d++;
        return d;
    }
    // AND NOTE: Java has NO TAIL-CALL OPTIMISATION. The recursive version above IS
    // tail-recursive and still consumes a frame per call. So recursion over
    // user-supplied depth — nested JSON, for instance — is a DoS vector.

    // ── THE LEAK THAT LOOKS OBVIOUSLY CORRECT ───────────────────────────
    public Object pop() {
        if (size == 0) throw new EmptyStackException();
        return elements[--size];
    //         ^^^^^^^^^^^^^^^^ THE SLOT STILL HOLDS THE REFERENCE. `size` says the
    //   stack is shorter; the ARRAY does not care. The popped object — and everything
    //   IT references — is reachable until that slot is overwritten by a later push.
    }
    public Object pop() {
        if (size == 0) throw new EmptyStackException();
        Object result = elements[--size];
        elements[size] = null;                   // ← ONE LINE. Effective Java Item 7.
        return result;
    }
    // The principle: WHENEVER A CLASS MANAGES ITS OWN MEMORY, NULL OUT OBSOLETE
    // REFERENCES. ArrayList.remove does exactly this internally.

    // ── THE FOUR CLASSIC LEAKS, EACH ROOTED SOMEWHERE ───────────────────
    static final Map<String,Session> CACHE = new HashMap<>();  // ← a STATIC field is
    //                                                            a GC ROOT. No
    //                                                            eviction = retain all.
    EventBus.register(this::onEvent);            // ← never deregistered; the registry
    //                                              outlives you and holds `this`
    static final ThreadLocal<Ctx> CTX = new ThreadLocal<>();
    void handle() { CTX.set(new Ctx()); ... }    // ← on a POOLED thread that never
    //                                              dies. Always remove() in a finally.
    executor.submit(new Runnable() { public void run() { redraw(); } });
    //              ^^^^^^^^^^^^^^ a non-static inner class, carrying a hidden this$0
    //                             to the entire enclosing object

    // ── THE LEAK-PREVENTION TOOL THAT LEAKS ─────────────────────────────
    Map<Key,Value> m = new WeakHashMap<>();
    m.put(key, valueThatReferencesItsOwnKey);
    // ^ WeakHashMap holds KEYS weakly and VALUES STRONGLY. If the value can reach the
    //   key, the key is strongly reachable, so the entry is IMMORTAL.

    // ── WHAT DOES NOT HELP ──────────────────────────────────────────────
    p = null;              // inside a method: almost always noise. The JIT already
    //                        knows `p` is dead after its last use.
    System.gc();           // a HINT, and it cannot free anything REACHABLE — which is
    //                        exactly what a leak is.""",

"""9. THE TRACE — one call, and one object that never dies

TRACE 1 — WHAT A CALL DOES TO THE STACK. `main` calls `process(3)`, which calls `helper()`:

    stack (grows downward)                     heap
    ---------------------------------------------------------------------------------
    [main]        args, cfg → ────────────────► Config@0x100
    [process]     n=3, p   → ─────────────────► Point@0x200
    [helper]      tmp=7, s → ─────────────────► String@0x300
    ---------------------------------------------------------------------------------
    helper returns  → its frame POPS. `tmp` and `s` are gone INSTANTLY. No collector
                      ran. String@0x300 is now unreachable and will be collected
                      whenever the GC next looks.
    process returns → its frame pops. Point@0x200 becomes unreachable.
    ---------------------------------------------------------------------------------
    STACK RECLAMATION IS FREE AND IMMEDIATE; HEAP RECLAMATION IS DEFERRED AND COSTS A TRAVERSAL. Two
    memories, two completely different reclamation models, and every difference in this entry follows
    from that.

TRACE 2 — THE SAME CALL, WITH ONE LINE ADDED.

    void process(int n) {
        Point p = new Point();
        CACHE.put("last", p);          // ← CACHE is a static field
    }
    ---------------------------------------------------------------------------------
    process returns  → the frame pops, `p` is gone from the stack
    the GC runs      → is Point@0x200 reachable?
                       CACHE (a STATIC FIELD — a GC ROOT) → HashMap → Point@0x200
                       YES. RETAINED.
    ---------------------------------------------------------------------------------
    NOTHING IN `process` LOOKS WRONG. The local went out of scope exactly as expected. A reference was
    handed to something rooted, and that is the entire mechanism of every Java leak.

TRACE 3 — THE ARRAY SLOT, step by step. A stack holding three elements:

    step                     size   elements[]                    reachable?
    ---------------------------------------------------------------------------------
    after 3 pushes           3      [A, B, C, null, ...]           A, B, C
    pop() → returns C        2      [A, B, C, null, ...]           A, B, AND C
                                        ^^^ THE SLOT STILL POINTS AT C
    caller discards C        2      [A, B, C, null, ...]           A, B, and C —
                                                                   because the ARRAY
                                                                   still reaches it
    push(D)                  3      [A, B, D, null, ...]           A, B, D. C is
                                                                   finally free.
    ---------------------------------------------------------------------------------
    IF THE STACK NEVER GROWS BACK, C IS RETAINED FOREVER — along with everything C references, which for
    a session object or a document might be megabytes. And a stack that peaked at 10,000 and now holds
    10 retains 9,990 obsolete references.

TRACE 4 — STACK OVERFLOW, and why the trace is the diagnosis:

    Exception in thread "main" java.lang.StackOverflowError
        at Parser.parseValue(Parser.java:88)
        at Parser.parseObject(Parser.java:42)
        at Parser.parseValue(Parser.java:91)
        at Parser.parseObject(Parser.java:42)
        ... repeated ~11,000 times
    ---------------------------------------------------------------------------------
    THE REPEATING PAIR NAMES THE RECURSION IMMEDIATELY. Two frames alternating means mutual recursion
    between `parseValue` and `parseObject` — here, parsing a deeply nested JSON document. The heap is at
    12%; `-Xmx` is irrelevant. The choices are a depth limit on the input, a bigger `-Xss` (which
    multiplies by thread count and only delays it), or an iterative parser with an explicit `ArrayDeque`.

    AND NOTE WHAT THIS MEANS SECURITY-WISE: if that JSON came from a request, an attacker chooses the
    recursion depth. Because Java has no tail-call optimisation, there is no depth at which the runtime
    saves you.

WHAT PRODUCED WHAT:
    FRAMES POPPING ON RETURN     produced trace 1's instant reclamation — and the absence of any leak
                                 risk on the stack.
    REACHABILITY FROM A ROOT     produced traces 2 and 3. Both are "a reference reached something
                                 rooted", and neither line of code looks wrong.
    NO TAIL-CALL OPTIMISATION    produced trace 4, and turned a parser into an availability risk.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    Stack: per thread, ~1 MB reserved by default (`-Xss`), roughly 10,000–20,000 ordinary frames.
    Frame allocation is a pointer bump; `max_locals` and `max_stack` are fixed in the class file.
    Heap: shared, bounded by `-Xmx`, reclaimed by a traversal from GC roots.
    GC roots: thread stacks, static fields, JNI references, and JVM-internal structures. That list is
    the complete set of places a leak can start.
    No tail-call optimisation: recursion depth is bounded by stack memory, always.
    Escape analysis can eliminate an allocation entirely — so "always on the heap" is a language
    statement, not a runtime guarantee.

THE #1 MISTAKE: believing a garbage-collected language cannot leak. It frees the UNREACHABLE, not the
unused.

THE #2 MISTAKE: an unbounded static collection called a cache. A static field is a root; nothing in it
is ever collectable.

THE #3 MISTAKE: a listener never deregistered. Registration without matching removal is a leak by
construction.

THE #4 MISTAKE: a `ThreadLocal` on a pooled thread. The thread never dies, so nothing clears it.

THE #5 MISTAKE: a non-static inner class handed to something long-lived. The hidden `this$0` retains the
whole enclosing graph.

THE #6 MISTAKE: not nulling obsolete array slots in a class that manages its own storage. The
`Effective Java` stack, and it looks correct.

THE #7 MISTAKE: raising `-Xmx` for a `StackOverflowError`. Wrong memory entirely — and raising `-Xss`
multiplies across every thread.

THE #8 MISTAKE: recursion over user-supplied depth. With no tail-call optimisation, that is a denial of
service.

THE #9 MISTAKE: `WeakHashMap` whose values can reach their keys. Values are held STRONGLY, so the entry
is immortal.

THE #10 MISTAKE: `SoftReference` as a cache policy. The collector decides, unpredictably. A bounded LRU
cache is better behaved.

THE #11 MISTAKE: setting locals to `null` for "hygiene". Noise inside a method; the JIT already knows.

THE #12 MISTAKE: `System.gc()` to fix a leak. It cannot free anything reachable, and reachable is what a
leak is.

ONE-SENTENCE TAKEAWAY: the stack is per-thread frames reclaimed instantly on return, the heap is shared
objects reclaimed only when UNREACHABLE — and that word is why Java leaks, because the collector cannot
tell you are finished with an object, only whether some chain from a thread stack, a static field or a
JNI reference can still get to it; every leak is therefore an OBSOLETE REFERENCE, which is why the
sources are so predictable (unbounded static caches, un-deregistered listeners, `ThreadLocal`s on pooled
threads, inner classes, and array slots a class forgot to null), and why the stack has no leaks at all
but does have a hard ceiling — Java has no tail-call optimisation, so recursion depth is bounded by
memory and any recursion over user-supplied data is an availability risk that should be an explicit
`ArrayDeque` on the heap instead.""",
]


DEEP["switch — fall-through, strings, and the expression form"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the statement that keeps going, and the expression that does not

The old `switch` has a behaviour nobody would design today: WHEN A CASE MATCHES, EXECUTION FALLS INTO
EVERY CASE BELOW IT until it hits a `break`. Matching selects a STARTING POINT, not a block.

    switch (day) {
        case 1: print("Mon");     // ← day == 1 prints Mon, Tue AND Wed
        case 2: print("Tue");
        case 3: print("Wed"); break;
    }

    A MISSING `break` IS A SILENT LOGIC BUG. It compiles, it runs, and it does something plausible-
    looking. This is inherited from C — where fall-through was genuinely useful for hand-optimised
    jump tables — and Java kept it in 1995 for familiarity.

JAVA 14 ADDED THE ARROW FORM, WHICH FIXES IT AND MORE:

    switch (day) {
        case 1 -> print("Mon");        // NO fall-through. Ever.
        case 2, 3 -> print("Midweek"); // several labels, one arm
    }

    AND — the more important change — `switch` BECAME AN EXPRESSION that produces a value:

        String name = switch (day) {
            case 1, 7 -> "weekend";
            default   -> "weekday";
        };

    An expression must produce a value on every path, so the compiler now CHECKS EXHAUSTIVENESS. Over
    an enum or a sealed type, that means you cannot forget a case — and if you add a new constant, code
    that does not handle it FAILS TO COMPILE.

    THAT IS THE REAL UPGRADE. The old form could be wrong in two silent ways (a missing `break`, a
    missing case); the new form makes both of them compile errors.

THE EVERYDAY VERSION: the old switch is a set of instructions on one long page where "start at step 4"
means you also do steps 5, 6 and 7 unless someone wrote STOP. The new one is a lookup table: find the
row, do that row, done — and the table refuses to be printed with a row missing.

TERMS AS THEY APPEAR:
- FALL-THROUGH: continuing into the next case because there was no `break`.
- ARROW LABEL: `case X ->`. No fall-through, in statements as well as expressions.
- EXHAUSTIVE: every possible value is covered, checked by the compiler.
- `yield`: returns a value from a multi-statement arm of a switch EXPRESSION.""",

"""2. THE INTUITION — why `switch` exists at all, and why the types are so restricted

A CHAIN OF `if`/`else if` COMPARES ONE VALUE AGAINST EACH CANDIDATE IN TURN — O(n) comparisons. `switch`
exists because a compiler can often do better than that, and the bytecode reflects it directly:

    `tableswitch`   used when the case values are DENSE (1, 2, 3, 4, 5). It is a JUMP TABLE: subtract
                    the low value, index an array of offsets, jump. O(1), REGARDLESS OF HOW MANY CASES.
    `lookupswitch`  used when the values are SPARSE (1, 100, 5000). Sorted key/offset pairs, searched
                    binary — O(log n).

    SO A DENSE `switch` OVER 200 CASES IS ONE INDEXED JUMP, while the equivalent if-else chain averages
    100 comparisons. That is the whole reason the construct exists, and it is why javac will sometimes
    emit a `tableswitch` with padding entries for a slightly sparse set — a jump table with gaps still
    beats a search.

AND THAT EXPLAINS THE TYPE RESTRICTIONS, WHICH OTHERWISE LOOK ARBITRARY:

    ALLOWED: `byte`, `short`, `char`, `int` and their wrappers, `String`, `enum` — and, since Java 21,
    any reference type with patterns.
    NOT ALLOWED: `long`, `float`, `double`, `boolean`.

    `long` IS THE INTERESTING OMISSION. It is excluded because both switch bytecodes index on an `int`
    — a 64-bit jump table is not a thing. `float` and `double` are excluded because equality on them is
    not what anyone wants (see `NaN`, and `0.1 + 0.2`). `boolean` is excluded because `if` already
    exists.

    THE STRING CASE IS A COMPILER TRICK, and it is worth knowing because it explains a NullPointerException
    people find mysterious: a `String` switch compiles to TWO switches — first a `lookupswitch` on
    `hashCode()`, then an `equals()` check to guard against hash collisions, mapping to an index, then a
    second `tableswitch` on that index. WHICH MEANS SWITCHING ON A NULL STRING CALLS `hashCode()` ON
    NULL. Hence: a `switch` on a null reference throws NPE, and always did.

THE ENUM CASE IS ALSO SYNTHETIC. javac generates a hidden `$SwitchMap` array mapping each constant's
ORDINAL to a small dense int, so an enum switch is a `tableswitch`. This indirection exists so that
adding a constant to the enum does not silently shift the meaning of already-compiled code — the map is
rebuilt per compilation unit.

    BUT NOTE WHAT IT DOES NOT PROTECT YOU FROM: in the OLD statement form, adding a constant means the
    switch silently does nothing for it. Only the EXPRESSION form, checked for exhaustiveness, turns
    that into a compile error.""",

"""3. THE MECHANISM — the four forms, and what `default` costs you

THERE ARE FOUR COMBINATIONS, and knowing which one you are writing is most of the topic:

    COLON STATEMENT      `case 1: ...; break;`      FALLS THROUGH. The legacy form.
    ARROW STATEMENT      `case 1 -> ...;`           NO fall-through. Still a statement; not exhaustive.
    COLON EXPRESSION     `case 1: yield x;`         Produces a value; `yield` instead of `break`.
    ARROW EXPRESSION     `case 1 -> x;`             Produces a value. THE FORM TO PREFER.

    THE ARROW FORM REMOVED FALL-THROUGH IN STATEMENTS TOO, which is often overlooked — you get the
    safety without needing a value.

`yield` VS `return`, since this trips people:
    `yield x` produces the value of the SWITCH EXPRESSION.
    `return x` returns from the ENCLOSING METHOD — and inside a switch EXPRESSION it is a compile error,
    because an expression must produce a value where it sits.
    In an arrow arm with a block body you need `yield`:
        case 1 -> { var t = compute(); yield t * 2; }

EXHAUSTIVENESS, WHICH IS THE WHOLE POINT OF THE EXPRESSION FORM:
    A switch EXPRESSION must produce a value for every possible input.
    Over an `enum` covering every constant, or over a `sealed` type covering every permitted subtype,
    NO `default` IS NEEDED — the compiler can see the full set.
    Over anything else — an `int`, a `String` — a `default` is required, because the set is open.

AND THE ONE RULE THAT MATTERS MOST IN PRACTICE: DO NOT WRITE `default` IN AN EXHAUSTIVE ENUM OR SEALED
SWITCH.

    With no `default`, adding a constant BREAKS THE BUILD at every site that needs updating — which is
    exactly what you want, and it is a guarantee virtual dispatch never gave you.
    With a `default`, adding a constant compiles fine and silently falls into it. YOU HAVE TRADED A
    COMPILE ERROR FOR A RUNTIME SURPRISE, in one word.
    (The compiler still inserts a hidden default that throws `IncompatibleClassChangeError` if the enum
    changes without recompilation — so the runtime is protected even though your code is not.)

PATTERN MATCHING (JAVA 21) EXTENDS ALL OF THIS to any reference type:
    TYPE PATTERNS        `case Circle c -> c.radius()`
    RECORD PATTERNS      `case Circle(double r) -> r`      — deconstruction, and nestable
    GUARDS               `case Integer i when i > 100 -> ...`
    `case null`          previously impossible; without it a switch on a null reference still THROWS,
                         which preserves the old behaviour and surprises people in new code.
    ORDER NOW MATTERS: labels are tested in order, so a more general pattern before a more specific one
    is a compile error — dominance checking, which the old form never needed.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — A MISSING `break` IN THE COLON FORM. Execution continues into every case below. Compiles,
runs, and produces a plausible wrong answer.

CASE 2 — INTENTIONAL FALL-THROUGH WITH NO COMMENT. Indistinguishable from a bug during review. If you
mean it, say so — and prefer `case 1, 2, 3 ->` in the arrow form, which expresses grouping without
fall-through.

CASE 3 — `switch` ON A NULL `String` OR ENUM. Throws `NullPointerException`, because the compiled form
calls `hashCode()` or `ordinal()` on it. Java 21 lets you write `case null`; without it the old
behaviour is preserved.

CASE 4 — SWITCHING ON A `long`. Not allowed, because both switch bytecodes index on an `int`. Neither
are `float`, `double` or `boolean`.

CASE 5 — ADDING AN ENUM CONSTANT WITH AN OLD-STYLE STATEMENT SWITCH. Nothing breaks; the new constant
silently matches nothing. Only an exhaustive EXPRESSION turns this into a compile error.

CASE 6 — WRITING `default` IN AN EXHAUSTIVE ENUM SWITCH. It compiles and discards the exhaustiveness
guarantee. One word, and the whole benefit is gone.

CASE 7 — A `String` SWITCH ASSUMED TO BE FAST. It is a hash lookup PLUS an `equals` call per candidate
in the bucket, not a jump table. Fast, but not free, and case-sensitive.

CASE 8 — VARIABLES DECLARED IN A COLON CASE. The whole switch body is ONE scope, so a variable declared
in `case 1:` is visible (and possibly unassigned) in `case 2:`. Braces around each arm, or the arrow
form, fixes it.

CASE 9 — `return` INSIDE A SWITCH EXPRESSION. A compile error; use `yield`. `return` inside a switch
STATEMENT is fine and returns from the method.

CASE 10 — MIXING COLON AND ARROW LABELS IN ONE SWITCH. Not allowed. Pick one form.

CASE 11 — `case` LABELS MUST BE COMPILE-TIME CONSTANTS in the classic form. A `static final` variable
works; a plain variable does not.

CASE 12 — PATTERN DOMINANCE. `case Object o` before `case String s` is a compile error, because the
first can never let the second run. The old form never needed this rule.

CASE 13 — A SWITCH EXPRESSION WITH AN ARM THAT ALWAYS THROWS. Legal, and it does not need to yield —
throwing is a valid way to complete.

CASE 14 — SPARSE `int` CASES. The compiler emits `lookupswitch` (binary search) rather than a jump
table. Still good, and not the O(1) people assume.""",

"""5. THE ALTERNATIVES — and when `switch` is the wrong shape entirely

THE ARROW SWITCH EXPRESSION IS THE DEFAULT for anything selecting a value from a closed set. Prefer it
over the colon form everywhere, even when you do not need a value, because it removes fall-through.

A `Map` LOOKUP when the mapping is data rather than logic. `Map<String, Handler>` populated once beats a
fifty-case switch: it is extensible without recompiling the switch, testable, and often clearer. USE A
SWITCH FOR BRANCHING LOGIC AND A MAP FOR A LOOKUP TABLE — a switch whose arms all just return a constant
was probably always a map.

POLYMORPHISM when the behaviour genuinely belongs to the type and the set of types is OPEN. A switch on
a type code is the classic smell; an abstract method removes it. THE TRADE IS THE EXPRESSION PROBLEM:
virtual dispatch makes adding TYPES easy and adding OPERATIONS hard; a sealed type plus a switch makes
adding OPERATIONS easy and adding types a compile error everywhere. Pick by which axis moves.

ENUM WITH CONSTANT-SPECIFIC BODIES when the behaviour belongs to the constants:

    enum Op { PLUS { int apply(int a, int b) { return a + b; } },
              TIMES { int apply(int a, int b) { return a * b; } };
              abstract int apply(int a, int b); }

    IMPOSSIBLE TO FORGET A CASE — the compiler requires every constant to implement the abstract method.
    Better than a switch when there is exactly one operation; worse when there are ten, because it puts
    unrelated concerns inside the enum.

SEALED INTERFACE + RECORDS + PATTERN SWITCH when the alternatives carry different DATA. This is the
modern shape for algebraic data, and exhaustiveness is the payoff.

A STRATEGY OBJECT or a rules engine when the branching is configuration rather than code.

`if`/`else if` when there are two or three cases, or when the conditions are ranges or compound
predicates rather than equality on one value. A switch on `true` with guards is a trick, not a
readability win.

WHAT NOT TO DO: a giant switch on a type code, or the same switch duplicated in five places. The second
is the real signal — a switch repeated over the same set in several files is asking to become
polymorphism or a sealed hierarchy.

WHAT TO SAY: "The arrow expression form, always — it removes fall-through and, over an enum or sealed
type, gives EXHAUSTIVENESS CHECKING, so adding a constant breaks the build instead of silently doing
nothing. And I would deliberately omit `default` there, because that one word trades the compile error
back for a runtime surprise."

""",

"""6. HOW TO WRITE SWITCHES WELL — numbered steps

STEP 1 — USE THE ARROW FORM. `case X ->`. It removes fall-through in statements as well as expressions,
so there is no reason to write the colon form in new code.

STEP 2 — PREFER THE EXPRESSION FORM WHEN YOU ARE PRODUCING A VALUE. It forces every path to produce one,
which is where the checking comes from.

STEP 3 — OVER AN ENUM OR SEALED TYPE, OMIT `default`. That is what makes adding a constant a compile
error at every site that needs attention.

STEP 4 — GROUP LABELS WITH COMMAS, NOT FALL-THROUGH. `case SATURDAY, SUNDAY ->`.

STEP 5 — USE `yield` FOR MULTI-STATEMENT ARMS. `return` inside a switch expression is a compile error.

STEP 6 — HANDLE `null` EXPLICITLY where it is possible. Without `case null`, a switch on a null reference
throws.

STEP 7 — IF EVERY ARM JUST RETURNS A CONSTANT, USE A `Map`. That was a lookup table, not branching logic.

STEP 8 — IF THE SAME SWITCH APPEARS IN SEVERAL PLACES OVER THE SAME SET, REACH FOR POLYMORPHISM OR A
SEALED HIERARCHY. Duplication over one set is the signal.

STEP 9 — IF YOU MUST USE THE COLON FORM, COMMENT EVERY INTENTIONAL FALL-THROUGH. Otherwise no reviewer
can distinguish it from a bug.

STEP 10 — BRACE EACH COLON ARM IF YOU DECLARE VARIABLES. The whole body is one scope otherwise.

STEP 11 — ORDER PATTERNS FROM SPECIFIC TO GENERAL. A dominating pattern first is a compile error, and
that check is helping you.

STEP 12 — DO NOT SWITCH ON A `long`. It is not allowed, and the reason — both bytecodes index on an
`int` — is worth knowing rather than working around blindly.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The old switch has a behaviour nobody would design today: when a case matches, execution falls into
every case BELOW it until it hits a break. Matching selects a STARTING POINT, not a block. So a missing
break is a silent logic bug — it compiles, it runs, and it does something plausible. That's inherited
from C, where fall-through was genuinely useful for hand-written jump tables, and Java kept it in 1995
for familiarity.

Java 14 added the arrow form, which removes fall-through — and importantly it does that in STATEMENTS
too, not just expressions, so you get the safety without needing a value. And then switch became an
EXPRESSION that produces a value. That's the real upgrade, because an expression has to produce a value
on every path, which means the compiler CHECKS EXHAUSTIVENESS. Over an enum or a sealed type you can't
forget a case, and adding a new constant makes code that doesn't handle it fail to compile. The old form
could be wrong in two silent ways — missing break, missing case — and the new form turns both into
compile errors.

It's worth knowing why switch exists at all, because it explains the type restrictions. An if-else chain
is O(n) comparisons. Switch compiles to one of two bytecodes: tableswitch, which is a real JUMP TABLE
for dense values — subtract the low value, index an array, jump, O(1) regardless of case count — or
lookupswitch for sparse values, which is a binary search. A dense switch over 200 cases is one indexed
jump where the if-else chain averages 100 comparisons.

And that explains the allowed types. You can switch on byte, short, char, int, their wrappers, String and
enum. You CANNOT switch on long — because both bytecodes index on an int, and a 64-bit jump table isn't
a thing. Not float or double either, because equality on them isn't what anyone wants. Not boolean,
because if already exists.

String switch is a compiler trick worth knowing, because it explains an NPE people find mysterious: it
compiles to TWO switches — a lookupswitch on hashCode, then an equals check to guard against collisions,
then a second switch on an index. Which means switching on a null String calls hashCode on null. That's
why a switch on a null reference throws, and always did. Java 21 finally lets you write `case null`.

The rule I'd emphasise most: over an enum or sealed type, DON'T write default. With no default, adding a
constant breaks the build at every site that needs updating — which is exactly what you want. With a
default it compiles fine and silently falls into it. One word, and you've traded a compile error for a
runtime surprise.

And one design point: if every arm just returns a constant, that was a lookup table, not branching
logic — use a Map. And if the same switch over the same set appears in five files, that's the signal to
reach for polymorphism or a sealed hierarchy instead.'""",

"""8. THE CODE, LINE BY LINE

    // ── FALL-THROUGH: matching picks a STARTING POINT, not a block ──────
    switch (day) {
        case 1: print("Mon");        // day == 1 prints Mon, Tue AND Wed
        case 2: print("Tue");        // ← no break, so execution CONTINUES here
        case 3: print("Wed"); break;
    }
    // Compiles. Runs. Produces a plausible wrong answer. Inherited from C.

    // ── THE ARROW FORM: no fall-through, IN STATEMENTS TOO ──────────────
    switch (day) {
        case 1 -> print("Mon");
        case 2, 3 -> print("Midweek");   // ← grouping WITHOUT fall-through
    }
    // Often overlooked: you get the safety here without needing a value.

    // ── THE EXPRESSION FORM: the compiler now checks you ────────────────
    String kind = switch (day) {
        case SATURDAY, SUNDAY -> "weekend";
        case MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY -> "weekday";
    };
    // NO `default`. Every enum constant is covered, so the compiler is satisfied —
    // AND if someone adds a constant, THIS LINE STOPS COMPILING. That is the point.

    String kind = switch (day) {
        case SATURDAY, SUNDAY -> "weekend";
        default -> "weekday";            // ← ONE WORD, and the guarantee is gone.
    };
    // Adding a constant now compiles fine and silently falls into default. You traded
    // a compile error for a runtime surprise.

    // ── yield, NOT return ───────────────────────────────────────────────
    int v = switch (code) {
        case 1 -> 10;
        case 2 -> { var t = compute(); yield t * 2; }   // ← block body needs yield
    //                                  ^^^^^ `return` here is a COMPILE ERROR: an
    //   expression must produce a value where it sits, not leave the method.
        default -> 0;
    };

    // ── WHY THE ALLOWED TYPES ARE WHAT THEY ARE ─────────────────────────
    // tableswitch : DENSE values → subtract the low value, index an array, JUMP. O(1)
    //               regardless of how many cases.
    // lookupswitch: SPARSE values → sorted key/offset pairs, binary search. O(log n).
    //
    // switch (someLong)    ✗ NOT ALLOWED — both bytecodes index on an INT. A 64-bit
    //                        jump table is not a thing.
    // switch (someDouble)  ✗ equality on doubles is not what anyone wants (see NaN)
    // switch (someBoolean) ✗ `if` already exists

    // ── THE NPE THAT LOOKS MYSTERIOUS ───────────────────────────────────
    String s = null;
    switch (s) { case "a" -> ...; default -> ...; }   // → NullPointerException
    // A String switch compiles to TWO switches: a lookupswitch on hashCode(), an
    // equals() check to guard against hash collisions, then a tableswitch on an index.
    // SO IT CALLS hashCode() ON NULL. Same story for enums, via ordinal().
    switch (s) { case null -> "none"; case "a" -> ...; default -> ...; }   // Java 21

    // ── THE COLON-FORM SCOPE TRAP ───────────────────────────────────────
    switch (x) {
        case 1: int n = compute(); break;
        case 2: print(n);          // ← n IS IN SCOPE HERE, and unassigned. The whole
    }                              //   switch body is ONE scope. Brace each arm, or
    //                                 use the arrow form.

    // ── AND WHEN switch IS THE WRONG SHAPE ──────────────────────────────
    String label = switch (code) {
        case "A" -> "Alpha"; case "B" -> "Bravo"; /* ...48 more... */
    };
    static final Map<String,String> LABELS = Map.of("A","Alpha","B","Bravo", ...);
    // ^ If every arm just returns a constant, IT WAS A LOOKUP TABLE, NOT BRANCHING
    //   LOGIC. And the same switch repeated across five files is the signal to reach
    //   for polymorphism or a sealed hierarchy instead.""",

"""9. THE TRACE — the same decision, four ways, and what each catches

THE SETUP: an enum `Status { NEW, ACTIVE, CLOSED }` and code that maps a status to a message. Then
someone adds `ARCHIVED`.

    FORM 1 — COLON STATEMENT, missing break
    ---------------------------------------------------------------------------------
    switch (s) {
        case NEW:    msg = "new";
        case ACTIVE: msg = "active"; break;
        case CLOSED: msg = "closed"; break;
    }
    input NEW  → sets msg = "new", FALLS THROUGH, sets msg = "active", breaks
               → msg is "active"
    ---------------------------------------------------------------------------------
    WRONG ANSWER, NO ERROR, NO WARNING. And it is one missing keyword on a line that reads correctly.

    FORM 2 — COLON STATEMENT, correct breaks, then ARCHIVED is added
    ---------------------------------------------------------------------------------
    compile → SUCCEEDS. Nothing mentions ARCHIVED.
    input ARCHIVED → no case matches, no default → the switch does NOTHING
                   → msg keeps whatever it had before, or is null
    ---------------------------------------------------------------------------------
    THE SECOND SILENT FAILURE. The enum grew and the switch did not, and the build was perfectly happy.

    FORM 3 — ARROW EXPRESSION WITH `default`, then ARCHIVED is added
    ---------------------------------------------------------------------------------
    msg = switch (s) { case NEW -> "new"; case ACTIVE -> "active";
                       case CLOSED -> "closed"; default -> "unknown"; };
    compile → SUCCEEDS.
    input ARCHIVED → "unknown"
    ---------------------------------------------------------------------------------
    BETTER THAN FORM 2 — at least the value is defined — AND THE COMPILER STILL SAID NOTHING. You get a
    plausible default in production instead of a build failure in CI. That is the trade `default` makes,
    and it is why omitting it is a deliberate choice rather than an oversight.

    FORM 4 — ARROW EXPRESSION, NO `default`, then ARCHIVED is added
    ---------------------------------------------------------------------------------
    msg = switch (s) { case NEW -> "new"; case ACTIVE -> "active";
                       case CLOSED -> "closed"; };
    compile → ERROR: the switch expression does not cover all possible input values
    ---------------------------------------------------------------------------------
    EVERY SITE THAT NEEDS ATTENTION IS LISTED, BEFORE ANYTHING SHIPS. Four forms, one enum change, and
    only the fourth tells you.

NOW THE BYTECODE TRACE, which explains the type restrictions:

    case values        bytecode        how it dispatches            cost
    ---------------------------------------------------------------------------------
    1, 2, 3, 4, 5      tableswitch     index = value - 1;            O(1)
                                       jump to offsets[index]
    1, 100, 5000       lookupswitch    binary search over sorted     O(log n)
                                       (key, offset) pairs
    1, 2, 3, 9         tableswitch     a jump table WITH PADDING     O(1) — javac
                                       for 4..8                     accepts some waste
                                                                    to keep the table
    equivalent if-else n/a             compare in turn               O(n), averaging
                                                                    n/2
    ---------------------------------------------------------------------------------
    A DENSE SWITCH OVER 200 CASES IS ONE INDEXED JUMP. The if-else chain averages 100 comparisons. That
    difference is the entire reason the construct exists — and it is why `long` is excluded, since both
    bytecodes index on an `int`.

AND THE STRING TRACE, which explains the NPE:

    switch ("beta") { case "alpha" -> 1; case "beta" -> 2; default -> 0; }
    step  what the compiled code does
    ---------------------------------------------------------------------------------
    1     lookupswitch on "beta".hashCode()      ← THE CALL THAT NPEs ON NULL
    2     hash matched a bucket → call "beta".equals("beta")   ← guards against a hash
                                                                 collision
    3     set a synthetic index = 1
    4     tableswitch on that index → the "beta" arm
    ---------------------------------------------------------------------------------
    TWO SWITCHES AND AN equals CALL. Fast, and not the single jump people assume — and step 1 is exactly
    why `switch (nullString)` has always thrown.

WHAT PRODUCED WHAT:
    C HERITAGE               produced fall-through, and form 1.
    STATEMENTS NOT NEEDING   produced form 2 — nothing required the switch to be complete.
    A VALUE
    EXPRESSIONS NEEDING      produced form 4's compile error. Exhaustiveness is a consequence of
    A VALUE                  having to produce one.
    int-INDEXED BYTECODES    produced the allowed-type list, including the absence of `long`.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `tableswitch`: O(1) — subtract, index, jump. Used for dense case values.
    `lookupswitch`: O(log n) binary search. Used for sparse values.
    An if-else chain: O(n), averaging n/2 comparisons.
    A `String` switch: a hash lookup plus an `equals` call — two switches, not one jump.
    An `enum` switch: a synthetic `$SwitchMap` from ordinal to a dense int, then `tableswitch`.
    Allowed: byte, short, char, int and wrappers, String, enum, and (Java 21) any reference with
    patterns. NOT long, float, double or boolean.

THE #1 MISTAKE: a missing `break` in the colon form. Silent, plausible, and one keyword.

THE #2 MISTAKE: writing `default` in an exhaustive enum or sealed switch. It compiles and destroys the
guarantee that made the expression form worth using.

THE #3 MISTAKE: adding an enum constant with old-style statement switches in the codebase. Nothing
breaks and nothing happens for the new constant.

THE #4 MISTAKE: `switch` on a possibly-null `String` or enum. It calls `hashCode()`/`ordinal()` and
throws. `case null` since Java 21.

THE #5 MISTAKE: `return` inside a switch expression. A compile error; use `yield`.

THE #6 MISTAKE: declaring variables in a colon arm without braces. The whole body is one scope.

THE #7 MISTAKE: intentional fall-through with no comment. Unreviewable. Use comma-separated labels
instead.

THE #8 MISTAKE: mixing colon and arrow labels in one switch. Not allowed.

THE #9 MISTAKE: assuming every switch is a jump table. Sparse values give a binary search, and String
gives a hash lookup plus `equals`.

THE #10 MISTAKE: a fifty-case switch whose arms all return constants. That is a `Map`.

THE #11 MISTAKE: the same switch over the same set duplicated across files. That is polymorphism or a
sealed hierarchy asking to be written.

THE #12 MISTAKE: ordering patterns general-to-specific. A dominating label first is a compile error, and
that check is helping you.

ONE-SENTENCE TAKEAWAY: the classic `switch` selects a STARTING POINT rather than a block, so a missing
`break` falls into every case below it silently — while the arrow form removes fall-through (in
statements as well as expressions) and the EXPRESSION form, by requiring a value on every path, gives
the compiler exhaustiveness checking, which is why adding an enum constant breaks the build at every
site that matters unless you write `default` and trade that compile error back for a runtime surprise;
underneath, `switch` exists because dense cases compile to a `tableswitch` jump table that is O(1)
regardless of case count, which is also why you cannot switch on a `long` (both bytecodes index on an
`int`) and why switching on a null `String` throws — the compiled form calls `hashCode()` on it.""",
]


DEEP["What actually happens when you run a Java program?"] = [
"""1. THE GOAL IN PLAIN ENGLISH — two compilers, and a portable middle step

You write `Hello.java`. You run `javac Hello.java` and then `java Hello`. Between those two commands
something happens that is different from C, Python or Go, and understanding it explains most of Java's
character — its portability, its slow startup, and why it gets faster the longer it runs.

    `javac` DOES NOT PRODUCE MACHINE CODE. It produces BYTECODE — instructions for an imaginary machine
    that no physical CPU implements. A `.class` file will not run on your processor.

    `java` STARTS A VIRTUAL MACHINE that reads those instructions and executes them. At first it
    INTERPRETS them one at a time, while watching which parts run often. Then a SECOND compiler — the
    JIT, inside the running JVM — translates the hot parts into real machine code, using what it
    observed.

    SO JAVA IS COMPILED TWICE: ONCE AHEAD OF TIME, TO A PORTABLE FORMAT, AND AGAIN AT RUNTIME, TO THE
    ACTUAL MACHINE. That is the whole design, and everything else follows from it.

WHAT IT BUYS AND WHAT IT COSTS:

    BUYS PORTABILITY. The `.class` file is the artifact you ship, and it is identical on Linux, Windows
    and macOS, on x86 and ARM. "Write once, run anywhere" is a statement about the BYTECODE, not about
    the JVM — you need a platform-specific JVM, and that is precisely the point: the platform-specific
    part is written once, by someone else.
    BUYS RUNTIME OPTIMISATION. Because the second compilation happens while the program runs, it can
    use facts an ahead-of-time compiler can never know — which branches are actually taken, which types
    actually appear at a call.
    COSTS STARTUP. The JVM must start, load and verify classes, and interpret before it optimises. A
    "hello world" that a native binary does in a millisecond takes tens of milliseconds.
    COSTS WARM-UP. The first few thousand executions of a method are slow. This is why benchmarks
    without warm-up are meaningless.

THE EVERYDAY VERSION: writing instructions in a universal notation instead of one country's language.
Anyone anywhere can follow them if they have the notation's handbook. It is slower than instructions
already in your own language — until the reader notices you keep repeating the same section and writes
themselves a shortcut in their own language for it.

TERMS AS THEY APPEAR:
- BYTECODE: the instruction set of the JVM. One byte per opcode, roughly 200 of them.
- CLASS FILE: the compiled form of one class. Starts with the bytes `CAFEBABE`.
- VERIFIER: the component that proves the bytecode is safe before it runs.
- JIT: the just-in-time compiler inside the JVM.""",

"""2. THE INTUITION — a stack machine, and why it is one

JVM BYTECODE IS A STACK MACHINE, NOT A REGISTER MACHINE. `a + b` compiles to:

    iload_1        push local variable 1
    iload_2        push local variable 2
    iadd           pop two, add, push the result
    istore_3       pop, store into local 3

    NO REGISTERS ARE NAMED ANYWHERE. Every instruction operates on an implicit operand stack.

    WHY? THREE REASONS, AND THEY ARE THE REASON THE FORMAT HAS SURVIVED THIRTY YEARS:

    IT IS PLATFORM-NEUTRAL BY CONSTRUCTION. Real CPUs have different numbers of registers — x86 has 16,
    ARM has 31, older x86 had 8. Naming registers in the portable format would have baked one
    architecture's shape into it. A stack has no such number.
    IT IS COMPACT. Most instructions need no operands at all, because the stack says where the values
    are. `iadd` is ONE BYTE. That mattered enormously when class files were downloaded over modems, and
    it still matters for the code cache and for class-loading time.
    IT IS EASY TO VERIFY. The verifier can simulate the stack's shape through every path of a method and
    prove that it never underflows and that types always match. Register allocation would have made
    that far harder, and verification is what makes Java memory-safe.

    THE COST IS THAT A STACK MACHINE IS SLOW TO INTERPRET — every value moves through the stack. WHICH
    IS FINE, BECAUSE INTERPRETING IS NOT THE POINT: THE JIT COMPILES THE HOT PARTS TO REAL REGISTER CODE
    ANYWAY. The bytecode's job is to be a portable, verifiable, compact DESCRIPTION, not to be fast.

THE SECOND intuition: A CLASS FILE IS FULL OF NAMES, NOT ADDRESSES.

    When your code calls `System.out.println("hi")`, the class file does not contain an address. It
    contains a SYMBOLIC REFERENCE: the string "java/lang/System", the field name "out", its descriptor,
    the method name "println" and its descriptor. All of it lives in the CONSTANT POOL at the top of the
    file.

    THOSE NAMES ARE RESOLVED TO REAL LOCATIONS LAZILY, THE FIRST TIME EACH IS USED. Which is why:
    you can compile against one version of a library and run against another, as long as the names and
    descriptors still match — this is what binary compatibility means;
    a missing class is discovered when it is first NEEDED, not at startup, which is why
    `NoClassDefFoundError` appears mid-run rather than at launch;
    changing a method's PARAMETER TYPES is a breaking change even though the name is the same, because
    the descriptor is part of the reference. Hence `NoSuchMethodError` for a method that plainly
    exists — under a different descriptor.""",

"""3. THE MECHANISM — from source to a running `main`

STEP 1 — `javac`. Parses, type-checks, and emits one `.class` file per class (including nested and
anonymous ones — `Outer$1.class`). It performs only modest optimisation: constant folding of
compile-time constants, string concatenation lowering, and syntactic sugar (generics erasure, enhanced
`for` to iterators, autoboxing, lambdas to `invokedynamic`). ALMOST ALL REAL OPTIMISATION IS LEFT TO THE
JIT, deliberately, because the JIT knows more.

STEP 2 — THE CLASS FILE, whose structure is worth being able to name:

    CAFEBABE            the magic number
    minor/major version 65 = Java 21, 61 = 17, 52 = 8. A newer file on an older JVM gives
                        `UnsupportedClassVersionError`, which names both numbers.
    CONSTANT POOL       every string, class name, method name and descriptor. The bulk of the file.
    access flags, this class, super class, interfaces
    fields, methods     each method carries a `Code` attribute with `max_stack`, `max_locals` and the
                        bytecode itself
    attributes          `LineNumberTable` (for stack traces), `LocalVariableTable` (for debuggers, only
                        with `-g`), `Signature` (generic types, which survive erasure), `StackMapTable`
                        (precomputed type states that make verification fast)

STEP 3 — THE `java` LAUNCHER. It is a small native program that: creates the JVM by calling
`JNI_CreateJavaVM` in `libjvm`; initialises the heap and the GC; starts the bootstrap class loader;
initialises core classes in phases (`System.initPhase1/2/3` — which is why an exception during startup
can produce an unhelpfully bare stack trace); loads YOUR main class; verifies, links and initialises it;
and finally invokes `main(String[])` on the "main" thread.

STEP 4 — LOADING, LINKING, INITIALISING each class as it is first needed:
    LOAD      find the bytes, delegate to the parent loader first.
    VERIFY    prove the bytecode is well-formed: the stack cannot underflow, types match, jumps land
              inside the method, a local holding an `int` is never used as a reference. THIS IS WHY PURE
              JAVA BYTECODE CANNOT CORRUPT MEMORY.
    PREPARE   static fields get default values.
    RESOLVE   symbolic references become real ones — lazily, on first use.
    INITIALISE run `<clinit>`. Once, ever.

STEP 5 — EXECUTION. Tier 0 interprets while collecting a profile; roughly a couple of hundred
invocations later a method is compiled by C1 with instrumentation; around ten thousand it is recompiled
by C2 using the profile — inlining monomorphic calls, replacing never-taken branches with traps, and
eliminating allocations that provably never escape.

STEP 6 — SHUTDOWN. The JVM exits when all NON-DAEMON threads finish, or on `System.exit`, or on a fatal
signal. Registered shutdown hooks run — unless the process is killed with `SIGKILL` or the JVM crashes.
THIS IS WHY A FORGOTTEN THREAD POOL KEEPS A PROGRAM ALIVE AFTER `main` RETURNS: its threads are
non-daemon by default.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `UnsupportedClassVersionError`. A class file compiled by a newer JDK than the JVM running it.
The message gives both version numbers — 65 is Java 21, 61 is 17, 52 is 8. Compile with `--release`, not
just `-source`/`-target`, so the API surface matches too.

CASE 2 — `NoClassDefFoundError` MID-RUN. Resolution is LAZY, so a missing class surfaces when it is
first needed, possibly hours in — or the class is present and its `<clinit>` already failed.

CASE 3 — `NoSuchMethodError` FOR A METHOD THAT PLAINLY EXISTS. The DESCRIPTOR is part of the symbolic
reference, so a changed parameter or return type is a different method. Usually two library versions on
the classpath.

CASE 4 — `-source`/`-target` WITHOUT `--release`. You get the old bytecode version and the NEW JDK's
API, so the code compiles and then fails at runtime on an older JVM with `NoSuchMethodError`.

CASE 5 — `main` WITH THE WRONG SIGNATURE. It must be `public static void main(String[])`.
`String... args` works, because varargs IS an array. Anything else gives "Main method not found".

CASE 6 — THE PROGRAM NOT EXITING AFTER `main` RETURNS. A non-daemon thread — usually an executor nobody
shut down — is still alive. `setDaemon(true)` or a proper shutdown.

CASE 7 — SHUTDOWN HOOKS NOT RUNNING. `SIGKILL`, `Runtime.halt()`, a JVM crash, or a container's grace
period expiring. Hooks are best-effort, not a guarantee.

CASE 8 — A SLOW FIRST REQUEST IN PRODUCTION. Class loading plus interpretation plus JIT warm-up. This is
why services are warmed with synthetic traffic before joining a load balancer.

CASE 9 — A STACK TRACE WITH NO LINE NUMBERS. Compiled without `-g:lines`, or the `LineNumberTable` was
stripped by an obfuscator or a size-optimising build.

CASE 10 — A TRACE-LESS `NullPointerException` IN PRODUCTION. Not a logging bug: after enough throws
from one site, HotSpot recompiles it to throw a pre-allocated exception with no stack trace.
`-XX:-OmitStackTraceInFastThrow` while diagnosing.

CASE 11 — SPLIT PACKAGES OR MISSING `--add-opens` UNDER THE MODULE SYSTEM. Reflection into JDK internals
that worked on Java 8 is refused from Java 17 onward.

CASE 12 — ASSUMING `javac` OPTIMISES. It barely does. Do not hand-optimise source for the compiler's
benefit; optimise for the JIT, and mostly do not optimise at all.

CASE 13 — A FAT JAR WITH DUPLICATE CLASSES. The classpath is order-dependent and silent; the first
match wins.""",

"""5. THE ALTERNATIVES — other ways to get Java code running

`java Hello.java` (JAVA 11) — SINGLE-FILE SOURCE LAUNCH. Compiles in memory and runs, with no `.class`
file produced. Excellent for scripts and for reproducing a bug in one file. Java 22 extended it to
multi-file programs.

JSHELL (Java 9) — a REPL. The fastest way to answer "what does this actually return".

`jlink` — build a custom runtime image containing only the modules you use. A 40 MB runtime instead of
200 MB, which matters for container images.

`jpackage` — produce a platform-native installer bundling the runtime.

GRAALVM NATIVE IMAGE — AHEAD-OF-TIME compile the whole application to a native binary. This is the real
alternative to the model in this entry:
    GAINS millisecond startup, low memory, no warm-up, no JVM to ship.
    LOSES peak throughput, because it never sees a runtime profile. And it requires a CLOSED WORLD:
    reflection, dynamic proxies and resource loading must be declared at build time.
    THE TRADE IS EXPLICIT: right for CLI tools and serverless functions that exit before they warm up;
    wrong for a long-running server, where the JIT eventually wins.

CLASS DATA SHARING (`-Xshare`, AppCDS) — pre-parse and memory-map class metadata so startup skips work
and several JVMs share it. A real startup improvement with no downside worth mentioning.

PROJECT LEYDEN is the ongoing work to shift more of this earlier — caching JIT decisions and class
loading across runs — which is worth knowing as the direction of travel.

TOOLS FOR SEEING ANY OF THIS:
    `javap -c -p Foo.class` — the bytecode, and the single best way to answer "what does the compiler
    actually do with this". Read it once for a string concatenation and once for a lambda.
    `-verbose:class` — every class as it loads, and where it came from.
    `-XX:+PrintCompilation` — the JIT's decisions, live, with `%` marking on-stack replacement and
    `made not entrant` marking a deoptimisation.
    `jcmd <pid> VM.command_line`, `VM.flags` — what this JVM is actually running with, which is often
    not what anyone believes.

WHAT TO SAY: "`javac` produces bytecode for a stack machine, not machine code — that is the portable
artifact, and it is a stack machine because it has to be architecture-neutral, compact and verifiable.
The JVM interprets it while profiling, then JIT-compiles the hot parts using facts an ahead-of-time
compiler could never know. That buys portability and peak performance and costs startup and warm-up,
which is exactly the trade GraalVM native image reverses."

""",

"""6. HOW TO USE THIS KNOWLEDGE — numbered steps

STEP 1 — WHEN BEHAVIOUR SURPRISES YOU, READ THE BYTECODE. `javap -c -p`. String concatenation, lambdas,
enhanced `for`, autoboxing and generics all look different from the source, and one look settles the
argument.

STEP 2 — COMPILE WITH `--release N`, NOT `-source`/`-target`. Only `--release` also restricts the API
surface, so you cannot accidentally use a newer method.

STEP 3 — READ THE VERSION NUMBERS IN `UnsupportedClassVersionError`. 65 = 21, 61 = 17, 52 = 8. The
message tells you both halves of the mismatch.

STEP 4 — EXPECT RESOLUTION TO BE LAZY. A missing class or method appears when first used, not at
startup. Integration tests that exercise every path find these; unit tests do not.

STEP 5 — WARM UP BEFORE MEASURING, AND BEFORE SERVING. Several thousand iterations for a benchmark;
synthetic traffic before a new instance joins the load balancer.

STEP 6 — MAKE BACKGROUND THREADS DAEMONS, OR SHUT THEM DOWN. Otherwise the JVM will not exit after
`main` returns.

STEP 7 — TREAT SHUTDOWN HOOKS AS BEST-EFFORT. They do not run on `SIGKILL`, `Runtime.halt()`, or a crash.

STEP 8 — KEEP `-g:lines` ON IN PRODUCTION BUILDS. Line numbers in stack traces cost almost nothing and
are worth a great deal at 3am.

STEP 9 — USE `java Hello.java` OR `jshell` TO ANSWER SMALL QUESTIONS. Far faster than building a project
to test one behaviour.

STEP 10 — CONSIDER `jlink` OR AppCDS FOR CONTAINER STARTUP, and native image only when the process is
short-lived enough never to warm up.

STEP 11 — DO NOT HAND-OPTIMISE FOR `javac`. It barely optimises; the JIT does the work, and it does it
better with straightforward code.

STEP 12 — WHEN A JVM BEHAVES UNEXPECTEDLY, CHECK WHAT IT IS ACTUALLY RUNNING WITH.
`jcmd <pid> VM.command_line` and `VM.flags` — inherited flag lists are often obsolete or contradictory.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'The thing that makes Java different is that it's compiled TWICE. javac produces BYTECODE — instructions
for an imaginary machine that no physical CPU implements — and then the JVM reads those, interprets them
at first while watching which parts run often, and a second compiler inside the running JVM translates
the hot parts into real machine code using what it observed.

So the .class file is the portable artifact. It's byte-for-byte identical on Linux, Windows and macOS,
on x86 and ARM. "Write once, run anywhere" is a claim about the BYTECODE — you still need a
platform-specific JVM, and that's the point: the platform-specific part is written once, by someone
else.

The bytecode is a STACK machine, not a register machine. `a + b` is iload, iload, iadd, istore — no
registers are named anywhere. Three reasons, and they're why the format has survived thirty years. It's
architecture-neutral by construction: real CPUs have different register counts, so naming registers
would have baked one architecture into the portable format. It's compact — most instructions need no
operands because the stack says where the values are, so iadd is ONE BYTE, which mattered when class
files came over modems and still matters for load time. And it's easy to VERIFY: the verifier can
simulate the stack shape through every path and prove it never underflows and that types always match.
That verification is what makes pure Java bytecode unable to corrupt memory.

A stack machine is slow to interpret, and that's fine, because interpreting isn't the point — the JIT
compiles the hot parts to real register code anyway. The bytecode's job is to be a portable, verifiable,
compact DESCRIPTION.

The other thing worth knowing is that a class file is full of NAMES, not addresses. Calling
System.out.println stores the strings "java/lang/System", "out", "println" and their descriptors in a
constant pool, and those are resolved to real locations LAZILY, the first time each is used. Which
explains three things at once: you can compile against one library version and run against another as
long as names and descriptors match — that's what binary compatibility IS; a missing class surfaces
mid-run rather than at startup, hence NoClassDefFoundError appearing hours in; and changing a method's
parameter types is a breaking change even though the name is unchanged, because the descriptor is part
of the reference. That's where NoSuchMethodError for a method that plainly exists comes from.

The trade is explicit. You buy portability, and you buy runtime optimisation the JIT can only do because
it sees what actually happened. You pay startup — the JVM has to boot, load and verify classes — and you
pay warm-up, which is why an unwarmed benchmark is meaningless. GraalVM native image reverses exactly
that trade: millisecond startup, lower peak, and a closed world where reflection has to be declared.'""",

"""8. THE CODE, LINE BY LINE

    // ── WHAT javac PRODUCES ─────────────────────────────────────────────
    int add(int a, int b) { return a + b; }
    // javap -c:
    //   iload_1        push local 1        ← NO REGISTERS ARE NAMED. It is a STACK
    //   iload_2        push local 2           machine, because real CPUs disagree
    //   iadd           pop 2, add, push 1     about how many registers exist.
    //   ireturn        pop and return
    // `iadd` is ONE BYTE — most instructions need no operands, because the stack
    // already says where the values are.

    // ── A CLASS FILE IS NAMES, NOT ADDRESSES ────────────────────────────
    System.out.println("hi");
    // the class file stores SYMBOLIC references in the constant pool:
    //   Class     java/lang/System
    //   Fieldref  System.out : Ljava/io/PrintStream;
    //   Methodref PrintStream.println : (Ljava/lang/String;)V
    //                                   ^^^^^^^^^^^^^^^^^^^^^ THE DESCRIPTOR IS PART
    //   OF THE REFERENCE. Change a parameter type and it is a DIFFERENT method —
    //   which is why you get NoSuchMethodError for a method that plainly exists.
    // These are resolved to real locations LAZILY, on first use. Which is why a
    // missing class appears MID-RUN, not at startup.

    // ── THE CLASS FILE HEADER ───────────────────────────────────────────
    // CAFEBABE                 magic
    // 00 00 00 41              minor 0, major 65 = Java 21   (61 = 17, 52 = 8)
    // constant pool ...        every name, string and descriptor. The bulk of the file.
    // methods → Code attribute → max_stack, max_locals, the bytecode
    // attributes: LineNumberTable   (stack traces — keep -g:lines in production)
    //             LocalVariableTable (debuggers — only with -g)
    //             Signature          (generic types, which SURVIVE erasure)
    //             StackMapTable      (precomputed type states, so verification is fast)

    // ── THE LAUNCH SEQUENCE ─────────────────────────────────────────────
    // java Hello
    //  1. the `java` launcher calls JNI_CreateJavaVM in libjvm
    //  2. heap and GC initialised; bootstrap class loader started
    //  3. core classes initialised in phases (System.initPhase1/2/3) — which is why
    //     a startup failure can produce a bare, unhelpful stack trace
    //  4. Hello is LOADED → VERIFIED → PREPARED → RESOLVED (lazily) → INITIALISED
    //  5. main(String[]) invoked on the "main" thread
    //  6. the JVM exits when all NON-DAEMON threads finish

    public static void main(String[] args)      // ✓
    public static void main(String... args)     // ✓ varargs IS an array
    public static void main(String args)        // ✗ "Main method not found"

    // ── WHY THE PROGRAM DOES NOT EXIT ───────────────────────────────────
    var pool = Executors.newFixedThreadPool(4);
    pool.submit(task);
    // main returns... AND THE PROCESS HANGS. Pool threads are NON-DAEMON by default,
    // and the JVM exits only when every non-daemon thread has finished.
    pool.shutdown();                            // ← or setDaemon(true) in a factory

    // ── THE ERROR THAT NAMES BOTH HALVES ────────────────────────────────
    // UnsupportedClassVersionError: Hello has been compiled by a more recent version
    //   of the Java Runtime (class file version 65.0), this version of the Java
    //   Runtime only recognizes class file versions up to 61.0
    //                                                    ^^ 65 = Java 21, 61 = 17
    // javac --release 17 ...     ← --release ALSO restricts the API surface.
    //                               -source/-target does not, so you get old bytecode
    //                               calling new methods, and NoSuchMethodError later.

    // ── THE TOOLS ───────────────────────────────────────────────────────
    // javap -c -p Foo.class        the bytecode. Read it once for string concat and
    //                              once for a lambda; it settles most arguments.
    // java Hello.java              Java 11: compile in memory and run. No .class file.
    // jshell                       a REPL, for "what does this actually return"
    // -verbose:class               every class as it loads, and from which jar
    // -XX:+PrintCompilation        the JIT's decisions live; % = OSR, "made not
    //                              entrant" = a deoptimisation
    // jcmd <pid> VM.command_line   what this JVM is ACTUALLY running with""",

"""9. THE TRACE — one `println`, from source to machine code

`System.out.println("hi")` INSIDE A LOOP THAT RUNS 100,000 TIMES.

    PHASE 1 — COMPILE TIME
    step  what happens                                    artifact
    ---------------------------------------------------------------------------------
    1     javac parses and type-checks                     —
    2     the string "hi" goes in the CONSTANT POOL        a CONSTANT_String entry
    3     the call becomes a symbolic Methodref            "println", descriptor
                                                           (Ljava/lang/String;)V
    4     bytecode emitted: getstatic, ldc, invokevirtual  3 instructions
    ---------------------------------------------------------------------------------
    NOTHING WAS RESOLVED. The class file contains the NAME of `System.out` and the NAME and DESCRIPTOR
    of `println`. No address exists anywhere in it.

    PHASE 2 — FIRST EXECUTION
    step  what happens                                    cost
    ---------------------------------------------------------------------------------
    5     the JVM hits `getstatic System.out` for the      class loading: delegate to
          first time → java.lang.System must be LOADED     the parent, find the bytes
    6     VERIFY: simulate the operand stack through        proportional to code size
          every path, check types and jump targets
    7     PREPARE: static fields to defaults
    8     RESOLVE: the symbolic reference becomes a real   ONCE, then cached
          field offset
    9     INITIALISE: <clinit> runs. Once, ever.
    10    the call is INTERPRETED — every bytecode          ~100x slower than compiled
          dispatched through a switch
    ---------------------------------------------------------------------------------
    STEPS 5–9 HAPPEN EXACTLY ONCE. This is the startup cost, and it is why a native binary starts in a
    millisecond and a JVM does not.

    PHASE 3 — WARMING UP
    iteration    what is executing                          relative speed
    ---------------------------------------------------------------------------------
    1            tier 0, interpreter, collecting a profile   ~100x slow
    ~500         tier 3, C1 + full profiling — real machine  ~8x
                 code, deliberately slower than tier 1
                 because it carries counters
    ~12,000      tier 4, C2. The profile is CONSUMED:        ~1x
                 the call inlined behind a class check,
                 never-taken branches replaced by traps,
                 escaping-nowhere objects not allocated
    ---------------------------------------------------------------------------------
    THE SAME LINE RAN AT THREE DIFFERENT SPEEDS IN ONE PROGRAM. Which is the whole reason an unwarmed
    benchmark is not slightly wrong but wrong by two orders of magnitude.

NOW THE PORTABILITY TRACE — the same class file on three machines:

    machine        the .class file    what actually executes
    ---------------------------------------------------------------------------------
    x86-64 Linux   IDENTICAL bytes    x86 machine code, generated by that JVM's C2
    ARM macOS      IDENTICAL bytes    AArch64 machine code, from the same bytecode
    a phone        IDENTICAL bytes    whatever that runtime produces
    ---------------------------------------------------------------------------------
    THE PORTABLE THING IS THE DESCRIPTION, NOT THE EXECUTION. Every machine ends up running native code
    for its own architecture — it is just generated locally, at runtime, from a shared description.
    THAT is what "write once, run anywhere" actually means, and it is why the JVM itself is the
    unportable part and always was.

AND THE LAZY-RESOLUTION TRACE, which explains two familiar errors:

    situation                                    when you find out
    ---------------------------------------------------------------------------------
    a class referenced but never reached          NEVER. The program runs fine.
    a class on a rarely-taken branch, missing     when that branch first runs — possibly
    from the runtime classpath                    hours in → NoClassDefFoundError
    a method whose parameter type changed in a    when that call first runs →
    newer library                                 NoSuchMethodError, for a method that
                                                  is visibly present in the jar
    ---------------------------------------------------------------------------------
    ALL THREE ARE THE SAME MECHANISM: names are resolved on FIRST USE, and the descriptor is part of the
    name. Which is also why binary compatibility is a real, checkable property rather than a hope.

WHAT PRODUCED WHAT:
    A STACK-BASED, NAME-BASED FORMAT   produced portability, verifiability, and lazy resolution.
    LAZY RESOLUTION                    produced mid-run NoClassDefFoundError and NoSuchMethodError.
    TWO COMPILERS                      produced the warm-up curve, and the reason benchmarks lie.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `javac` → bytecode: a stack machine, ~200 one-byte opcodes, architecture-neutral by construction.
    Class file version 65 = Java 21, 61 = 17, 52 = 8.
    Loading is lazy; resolution of symbolic references is lazy; initialisation happens once, ever.
    Verification proves the operand stack cannot underflow and types match — this is what makes
    bytecode memory-safe.
    Interpreted → C2 steady state is commonly 10–100x. Roughly a couple of hundred invocations to leave
    the interpreter, on the order of ten thousand to reach C2.
    The JVM exits when all NON-DAEMON threads finish.

THE #1 MISTAKE: thinking `javac` produces machine code, or that it optimises much. It produces a
portable description and leaves the optimisation to the JIT.

THE #2 MISTAKE: benchmarking without warm-up. You measured the interpreter, and it is not close.

THE #3 MISTAKE: `-source`/`-target` instead of `--release`. Old bytecode, new API, and a runtime failure
on the older JVM.

THE #4 MISTAKE: expecting a missing class at startup. Resolution is lazy; it surfaces on first use.

THE #5 MISTAKE: reading `NoSuchMethodError` as "the jar is missing". The descriptor is part of the
reference, so a changed signature is a different method.

THE #6 MISTAKE: forgetting non-daemon threads keep the JVM alive after `main` returns.

THE #7 MISTAKE: relying on shutdown hooks. Best-effort — not on `SIGKILL`, `halt()`, or a crash.

THE #8 MISTAKE: stripping line numbers from production builds. They cost almost nothing and are worth a
great deal during an incident.

THE #9 MISTAKE: treating a trace-less production `NullPointerException` as a logging failure. The JIT
optimised the trace away at a hot throw site.

THE #10 MISTAKE: choosing native image for a long-running server. It reverses the trade — great startup,
lower peak, closed world.

THE #11 MISTAKE: arguing about what the compiler does instead of running `javap -c`. One command settles
it.

ONE-SENTENCE TAKEAWAY: Java is compiled TWICE — `javac` emits bytecode for a STACK machine that names no
registers (so it is architecture-neutral, one byte per opcode, and simple enough for a verifier to prove
memory-safe before anything runs), and the JVM then interprets it while profiling before a second
compiler turns the hot parts into real machine code using facts no ahead-of-time compiler could know;
the class file holds SYMBOLIC names and descriptors rather than addresses, resolved lazily on first use,
which is simultaneously what makes binary compatibility possible, why `NoClassDefFoundError` arrives
mid-run, and why a changed parameter type produces `NoSuchMethodError` for a method that is plainly
there — and the whole design buys portability and peak throughput at the price of startup and warm-up,
which is exactly the trade a native image reverses.""",
]


DEEP["Varargs — and the overload ambiguity it creates"] = [
"""1. THE GOAL IN PLAIN ENGLISH — an array, with the array-making hidden

`void log(String... parts)` lets a caller write `log("a")`, `log("a", "b")` or `log()`. Inside the
method, `parts` IS AN ARRAY — `String[]`. Nothing else. The whole feature is that the COMPILER creates
the array at the CALL SITE so you do not have to.

    log("a", "b");        // compiles to:  log(new String[]{"a", "b"});
    log();                // compiles to:  log(new String[0]);

    THAT IS THE ENTIRE MECHANISM. `String...` and `String[]` are the same type at runtime; the `...`
    only changes what callers are allowed to write. You can pass an existing array directly and it is
    used AS-IS, with no wrapping.

    WHICH IMMEDIATELY EXPLAINS THE TWO SURPRISES:

    `log(null)` PASSES A NULL ARRAY, not an array containing null. `parts.length` then throws
    `NullPointerException` inside a method that looks defensive. To pass one null ELEMENT you must
    write `log((String) null)`.

    PASSING AN ARRAY SPREADS IT INSTEAD OF WRAPPING IT. `Arrays.asList(someArray)` gives a list of the
    array's ELEMENTS — usually what you want, and catastrophically not what you want when the array is
    a primitive array. See section 2; this is the single most famous varargs bug in Java.

AND THE COST NOBODY MENTIONS: EVERY VARARGS CALL ALLOCATES AN ARRAY. Even a zero-argument one, though
some JDK methods special-case that. On a hot path — a logging call, a formatting call — that allocation
is real, and it is exactly why `List.of` has eleven fixed-arity overloads before it falls back to
varargs.

THE EVERYDAY VERSION: a form that says "list any number of items". You still fill in a numbered list;
the form just prints the numbers for you. And if you hand in a list you already made, it is used as-is
— not put inside a new list of one.

TERMS AS THEY APPEAR:
- ARITY: how many arguments a method takes.
- VARIABLE ARITY METHOD: the specification's name for a varargs method.
- HEAP POLLUTION: a generic variable referring to an object of a different generic type — which varargs
  makes possible, and which `@SafeVarargs` exists to acknowledge.""",

"""2. THE INTUITION — why overload resolution treats it as a last resort

JAVA CHOOSES AMONG OVERLOADS IN THREE ORDERED PHASES, and varargs is dead last:

    PHASE 1  try to match using only WIDENING conversions. No boxing, no varargs.
    PHASE 2  if none matched, allow BOXING and unboxing. Still no varargs.
    PHASE 3  if still none, allow VARARGS.

    THE FIRST PHASE THAT FINDS ANY APPLICABLE METHOD WINS, and the later phases are never consulted.

    SO A VARARGS METHOD LOSES TO EVERYTHING. Given `f(int, int)` and `f(int...)`, the call `f(1, 2)`
    picks the fixed-arity one. Given `f(Integer)` and `f(int...)`, the call `f(1)` picks `f(Integer)` —
    boxing is phase 2, varargs is phase 3.

    WHY THE ORDER EXISTS IS THE INTERESTING PART: AUTOBOXING AND VARARGS BOTH ARRIVED IN JAVA 5, and
    neither was allowed to change the meaning of any program written before them. Making both
    last-resort guarantees that. The ordering is not a design preference; it is a backwards-compatibility
    obligation, and knowing that makes it memorable rather than arbitrary.

NOW THE FAMOUS BUG, WHICH IS VARARGS MEETING PRIMITIVES:

    Arrays.asList(new int[]{1, 2, 3})     →  a List<int[]> of SIZE 1
    Arrays.asList(new Integer[]{1, 2, 3}) →  a List<Integer> of size 3

    `asList` IS `<T> List<T> asList(T... a)`. A type parameter `T` must be a REFERENCE type — erasure
    turns it into `Object`, and a primitive is not a reference. So `int[]` cannot be spread into `T...`
    elements, because `int` cannot be a `T`. But `int[]` IS ITSELF AN OBJECT, so it matches as a single
    element, and you get one list containing one array.

    THE COMPILER IS PERFECTLY HAPPY. The result is a size-1 list and everyone expects 3, and it is
    exactly the same root cause as `List<int>` not existing. `Arrays.stream(intArray).boxed().toList()`
    is the fix.

THE SECOND STRUCTURAL ISSUE IS AMBIGUITY. Two varargs overloads can both be applicable with neither more
specific:

    f(Object...) and f(String, Object...) called as f("x")  →  AMBIGUOUS, a compile error.

    Neither is more specific: the first accepts everything the second does at that arity, and the second
    is more specific in its first parameter. THE COMPILER REFUSES RATHER THAN GUESSING, which is the
    right behaviour and produces an error message that reads like a puzzle.

AND THE GENERICS PROBLEM — HEAP POLLUTION:

    A varargs parameter of a generic type creates an array of a generic type, and Java has no such
    thing. `T...` becomes `Object[]` after erasure. That array can be aliased and written into with the
    wrong type, and nothing checks. Hence the "possible heap pollution" warning, and `@SafeVarargs` —
    which does not make anything safe, it asserts that YOU have checked the method only READS the array
    and never stores it or exposes it.""",

"""3. THE MECHANISM — what the compiler emits, and the three call shapes

THE DECLARATION `void log(String prefix, String... parts)` COMPILES TO
`void log(String prefix, String[] parts)` with an ACC_VARARGS flag on the method. That flag is the only
difference, and it exists so that callers compiled later know they may use the sugar. Reflection sees a
`String[]` parameter, and `Method.isVarArgs()` reports the flag.

THREE THINGS A CALLER CAN WRITE, AND WHAT EACH BECOMES:

    log("p", "a", "b")     →  log("p", new String[]{"a","b"})   the compiler builds the array
    log("p")               →  log("p", new String[0])           an EMPTY array, allocated
    log("p", existingArr)  →  log("p", existingArr)              PASSED AS-IS. No wrapping.

    THE THIRD ONE IS WHY YOU CANNOT PASS AN ARRAY AS A SINGLE ELEMENT WITHOUT SAYING SO. To wrap it:
    `log("p", new String[][]{existingArr})` for an array element, or more usually you wanted `spread`
    and this is fine.

THE RULES:
    THE VARARGS PARAMETER MUST BE LAST, and there can be at most ONE. Otherwise a call would be
    ambiguous about where the variable part ends.
    A VARARGS METHOD CAN BE OVERRIDDEN by one taking an array, and vice versa — they are the same
    erasure — but the compiler warns, because callers of the two forms behave differently.
    `main(String... args)` IS A VALID ENTRY POINT, because it is exactly `main(String[])`.

THE ALLOCATION COST, and how the JDK responds to it:

    EVERY CALL ALLOCATES. `List.of("a")` would allocate a one-element array on every call if it were
    varargs-only — so `List.of` declares ELEVEN fixed-arity overloads (`of()`, `of(E)`, `of(E,E)` …
    up to ten) and only then a varargs one. `Map.of` does the same. `EnumSet.of` does the same.
    THAT IS NOT STYLE; IT IS AN ALLOCATION AVOIDANCE MEASURE in code that runs everywhere.
    Escape analysis often removes the array when the method is inlined and the array provably does not
    escape — so on a warm hot path the cost may be zero. On a cold path, or where the method is too big
    to inline, it is not.

`@SafeVarargs` — where it may be applied and what it means:
    Applicable to `static` methods, `final` instance methods, `private` instance methods (Java 9+), and
    constructors — that is, anything that cannot be overridden, because an override could break the
    promise.
    IT SUPPRESSES THE WARNING. IT DOES NOT MAKE ANYTHING SAFE. You are asserting that the method only
    reads from the varargs array and never stores it, returns it, or lets it escape somewhere it could
    be written through.

`Arrays.stream`, `String.format`, `Logger.log`, `EnumSet.of`, `Objects.hash`, `List.of`, `Stream.of` —
the varargs API surface is enormous, which is why the resolution rules matter more than the feature's
apparent simplicity.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `f(null)` PASSES A NULL ARRAY. `args.length` throws `NullPointerException` inside a method that
was written defensively. `f((String) null)` passes an array of one null.

CASE 2 — `Arrays.asList(intArray)` GIVES A `List<int[]>` OF SIZE 1. A type parameter cannot be a
primitive, so the `int[]` matches as a single element. The most famous varargs bug in Java, and the
compiler is content.

CASE 3 — PASSING AN `Object[]` TO `f(Object...)` SPREADS IT. If you meant to pass the array itself as
one element, you must wrap it explicitly.

CASE 4 — VARARGS LOSES EVERY OVERLOAD CONTEST. `f(int, int)` beats `f(int...)`; `f(Integer)` beats
`f(int...)`. Phases 1 and 2 come first, for backwards compatibility with pre-Java-5 code.

CASE 5 — TWO APPLICABLE VARARGS OVERLOADS WITH NEITHER MORE SPECIFIC. `f(Object...)` and
`f(String, Object...)` called as `f("x")` is a compile error. The compiler refuses to guess.

CASE 6 — HEAP POLLUTION WITH GENERIC VARARGS. `T...` erases to `Object[]`, which can be aliased and
written with the wrong type. Hence the warning and `@SafeVarargs`.

CASE 7 — `@SafeVarargs` READ AS A SAFETY MECHANISM. It only suppresses the warning; you are asserting
the method never stores or exposes the array.

CASE 8 — AN ALLOCATION PER CALL ON A HOT PATH. `log.debug("x", a, b)` allocates an array even when the
level is disabled — and so does the string concatenation, if you wrote one.

CASE 9 — `String.format("%s", someArray)` PRINTING SOMETHING ODD. `format` is varargs, so an
`Object[]` is SPREAD into the format arguments rather than being one argument.

CASE 10 — OVERLOADING A VARARGS METHOD WITH AN ARRAY VERSION. Same erasure, so it does not compile as
two methods — and where it does apply (an override), the two call shapes behave differently.

CASE 11 — VARARGS PLUS AUTOBOXING. `f(Integer... xs)` called with `f(1, 2)` boxes both AND allocates the
array. Two costs, neither visible.

CASE 12 — REFLECTION. `Method.invoke` takes `Object...`, so invoking a method whose single parameter is
an `Object[]` requires wrapping: `invoke(target, new Object[]{ theArray })`.

CASE 13 — A VARARGS PARAMETER THAT IS NOT LAST. A compile error, and necessarily so: there would be no
way to tell where the variable part ends.""",

"""5. THE ALTERNATIVES — and when not to use varargs at all

AN EXPLICIT `List<T>` PARAMETER. Clearer, no allocation surprise, no null-array trap, no ambiguity, and
composable — a caller who already has a collection does not have to convert it. FOR ANYTHING WITH MORE
THAN A COUPLE OF ARGUMENTS, THIS IS USUALLY THE BETTER SIGNATURE.

FIXED-ARITY OVERLOADS FOR THE COMMON CASES, with a varargs fallback. Exactly what `List.of`, `Map.of`
and `EnumSet.of` do — ten explicit arities, then varargs. It removes the allocation for the calls that
actually happen and keeps the general form available.

`Collection<T>` OR `Iterable<T>` for input, so callers can pass whatever they have.

A BUILDER when there are several optional things, rather than a varargs of alternating key/value pairs.
`Map.of("a",1,"b",2)` is convenient and untyped in its pairing; a builder is typed.

PARAMETERISED LOGGING RATHER THAN A HOT VARARGS CALL. `log.debug("x {}", v)` — the SLF4J API has
fixed-arity overloads for one and two arguments precisely to avoid the array allocation on a disabled
level.

`Arrays.stream(intArray).boxed().toList()` INSTEAD OF `Arrays.asList(intArray)`. And
`IntStream.of(intArray)` when you want to stay primitive.

`Objects.requireNonNull(args, "args")` AT THE TOP OF A VARARGS METHOD if you accept references, because
`f(null)` really does hand you null.

FOR GENERIC VARARGS: prefer `List<T>` over `T...` wherever you can, since it sidesteps heap pollution
entirely. When you cannot, apply `@SafeVarargs` and genuinely verify that the method only reads.

WHEN VARARGS IS RIGHT: `String.format`, `List.of`, `EnumSet.of`, `Objects.hash`, assertion helpers,
logging APIs — cases where the arguments are HETEROGENEOUS OR FEW, where the call sites are numerous,
and where the readability gain at the call site is the whole point.

WHEN IT IS WRONG: as a substitute for a collection parameter; in a method that is called in a tight
loop; in any signature that already has close overloads, because it turns overload resolution into a
puzzle.

WHAT TO SAY: "It is sugar for an array built at the call site, so the runtime type is just `String[]` —
which is why `f(null)` passes a null ARRAY and why passing an existing array spreads rather than wraps.
Overload resolution treats it as a LAST resort, in phase three after widening and boxing, because
autoboxing and varargs both arrived in Java 5 and neither was allowed to change the meaning of existing
code. And I would usually take a `List` instead once there are more than a couple of arguments."

""",

"""6. HOW TO USE VARARGS WELL — numbered steps

STEP 1 — ASK WHETHER A `List` OR `Collection` PARAMETER IS BETTER. Usually it is, once there is more
than a handful of arguments.

STEP 2 — NULL-CHECK THE ARRAY ITSELF. `f(null)` hands you a null array, not an empty one.

STEP 3 — REMEMBER PASSING AN ARRAY SPREADS IT. If you meant one element, wrap it explicitly.

STEP 4 — NEVER PASS A PRIMITIVE ARRAY TO A GENERIC VARARGS METHOD. `Arrays.asList(intArray)` is a
size-1 list. Use `Arrays.stream(...).boxed()`.

STEP 5 — EXPECT VARARGS TO LOSE EVERY OVERLOAD CONTEST. It is phase three, after widening and boxing.

STEP 6 — DO NOT ADD A VARARGS OVERLOAD NEXT TO CLOSE FIXED-ARITY ONES. Ambiguity errors here read like
puzzles, and readers cannot predict which one runs.

STEP 7 — PROVIDE FIXED-ARITY OVERLOADS FOR HOT COMMON CASES. `List.of` does it ten times over, and for
a reason.

STEP 8 — KEEP VARARGS OUT OF TIGHT LOOPS. Every call allocates, unless escape analysis happens to remove
it.

STEP 9 — USE PARAMETERISED LOGGING. Fixed-arity overloads for one and two arguments avoid the array when
the level is disabled.

STEP 10 — WITH GENERIC VARARGS, PREFER `List<T>`; OTHERWISE APPLY `@SafeVarargs` AND ACTUALLY CHECK that
the method only reads the array.

STEP 11 — DOCUMENT WHAT ZERO ARGUMENTS MEANS. `f()` is legal and gives an empty array; decide whether
that is "nothing" or an error, and say so.

STEP 12 — WHEN REFLECTING, WRAP AN ARRAY ARGUMENT. `Method.invoke` is itself varargs, so a single
`Object[]` parameter needs `new Object[]{ theArray }`.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'Varargs is sugar. `void log(String... parts)` compiles to `log(String[] parts)` with a flag on the
method, and at each CALL SITE the compiler builds the array for you. `log("a","b")` becomes `log(new
String[]{"a","b"})`, and `log()` becomes `log(new String[0])`. Inside the method it is just an array,
and `String...` and `String[]` are the same type at runtime.

Which immediately explains the two surprises. `log(null)` passes a NULL ARRAY, not an array containing
null — so `parts.length` throws inside a method that looks defensive. To pass one null element you have
to write `log((String) null)`. And passing an existing array SPREADS it rather than wrapping it, because
the array is used as-is.

That second one gives the most famous varargs bug in Java. `Arrays.asList(new int[]{1,2,3})` returns a
List of SIZE ONE — a `List<int[]>`. Because asList is `<T> List<T> asList(T... a)`, and a type parameter
must be a REFERENCE type; erasure makes T an Object and a primitive isn't one. So `int` can't be a T and
the array can't be spread — but `int[]` is itself an object, so it matches as a single element. The
compiler is perfectly happy, you expected three, and it's exactly the same root cause as `List<int>` not
existing. The fix is `Arrays.stream(arr).boxed().toList()`.

On overload resolution: varargs is a LAST resort. Java picks among overloads in three ordered phases —
widening only, then boxing allowed, then varargs allowed — and the first phase that finds anything wins.
So `f(int,int)` beats `f(int...)`, and `f(Integer)` beats `f(int...)` because boxing is phase two.

The reason for that order is the part worth saying: autoboxing and varargs BOTH arrived in Java 5, and
neither was allowed to change the meaning of any program written before them. Making both last-resort
guarantees it. It's not a design preference, it's a backwards-compatibility obligation.

Two more things. Every varargs call ALLOCATES an array — which is why `List.of` has eleven fixed-arity
overloads before falling back to varargs, and `Map.of` and `EnumSet.of` do the same. That's not style,
it's allocation avoidance in code that runs everywhere. Escape analysis often removes it on a warm
inlined path, but not on a cold one.

And generic varargs cause HEAP POLLUTION, because `T...` erases to `Object[]` and Java has no real
generic arrays — the array can be aliased and written with the wrong type. That's what the "possible
heap pollution" warning is, and `@SafeVarargs` doesn't make anything safe; it's you asserting the method
only READS the array and never stores or exposes it.

Practically, once there are more than a couple of arguments I'd usually take a `List` instead — clearer,
no allocation surprise, no null-array trap, and a caller who already has a collection doesn't have to
convert it.'""",

"""8. THE CODE, LINE BY LINE

    // ── IT IS SUGAR, AND NOTHING ELSE ───────────────────────────────────
    void log(String prefix, String... parts) { ... }
    // compiles to:  void log(String prefix, String[] parts)   + an ACC_VARARGS flag
    // The flag is the ONLY difference. Reflection sees String[]; isVarArgs() sees
    // the flag.

    log("p", "a", "b");        // → log("p", new String[]{"a","b"})   compiler builds
    log("p");                  // → log("p", new String[0])           ALLOCATED
    log("p", existingArray);   // → log("p", existingArray)           PASSED AS-IS

    // ── THE NULL TRAP ───────────────────────────────────────────────────
    log("p", null);
    //        ^^^^ a NULL ARRAY, not an array containing null.
    //   parts.length → NullPointerException, inside a method that looks defensive.
    log("p", (String) null);   // ← an array of ONE null. The cast is the whole fix.

    // ── THE MOST FAMOUS VARARGS BUG IN JAVA ─────────────────────────────
    int[] nums = {1, 2, 3};
    List<int[]> wrong = Arrays.asList(nums);     // SIZE 1
    System.out.println(Arrays.asList(nums).size());     // 1  ← everyone expects 3
    System.out.println(Arrays.asList(1, 2, 3).size());  // 3
    //
    // asList is  <T> List<T> asList(T... a).  A type parameter must be a REFERENCE
    // type — erasure makes T an Object, and `int` is not one. So int[] cannot be
    // SPREAD into T elements. But int[] IS ITSELF AN OBJECT, so it matches as ONE
    // element. The compiler is content. Same root cause as List<int> not existing.
    List<Integer> right = Arrays.stream(nums).boxed().toList();   // ← the fix

    // ── VARARGS LOSES EVERY OVERLOAD CONTEST ────────────────────────────
    static void f(int a, int b) { print("fixed");   }
    static void f(int... xs)    { print("varargs"); }
    f(1, 2);                   // "fixed"   — phase 1 (widening) found a match

    static void g(Integer x) { print("boxed");   }
    static void g(int... xs) { print("varargs"); }
    g(1);                      // "boxed"   — phase 2 beats phase 3
    //
    // PHASE 1 widening only → PHASE 2 boxing allowed → PHASE 3 varargs allowed.
    // The first phase that finds ANY applicable method wins.
    // WHY THAT ORDER: autoboxing AND varargs both arrived in Java 5, and neither was
    // allowed to change the meaning of a program written before them.

    // ── THE AMBIGUITY THE COMPILER REFUSES TO GUESS ─────────────────────
    static void h(Object... xs)          { }
    static void h(String a, Object... xs){ }
    h("x");                    // ✗ COMPILE ERROR: reference to h is ambiguous
    // Neither is more specific: the first accepts everything at that arity, the
    // second is more specific in its first parameter. The compiler refuses.

    // ── THE ALLOCATION, AND WHAT THE JDK DOES ABOUT IT ──────────────────
    // EVERY varargs call allocates an array. Which is why List.of declares:
    //   of()  of(E)  of(E,E)  of(E,E,E) ... of(E×10)   ← ELEVEN fixed arities
    //   of(E... elements)                              ← only then varargs
    // Map.of and EnumSet.of do the same. Not style — ALLOCATION AVOIDANCE in code
    // that runs everywhere. (Escape analysis often removes it on a warm inlined
    // path; not on a cold one.)
    log.debug("state {}", v);  // ← SLF4J has 1- and 2-arg overloads for exactly this

    // ── GENERIC VARARGS: heap pollution ─────────────────────────────────
    @SafeVarargs
    static <T> List<T> listOf(T... items) { return List.of(items); }
    //                        ^^^^ T... erases to Object[], and Java has no real
    //   generic arrays — so the array can be aliased and written with the wrong type.
    //   That is what "possible heap pollution" means.
    // @SafeVarargs DOES NOT MAKE ANYTHING SAFE. It suppresses the warning, and you
    // are asserting the method only READS the array and never stores or exposes it.
    // Allowed on static, final, private (9+) methods and constructors — anything that
    // cannot be OVERRIDDEN, because an override could break the promise.

    // ── AND ONE REFLECTION QUIRK ────────────────────────────────────────
    method.invoke(target, theArray);              // SPREAD as several arguments
    method.invoke(target, new Object[]{theArray});// ← the array as ONE argument
    // Method.invoke is itself Object... , so it has the same spreading behaviour.""",

"""9. THE TRACE — three calls, three different methods chosen

THE OVERLOAD SET:

    f(int a, int b)      // fixed arity
    f(Integer a)         // one boxed
    f(int... xs)         // varargs

    call    phase 1 (widening only)   phase 2 (boxing)     phase 3 (varargs)   chosen
    ---------------------------------------------------------------------------------
    f(1,2)  f(int,int) APPLICABLE     not consulted        not consulted       f(int,int)
    f(1)    nothing applicable        f(Integer) APPLIC.   not consulted       f(Integer)
    f(1,2,3) nothing applicable       nothing applicable   f(int...) APPLIC.   f(int...)
    ---------------------------------------------------------------------------------
    NOTE ROW 2. A human reading `f(1)` would probably guess the varargs one — one argument, variable
    arity, seems natural. The compiler boxes instead, because phase 2 comes before phase 3. AND THAT IS
    NOT AN AESTHETIC CHOICE: if varargs could win at phase 2, adding an `f(int...)` overload to an
    existing library would silently change what pre-existing callers of `f(Integer)` invoke. The phase
    ordering is a compatibility guarantee.

NOW `Arrays.asList`, traced against its own signature:

    signature: <T> List<T> asList(T... a)

    call                          what T can be    what happens              size
    ---------------------------------------------------------------------------------
    asList("a","b","c")           String           spread into 3 elements     3
    asList(new Integer[]{1,2,3})  Integer          the array IS T[] already,
                                                   passed as-is, 3 elements   3
    asList(new int[]{1,2,3})      ??? — T must be  int[] cannot be T[],
                                  a REFERENCE      but int[] IS an Object,
                                  type, and int    so it matches as ONE
                                  is not           element                    1
    ---------------------------------------------------------------------------------
    ROWS 2 AND 3 DIFFER ONLY IN `Integer` VERSUS `int`, and the results differ by a factor of three. No
    warning is issued, because the third call is perfectly legal — it is a `List<int[]>` and the type
    system is satisfied. The failure is that the developer wanted a different type than the one they
    asked for.

    AND THE ROOT CAUSE IS THE SAME AS EVERYTHING ELSE PRIMITIVE-RELATED: erasure turns `T` into `Object`,
    a reference, and a primitive is not a reference. `List<int>` does not exist for the same reason.

THE NULL TRACE, showing why the cast matters:

    call                what the compiler emits              parts inside
    ---------------------------------------------------------------------------------
    log("p")            log("p", new String[0])              an EMPTY array. length 0.
    log("p", null)      log("p", (String[]) null)            NULL. parts.length → NPE
    log("p",(String)null) log("p", new String[]{null})       an array of ONE null
    ---------------------------------------------------------------------------------
    THREE CALLS THAT LOOK LIKE VARIATIONS OF EACH OTHER PRODUCE AN EMPTY ARRAY, A NULL, AND A ONE-NULL
    ARRAY. The middle row is the one that reaches production, because `null` is what a caller passes
    when they mean "nothing" — and the method's own `if (parts.length == 0)` guard is what throws.

AND THE ALLOCATION TRACE, which explains a JDK design decision:

    expression              allocations                     why the JDK cares
    ---------------------------------------------------------------------------------
    List.of("a")            0 — matches of(E), a fixed       called everywhere, in
                            arity overload                   every JDK code path
    List.of(a,b,c,…,k)      1 — 11 arguments falls through   rare enough to accept
                            to of(E... )
    a hypothetical          1 PER CALL, forever              which is why the eleven
    varargs-only List.of                                     overloads exist
    ---------------------------------------------------------------------------------
    ELEVEN NEARLY-IDENTICAL METHODS IN THE PUBLIC API OF `List` IS NOT AN ACCIDENT OR A STYLE CHOICE. It
    is what avoiding one array allocation looks like when the method is called billions of times across
    an ecosystem.

WHAT PRODUCED WHAT:
    "IT IS JUST AN ARRAY"     produced the null trace and the spreading behaviour.
    ERASURE (T = Object)      produced the `Arrays.asList(int[])` result, and heap pollution.
    PHASE ORDERING            produced row 2 of the first table — and it exists to protect programs
                              written before Java 5.
    ONE ALLOCATION PER CALL   produced eleven overloads of `List.of`.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `T...` IS `T[]`. Identical at runtime; the only difference is an `ACC_VARARGS` flag on the method.
    Every varargs call allocates an array — including the zero-argument case — unless escape analysis
    removes it on an inlined path.
    Overload resolution: phase 1 widening, phase 2 boxing, phase 3 varargs. First phase to find any
    applicable method wins.
    The varargs parameter must be LAST, and there can be only one.
    Generic varargs erase to `Object[]`, hence heap pollution and `@SafeVarargs`.
    `@SafeVarargs` applies only to methods that cannot be overridden: `static`, `final`, `private`
    (Java 9+), and constructors.

THE #1 MISTAKE: `f(null)`. It passes a null ARRAY, and the method's own length check throws.

THE #2 MISTAKE: `Arrays.asList(primitiveArray)`. A size-1 list, because a type parameter cannot be a
primitive. Use `Arrays.stream(...).boxed()`.

THE #3 MISTAKE: expecting an array argument to be wrapped. It is spread, because varargs IS the array
parameter.

THE #4 MISTAKE: expecting varargs to win an overload contest. It is phase three, after widening and
boxing.

THE #5 MISTAKE: adding a varargs overload beside close fixed-arity ones. Ambiguity errors that read like
puzzles, and readers who cannot predict which runs.

THE #6 MISTAKE: reading `@SafeVarargs` as a safety mechanism. It suppresses a warning; you are making
the promise.

THE #7 MISTAKE: varargs in a tight loop. An allocation per call, plus boxing if the parameter is a
wrapper.

THE #8 MISTAKE: `log.debug("x " + v, a, b)` — the concatenation AND the array both happen before the
call, regardless of the level.

THE #9 MISTAKE: `String.format("%s", someArray)`. `format` is varargs, so the array is spread into the
format arguments.

THE #10 MISTAKE: using varargs where a `List` parameter belongs. Clearer, allocation-free, null-safe,
and callers with a collection do not have to convert.

THE #11 MISTAKE: forgetting `Method.invoke` is itself varargs. A single `Object[]` parameter must be
wrapped.

ONE-SENTENCE TAKEAWAY: varargs is pure call-site sugar — `String...` IS `String[]`, with the compiler
building the array for the caller — which is why `f(null)` hands the method a NULL array rather than an
empty one, why passing an existing array SPREADS it rather than wrapping it, and why
`Arrays.asList(intArray)` returns a size-1 `List<int[]>` (a type parameter erases to `Object`, and a
primitive is not a reference, exactly as `List<int>` does not exist); overload resolution treats varargs
as a LAST resort in phase three after widening and boxing, not as a preference but as a compatibility
obligation to programs written before Java 5 — and since every call allocates an array, `List.of`
declares eleven fixed-arity overloads before falling back to it.""",
]


DEEP["JDK vs JRE vs JVM — and which one do you install?"] = [
"""1. THE GOAL IN PLAIN ENGLISH — three nested things, and only one you install

    JVM   the engine that executes bytecode. It is BOTH a written SPECIFICATION and a set of
          implementations of it — HotSpot, OpenJ9, GraalVM, Zing.
    JRE   the JVM PLUS the standard library — `java.lang`, `java.util`, `java.io` and the rest. Enough
          to RUN a program and nothing more.
    JDK   the JRE PLUS the tools that PRODUCE and INSPECT programs — `javac`, `jar`, `javadoc`,
          `jshell`, `jlink`, plus the diagnostic set: `jcmd`, `jstack`, `jmap`, `jfr`.

    THEY NEST: JDK ⊃ JRE ⊃ JVM. Every JDK contains a JRE; every JRE contains a JVM.

    AND THE ANSWER TO "WHICH DO I INSTALL" IS THE JDK, ALWAYS — including in production. Since Java 11
    Oracle stopped shipping a standalone JRE at all. If you want a smaller runtime for a container you
    build one with `jlink`, containing only the modules you actually use, which produces something
    smaller than the old JRE ever was.

    THE PRACTICAL REASON TO INSTALL A JDK IN PRODUCTION IS NOT COMPILATION. IT IS THE TOOLS. When a
    service is stuck at 3am, `jstack` gives you a thread dump, `jcmd GC.heap_dump` gives you a heap
    dump, and `jfr` gives you a flight recording. A JRE-only container has none of them, and you cannot
    install them into a running incident.

THE SECOND THING WORTH KNOWING IS THAT "WHICH JDK" IS A REAL QUESTION WITH A BORING ANSWER. Temurin,
Corretto, Zulu, Liberica, Microsoft, Oracle — ALL OF THEM ARE BUILT FROM THE SAME OpenJDK SOURCE. They
differ in who builds and tests them, how long each version is supported, and what extras are bundled.
They do not differ in what your code does.

THE EVERYDAY VERSION: the JVM is the engine, the JRE is the finished car, and the JDK is the car plus the
workshop — the tools to build one and, more importantly, the diagnostics to find out why one stopped.
You ship the car, but you keep the workshop in the garage, because "we removed the tools to save space"
is a sentence you regret exactly once.

TERMS AS THEY APPEAR:
- BYTECODE: what `javac` produces and the JVM executes.
- LTS: a long-term support release. 8, 11, 17, 21, 25 — supported for years rather than six months.
- TCK: the Technology Compatibility Kit, the test suite a build must pass to call itself Java SE.""",

"""2. THE INTUITION — the specification is the product

THE MOST IMPORTANT IDEA HERE IS THAT JAVA IS TWO SPECIFICATIONS, NOT ONE:

    THE JAVA LANGUAGE SPECIFICATION describes the source language — syntax, types, overload resolution,
    what `final` means.
    THE JAVA VIRTUAL MACHINE SPECIFICATION describes the class file format and the bytecode instruction
    set. IT DOES NOT MENTION THE JAVA LANGUAGE AT ALL.

    THAT SEPARATION IS WHY KOTLIN, SCALA, CLOJURE AND GROOVY EXIST. They are not "Java with different
    syntax" — they are independent languages whose compilers emit class files. The JVM has no idea which
    language produced what it is running, and cannot tell.

    IT IS ALSO WHY THE JVM IS ARGUABLY THE MORE VALUABLE OF THE TWO ARTIFACTS. Thirty years of work on
    garbage collection, JIT compilation and observability is available to any language willing to target
    the format.

AND BECAUSE THE JVM IS A SPECIFICATION, THERE ARE SEVERAL IMPLEMENTATIONS, each with a real reason to
exist:

    HOTSPOT      the OpenJDK default. Tiered JIT (C1/C2), and the collectors everyone knows.
    OPENJ9       from IBM. Lower memory footprint and faster startup, with a shared class cache — a
                 genuinely different set of trade-offs, attractive in containers.
    GRAALVM      HotSpot with a JIT written in Java, plus AHEAD-OF-TIME native image compilation.
    ZING / AZUL   a pauseless collector for very large heaps, and an AOT-assisted JIT.

    ALL OF THEM RUN THE SAME CLASS FILES. That is the point of specifying the format rather than the
    implementation.

NOW THE DISTRIBUTION QUESTION, which is where teams actually spend time and which has a short answer:

    ALMOST EVERY DISTRIBUTION IS BUILT FROM THE SAME OpenJDK SOURCE. Temurin (Eclipse Adoptium),
    Corretto (Amazon), Zulu (Azul), Liberica (BellSoft), Microsoft Build of OpenJDK, Red Hat's build,
    SapMachine, and Oracle's own JDK. The differences are:
        WHO BUILDS AND CERTIFIES IT — all the serious ones pass the TCK, so they are all "Java SE
        compatible" in the formal sense.
        HOW LONG IT IS SUPPORTED — Corretto and Zulu offer long horizons; Adoptium follows the LTS
        cadence.
        WHAT IS BUNDLED — Liberica ships a variant with JavaFX; Corretto carries some Amazon patches;
        Zulu offers CRaC builds.
        THE LICENCE — the one genuine trap. Oracle's own JDK has changed terms three times since 2019.
        The OpenJDK builds are GPL+CE and have not.
    THE PRACTICAL ANSWER FOR MOST TEAMS IS TEMURIN OR CORRETTO, PINNED TO AN LTS.

VERSIONS: 8, 11, 17, 21 and 25 are LTS; everything between is a six-month release supported for six
months. Java 8 is still enormously deployed and is where most "why does this not compile" surprises come
from. AND THE NUMBERING HISTORY IS WORTH KNOWING BECAUSE IT SHOWS UP IN VERSION STRINGS: 1.0 to 1.4, then
5 (still `1.5` internally), through 8 (`1.8`), and from 9 onward the marketing number and the internal
number finally agree.""",

"""3. THE MECHANISM — what is actually in each, and how the pieces are laid out

INSIDE A MODERN JDK (Java 9+, after the module system reorganised everything):

    bin/     java        the launcher — creates the JVM and calls `main`
             javac       the compiler
             jar         packaging
             javadoc     documentation
             jshell      the REPL (Java 9+)
             jlink       build a custom runtime image containing only what you use
             jpackage    build a native installer (Java 14+)
             jdeps       analyse dependencies, and find internal-API usage before an upgrade
             THE DIAGNOSTIC SET — the reason a JDK belongs in production:
             jcmd        the swiss army knife: thread dumps, heap dumps, VM flags, GC info, JFR control
             jstack      thread dumps (and it DETECTS DEADLOCKS automatically)
             jmap        heap dumps and heap summaries
             jstat       GC and class-loading statistics over time
             jfr         Flight Recorder — low-overhead production profiling
             jinfo       inspect and change some VM flags on a live process
    lib/     modules     a single file containing the linked standard library. Replaced `rt.jar`.
             server/libjvm.so   THE JVM ITSELF — the native library `java` loads
    conf/    logging.properties, security policy, networking defaults

    NOTE `lib/modules`. Before Java 9 the library was `rt.jar`, a plain zip you could open. Since 9 it
    is a linked image in the jimage format, optimised for load speed and not designed to be poked at —
    which is one reason old tools that unpacked `rt.jar` broke on 9.

WHAT `jlink` DOES, since it replaced the JRE:

    jlink --add-modules java.base,java.logging --output myruntime

    It produces a self-contained runtime with only the named modules and their dependencies. A `java.base`-
    only image is around 40 MB versus roughly 200 MB for a full JDK — WHICH IS THE ACTUAL ANSWER TO
    "I want a small runtime for my container", and it beats the old JRE because it is tailored to your
    program rather than to everyone's.

    THE CATCH: `jlink` needs your dependencies to be modular, or at least to be automatic modules, and
    reflection-heavy frameworks can need extra modules added by hand. `jdeps` tells you which.

HOW THE VERSION PIECES RELATE AT RUNTIME:
    `java -version` reports the RUNTIME. `javac -version` reports the COMPILER. THEY CAN DIFFER, and a
    mismatch is one of the most common setup problems — compile with 21, run on 17, get
    `UnsupportedClassVersionError`. `--release N` is the fix: it targets both the bytecode version AND
    the API surface of N.
    `JAVA_HOME` is what build tools read; `PATH` is what your shell resolves. THEY CAN POINT AT
    DIFFERENT JDKs, which produces the memorable experience of Maven and your terminal disagreeing.
    SDKMAN, `jenv` or your distribution's alternatives system manage several installed JDKs; a project
    should pin its version in the build file (`maven.compiler.release`, Gradle's toolchain block) rather
    than relying on whatever is installed.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — A JRE-ONLY CONTAINER IN PRODUCTION. No `jstack`, no `jcmd`, no `jfr`. During an incident you
cannot take a thread dump or a heap dump, and you cannot install them into a running pod.

CASE 2 — `java -version` AND `javac -version` DISAGREEING. Compile with a newer JDK, run on an older
JVM, get `UnsupportedClassVersionError` — which helpfully reports both class-file versions.

CASE 3 — `JAVA_HOME` AND `PATH` POINTING AT DIFFERENT JDKs. Maven or Gradle uses one, your terminal uses
another, and the two disagree about a compile error.

CASE 4 — `-source`/`-target` WITHOUT `--release`. You get older bytecode compiled against the NEWER
JDK's API, so it compiles cleanly and then throws `NoSuchMethodError` on the older runtime.

CASE 5 — ASSUMING ORACLE JDK AND OpenJDK BEHAVE DIFFERENTLY. Since Java 11 they are built from
essentially the same source. The difference is the LICENCE and the support contract, not the behaviour.

CASE 6 — THE ORACLE LICENCE. It changed in 2019 (paid for production), again with the NFTC in 17 (free
again), and again afterwards. Teams have been billed for this. An OpenJDK build under GPL+CE avoids the
question entirely.

CASE 7 — ASSUMING A NON-LTS RELEASE IS SUPPORTED. Java 18, 19, 20, 22 and so on get six months of
updates. Fine for experimenting, wrong for a service you will still be running next year.

CASE 8 — UPGRADING FROM JAVA 8 AND HITTING REMOVED INTERNAL APIS. `sun.misc.Unsafe`, `--add-opens` for
reflection into JDK internals, the removal of JAXB and CORBA from the JDK in 11. `jdeps --jdk-internals`
finds these before you upgrade rather than after.

CASE 9 — 32-BIT VERSUS 64-BIT. A 32-bit JVM caps the heap at roughly 4 GB, and 32-bit builds have been
dropped from most distributions.

CASE 10 — A JDK IN A CONTAINER THAT DOES NOT SEE THE CGROUP LIMIT. Very old JVMs size the heap from the
HOST's memory and are OOM-killed with no Java-level error. `-XX:MaxRAMPercentage` on a modern one.

CASE 11 — CONFUSING JAVA SE WITH JAKARTA EE. Servlets, JPA and CDI are not in the JDK and never were.
Jakarta EE is a separate specification implemented by application servers.

CASE 12 — `jlink` FAILING ON A NON-MODULAR DEPENDENCY. Automatic modules help; reflection-heavy
frameworks often need modules added explicitly.

CASE 13 — RELYING ON THE DEFAULT LOCALE, CHARSET OR TIMEZONE. These come from the environment, not the
JDK. Java 18 finally made UTF-8 the default charset; before that the same program produced different
bytes on different machines.""",

"""5. THE ALTERNATIVES — choosing a distribution and a runtime shape

FOR MOST TEAMS: ECLIPSE TEMURIN OR AMAZON CORRETTO, pinned to an LTS. Both free, both TCK-certified,
both with predictable update cadence, and neither carries a licence question.

    AZUL ZULU if you want long support horizons or CRaC (checkpoint/restore for near-instant startup).
    LIBERICA if you need bundled JavaFX.
    MICROSOFT BUILD if you are on Azure and want their support relationship.
    RED HAT'S BUILD if you are on RHEL and want it in the platform's support contract.
    ORACLE JDK only if you have a commercial reason — and read the current licence, because it has
    changed three times.
    ECLIPSE OPENJ9 (via IBM Semeru) when memory footprint and startup matter more than peak throughput.
    A genuinely different trade, not a rebadge.

FOR THE RUNTIME YOU SHIP:
    A FULL JDK IMAGE — simplest, ~200-400 MB, and every diagnostic tool present. FINE FOR MOST SERVICES,
    and the extra megabytes are cached layers.
    `jlink` CUSTOM IMAGE — ~40-100 MB with only the modules you use. Worth it when image size genuinely
    matters. Include `jdk.jcmd` and `jdk.management` explicitly, or you have recreated the JRE problem.
    ALPINE + A MUSL BUILD — smallest, and be aware musl versus glibc has produced real performance
    differences.
    GRAALVM NATIVE IMAGE — no JVM at all. Millisecond startup, low memory, lower peak, closed world.
    Right for CLI tools and short-lived functions; wrong for a long-running server where the JIT wins.

FOR MANAGING VERSIONS LOCALLY: SDKMAN or `jenv`, and PIN THE VERSION IN THE BUILD rather than relying on
what is installed:
    Maven `<maven.compiler.release>21</maven.compiler.release>`
    Gradle `java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }`
    Gradle toolchains will even DOWNLOAD the right JDK, which removes the whole class of "works on my
    machine" caused by version drift.

FOR UPGRADING: `jdeps --jdk-internals` to find dependencies on removed internals, and the JDK's own
release notes for removals. THE JAVA 8 → 11 STEP IS THE HARD ONE, because of the module system and the
removal of JAXB, CORBA and the extension mechanism. 11 → 17 → 21 are comparatively easy.

WHAT TO SAY: "Install a JDK, including in production — not for `javac` but for `jstack`, `jcmd` and
`jfr`, which you cannot add during an incident. Temurin or Corretto pinned to an LTS; they are all built
from the same OpenJDK source, so the differences are support and licence, not behaviour. And `jlink` if
the image size genuinely matters, remembering to include the diagnostic modules."

""",

"""6. HOW TO SET THIS UP — numbered steps

STEP 1 — INSTALL A JDK, NOT A JRE. There is no standalone JRE from Oracle since Java 11, and you want
the tools anyway.

STEP 2 — PICK AN LTS: 17 or 21 for new work; 25 as it matures. Non-LTS releases get six months of
updates.

STEP 3 — PICK A DISTRIBUTION AND STOP THINKING ABOUT IT. Temurin or Corretto. They are the same source
as the others.

STEP 4 — PIN THE VERSION IN THE BUILD FILE, not in a README. Gradle toolchains or Maven's
`maven.compiler.release`.

STEP 5 — COMPILE WITH `--release N`, NEVER `-source`/`-target`. Only `--release` restricts the API
surface as well as the bytecode version.

STEP 6 — CHECK `java -version` AND `javac -version` MATCH, and that `JAVA_HOME` agrees with `PATH`.

STEP 7 — SHIP A JDK IMAGE IN PRODUCTION, or a `jlink` image that explicitly includes `jdk.jcmd` and
`jdk.management`. The diagnostics are the point.

STEP 8 — SET `-XX:MaxRAMPercentage` IN A CONTAINER rather than a hard `-Xmx`, and confirm the JVM sees
the cgroup limit.

STEP 9 — SET THE CHARSET, LOCALE AND TIMEZONE EXPLICITLY if behaviour depends on them. They come from
the environment, and UTF-8 only became the default in Java 18.

STEP 10 — BEFORE AN UPGRADE, RUN `jdeps --jdk-internals` over your artifacts. It finds the removed
internal APIs before production does.

STEP 11 — USE SDKMAN OR `jenv` LOCALLY, so several JDKs coexist and switching is one command.

STEP 12 — IF STARTUP GENUINELY DOMINATES — a CLI tool, a short-lived function — EVALUATE A NATIVE IMAGE
OR OPENJ9. For a long-running server, stay on HotSpot and let the JIT do its work.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'They nest. The JVM is the engine that executes bytecode — and it's both a written SPECIFICATION and
several implementations of it: HotSpot, OpenJ9, GraalVM, Zing. The JRE is the JVM plus the standard
library, which is enough to run a program. The JDK is the JRE plus the tools — javac, jar, jshell,
jlink, and the diagnostics: jcmd, jstack, jmap, jfr.

The answer to "which do I install" is always the JDK, including in production. Oracle stopped shipping a
standalone JRE at Java 11, and if you want a small runtime you build one with jlink containing only the
modules you use — which is smaller than the old JRE ever was.

But the real reason to have a JDK in production isn't compilation, it's the TOOLS. When a service is
stuck at 3am, jstack gives you a thread dump and detects deadlocks automatically, jcmd gives you a heap
dump, jfr gives you a flight recording. A JRE-only container has none of those and you cannot install
them into a running incident.

The idea I find most worth stating is that Java is TWO specifications. The language spec describes the
source language. The JVM spec describes the class file format and the bytecode instruction set — and it
doesn't mention the Java language at all. That separation is why Kotlin, Scala, Clojure and Groovy
exist: they're independent languages whose compilers emit class files, and the JVM can't tell which
language produced what it's running. It also means the JVM is arguably the more valuable artifact —
thirty years of GC, JIT and observability work available to anything willing to target the format.

On distributions: Temurin, Corretto, Zulu, Liberica, Microsoft, Oracle — they're all built from the same
OpenJDK source. What differs is who builds and certifies them, how long each version is supported,
what's bundled, and the licence. Oracle's own terms have changed three times since 2019 and teams have
been billed for it; the OpenJDK builds are GPL with classpath exception and haven't changed. So the
practical answer is Temurin or Corretto, pinned to an LTS — 8, 11, 17, 21, 25 — and the six-month
releases in between get six months of updates, which is fine for experimenting and wrong for a service
you'll still be running next year.

The setup mistake I'd flag is `-source`/`-target` instead of `--release`. Only --release restricts the
API SURFACE as well as the bytecode version, so with the older flags you get old bytecode compiled
against the new JDK's API — it compiles cleanly and then throws NoSuchMethodError on the older runtime.
And check that JAVA_HOME agrees with PATH, because Maven reads one and your shell resolves the other,
and that's where "the IDE compiles it and the terminal doesn't" comes from.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE NESTING ─────────────────────────────────────────────────────
    //  ┌─ JDK ────────────────────────────────────────────────┐
    //  │  javac  jar  javadoc  jshell  jlink  jpackage  jdeps │  ← produce & inspect
    //  │  jcmd  jstack  jmap  jstat  jfr  jinfo               │  ← THE 3AM TOOLS
    //  │  ┌─ JRE ─────────────────────────────────────────┐   │
    //  │  │  lib/modules   (the standard library)         │   │  ← enough to RUN
    //  │  │  ┌─ JVM ───────────────────────────────────┐  │   │
    //  │  │  │  lib/server/libjvm.so                   │  │   │  ← the engine
    //  │  │  └─────────────────────────────────────────┘  │   │
    //  │  └───────────────────────────────────────────────┘   │
    //  └──────────────────────────────────────────────────────┘

    // ── THE TOOLS THAT ARE THE REAL REASON ──────────────────────────────
    jstack <pid>                     # thread dump — AND it detects deadlocks
    jcmd <pid> Thread.print          # the same, via the modern entry point
    jcmd <pid> GC.heap_dump /d.hprof # heap dump, for Eclipse MAT
    jcmd <pid> VM.flags              # what this JVM is ACTUALLY running with
    jcmd <pid> VM.native_memory summary   # RSS broken down by pool
    jfr start --name=r duration=60s filename=r.jfr   # production profiling
    # NONE OF THESE EXIST IN A JRE-ONLY IMAGE, and you cannot add them mid-incident.

    // ── TWO SPECIFICATIONS, NOT ONE ─────────────────────────────────────
    // The JAVA LANGUAGE SPEC describes source: syntax, types, overload resolution.
    // The JVM SPEC describes the class file format and bytecode.
    //   IT DOES NOT MENTION THE JAVA LANGUAGE AT ALL.
    // Which is why:
    kotlinc Hello.kt   → Hello.class    # the JVM cannot tell what produced it
    scalac  Hello.scala → Hello.class
    javac   Hello.java  → Hello.class

    // ── THE SETUP MISTAKE ───────────────────────────────────────────────
    javac -source 8 -target 8 App.java     # ✗ old BYTECODE, NEW JDK's API surface
    //                                        → compiles fine, then NoSuchMethodError
    //                                          on the Java 8 runtime
    javac --release 8 App.java             # ✓ restricts BOTH bytecode and API
    java -version                          # the RUNTIME
    javac -version                         # the COMPILER — THESE CAN DIFFER
    echo $JAVA_HOME                        # what Maven/Gradle read
    which java                             # what your shell resolves — ALSO CAN DIFFER

    // ── PIN IT IN THE BUILD, NOT IN A README ────────────────────────────
    // Maven:
    //   <maven.compiler.release>21</maven.compiler.release>
    // Gradle:
    //   java { toolchain { languageVersion = JavaLanguageVersion.of(21) } }
    //   ^ Gradle toolchains will DOWNLOAD the right JDK, removing the whole class
    //     of "works on my machine" caused by version drift.

    // ── jlink: what replaced the JRE ────────────────────────────────────
    jlink --add-modules java.base,java.logging,jdk.jcmd,jdk.management           --strip-debug --no-man-pages --compress=2 --output myruntime
    //                  ^^^^^^^^^^^^^^^^^^^^^^^^ INCLUDE THE DIAGNOSTICS, or you have
    //                  recreated the JRE problem with extra steps.
    // ~40-100 MB instead of ~200-400 MB, tailored to YOUR program rather than
    // to everyone's — which is why it beats the old JRE.

    // ── BEFORE AN UPGRADE ───────────────────────────────────────────────
    jdeps --jdk-internals app.jar     # finds sun.misc.Unsafe and friends BEFORE
    //                                  production does
    // Java 8 → 11 is the hard step: the module system, and JAXB/CORBA removed from
    // the JDK. 11 → 17 → 21 are comparatively easy.

    // ── AND ONE ENVIRONMENT TRAP ────────────────────────────────────────
    // The default CHARSET, LOCALE and TIMEZONE come from the environment, not the
    // JDK. UTF-8 only became the default charset in Java 18 — before that the same
    // program produced different bytes on different machines.
    java -Dfile.encoding=UTF-8 -Duser.timezone=UTC -Duser.language=en ...""",

"""9. THE TRACE — four decisions, and what each one costs later

DECISION 1 — JRE-ONLY IMAGE VERSUS JDK IMAGE

    situation                          JRE-only image           JDK image
    ---------------------------------------------------------------------------------
    normal operation                   works                     works
    image size                         ~120 MB                   ~350 MB (cached layers)
    3am: requests hanging               NO jstack. NO jcmd.       jstack → "Found one
                                        You can restart and hope. Java-level deadlock",
                                                                  with the exact lines.
    3am: memory climbing                NO heap dump possible.    jcmd GC.heap_dump →
                                                                  dominator tree → the
                                                                  retaining path
    ---------------------------------------------------------------------------------
    THE SAVING IS A FEW HUNDRED CACHED MEGABYTES. THE COST IS THAT AN INCIDENT BECOMES UNDIAGNOSABLE, and
    you cannot change the decision while it is happening. This is the whole argument, and it is why
    "install the JDK" is not a compilation question.

DECISION 2 — `-source 8 -target 8` VERSUS `--release 8`

    step                                     -source/-target        --release
    ---------------------------------------------------------------------------------
    you call List.of(...) (a Java 9 method)  COMPILES — the API      COMPILE ERROR:
                                             surface is the NEW      "cannot find symbol"
                                             JDK's
    bytecode version emitted                 52 (Java 8)             52 (Java 8)
    running on a Java 8 JVM                  NoSuchMethodError at    n/a — you fixed it
                                             the first call          at compile time
    ---------------------------------------------------------------------------------
    THE OLD FLAGS RESTRICT THE FORMAT AND NOT THE VOCABULARY. Which produces a build that succeeds and a
    runtime that fails, on a machine you do not control, on a code path that may be rare.

DECISION 3 — WHICH DISTRIBUTION

    axis                          does it differ?
    ---------------------------------------------------------------------------------
    what your code does           NO. Same OpenJDK source, same TCK certification.
    performance                   NO, between HotSpot-based builds. YES for OpenJ9 and
                                  GraalVM native, which are genuinely different engines.
    support duration              YES. Corretto and Zulu offer long horizons.
    bundled extras                YES. Liberica has a JavaFX variant; Corretto carries
                                  some Amazon patches.
    LICENCE                       YES, AND THIS IS THE ONLY ONE THAT HAS COST PEOPLE
                                  MONEY. Oracle's terms changed in 2019, again with the
                                  NFTC in 17, and again after. GPL+CE builds did not.
    ---------------------------------------------------------------------------------
    FOUR OF THE FIVE ROWS ARE "NO" OR "MINOR". This is a decision that deserves ten minutes, once, and
    then never again.

DECISION 4 — LTS VERSUS LATEST

    release      updates for              suitable for
    ---------------------------------------------------------------------------------
    17, 21, 25   years                    anything you will still be running next year
    18-20, 22-24 SIX MONTHS               experimenting, previewing language features
    8            still widely deployed    and still the source of most "why does this
                                          not compile" surprises
    ---------------------------------------------------------------------------------
    THE FAILURE MODE OF PICKING A NON-LTS IS NOT IMMEDIATE. It is discovering, eight months later, that
    your runtime has no security updates and the upgrade path is now two versions long.

AND THE VERSION-MISMATCH TRACE, which is the single most common setup problem:

    what you see                              what is actually true
    ---------------------------------------------------------------------------------
    "It compiles in IntelliJ, fails in Maven"  IntelliJ uses its configured SDK; Maven
                                               uses JAVA_HOME. They differ.
    "UnsupportedClassVersionError: class file  compiled by 21, run on 17. The message
     version 65.0 ... recognizes up to 61.0"   names BOTH halves — 65 is 21, 61 is 17.
    "NoSuchMethodError on a method in the jar" two library versions on the classpath,
                                               OR -source/-target without --release
    ---------------------------------------------------------------------------------
    ALL THREE ARE THE SAME ROOT CAUSE IN DIFFERENT CLOTHES: more than one Java version is in play and
    nothing pinned which one. `java -version`, `javac -version`, `echo $JAVA_HOME`, `which java` — four
    commands that resolve it in under a minute.

WHAT PRODUCED WHAT:
    THE TOOLS LIVING IN THE JDK       produced decision 1's asymmetry.
    --release RESTRICTING THE API     produced decision 2 — the flag that fails at build time instead
                                      of runtime.
    A SHARED OpenJDK SOURCE           produced decision 3's four "no"s.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    JDK ⊃ JRE ⊃ JVM. No standalone JRE from Oracle since Java 11; `jlink` replaced it.
    A full JDK image is ~200–400 MB; a `jlink` image is ~40–100 MB; a native image has no JVM at all.
    LTS releases: 8, 11, 17, 21, 25. Everything else gets six months.
    Class file versions: 52 = Java 8, 61 = 17, 65 = 21.
    Two specifications: the language spec and the JVM spec, and the second does not mention Java.
    Essentially every distribution is built from the same OpenJDK source and TCK-certified.

THE #1 MISTAKE: a JRE-only production image. No `jstack`, no `jcmd`, no `jfr`, and no way to add them
during an incident.

THE #2 MISTAKE: `-source`/`-target` instead of `--release`. Old bytecode against the new API surface —
compiles clean, fails at runtime.

THE #3 MISTAKE: `JAVA_HOME` and `PATH` disagreeing. Maven and your shell then disagree about your code.

THE #4 MISTAKE: assuming Oracle JDK behaves differently from an OpenJDK build. Same source; the
difference is the licence and the support contract.

THE #5 MISTAKE: ignoring the Oracle licence. It has changed three times since 2019 and has generated real
invoices.

THE #6 MISTAKE: deploying a non-LTS release. Six months of updates, discovered eight months later.

THE #7 MISTAKE: not pinning the JDK version in the build. Version drift across machines is the classic
"works on mine".

THE #8 MISTAKE: expecting servlets or JPA in the JDK. Jakarta EE is a separate specification and always
was.

THE #9 MISTAKE: `jlink` without `jdk.jcmd` and `jdk.management`. You have rebuilt the JRE problem.

THE #10 MISTAKE: upgrading from Java 8 without running `jdeps --jdk-internals` first. Removed internals
surface at runtime, on a rare code path.

THE #11 MISTAKE: relying on the default charset, locale or timezone. They come from the environment, and
UTF-8 only became the default in Java 18.

ONE-SENTENCE TAKEAWAY: JDK ⊃ JRE ⊃ JVM, and you install the JDK everywhere including production — not for
`javac` but for `jstack`, `jcmd` and `jfr`, which are the difference between diagnosing an incident and
restarting and hoping, and which cannot be added once one is under way; the JVM is a SPECIFICATION
separate from the Java language specification, which is why Kotlin and Scala exist and why the class file
rather than the source is the real interface; and since essentially every distribution — Temurin,
Corretto, Zulu, Liberica, Oracle — is built from the same TCK-certified OpenJDK source, the only choices
that actually matter are picking an LTS, pinning it in the build file, and compiling with `--release`
rather than `-source`/`-target`, which restricts the API surface as well as the bytecode version and so
fails at build time instead of on someone else's runtime.""",
]


DEEP["Integer caching — why 127 == 127 but 128 != 128"] = [
"""1. THE GOAL IN PLAIN ENGLISH — the same comparison, two answers, one byte apart

    Integer a = 127, b = 127;   System.out.println(a == b);   // true
    Integer c = 128, d = 128;   System.out.println(c == d);   // FALSE

    THE ONLY DIFFERENCE IS THE NUMBER. Nothing about the code changed, and the comparison went from
    "correct" to "wrong".

The reason is that `==` on objects asks "ARE THESE THE SAME OBJECT?", never "do they hold the same
value". And when you write `Integer a = 127`, the compiler inserts `Integer.valueOf(127)` — which
returns a CACHED, SHARED instance for values from −128 to 127, and a brand-new object outside that
range.

    SO AT 127 BOTH VARIABLES POINT AT LITERALLY THE SAME OBJECT AND `==` IS TRUE. At 128 they point at
    two different objects holding the same number, and `==` is false. THE COMPARISON WAS NEVER ABOUT
    VALUE; IT ONLY LOOKED CORRECT BECAUSE OF THE CACHE.

WHY THIS IS THE WORST POSSIBLE FAILURE PATTERN, and why it deserves a whole entry:

    IT WORKS FOR EXACTLY THE VALUES A DEVELOPER TESTS WITH. Loop counters, small ids, list sizes, the
    numbers 1 and 2 and 3 in a unit test. All under 128.
    IT FAILS FOR THE VALUES PRODUCTION USES. Real database ids, real counts, real amounts.
    AND IT IS REQUIRED BY THE LANGUAGE SPECIFICATION for −128..127, so it is PORTABLE behaviour, not a
    quirk of one JVM. No runtime will save you and no other JVM will behave differently.

THE EVERYDAY VERSION: a library that keeps one physical copy of its hundred most popular books and
prints a fresh copy of anything else on request. Ask two people to fetch "book 42" and they come back
with the same physical object — so "is it the same book?" and "does it say the same thing?" happen to
agree. Ask for "book 900" and they return two different printed copies, and the first question suddenly
gives a different answer from the second. Nothing about the question changed.

TERMS AS THEY APPEAR:
- AUTOBOXING: the compiler inserting `Integer.valueOf(x)` when a primitive is used where an object is
  required.
- THE INTEGER CACHE: a preallocated array of `Integer` objects for −128..127, held in a static nested
  class.
- IDENTITY: whether two references point at the same object. What `==` tests.""",

"""2. THE INTUITION — why a cache exists at all, and why it stops at 127

THE CACHE IS NOT AN OPTIMISATION SOMEONE BOLTED ON. It is a response to a measured fact: SMALL INTEGERS
ARE OVERWHELMINGLY THE COMMON CASE. Loop counters, array sizes, small identifiers, HTTP status codes,
enum ordinals, month numbers. In a program that boxes millions of integers, the overwhelming majority
are tiny.

    SO `Integer.valueOf` PREALLOCATES 256 OBJECTS — one for each value from −128 to 127 — AT CLASS
    INITIALISATION, and hands out the shared instance whenever the value is in range. That turns
    millions of allocations into zero, for the values that actually occur.

    THE RANGE IS −128..127 BECAUSE THAT IS EXACTLY THE RANGE OF A SIGNED BYTE. It is not arbitrary; it
    is the natural "small number" boundary, and it is the same range used for `Byte`, `Short` and
    `Long`.

AND THE LANGUAGE SPECIFICATION REQUIRES IT, which is the part that makes this worth knowing rather than
just avoiding:

    The JLS mandates that boxing a value in −128..127 yields the same object for equal values. It also
    explicitly PERMITS an implementation to cache more. So −128..127 is guaranteed, and above it is
    unspecified — which means `128 == 128` being false is not promised either, it just happens to be
    true on every real JVM.

    THE REASON THE SPEC MANDATES IT is memory and performance for the common case; the reason it does
    NOT mandate more is that caching every integer would need unbounded memory.

WHICH WRAPPERS CACHE, AND WHICH DO NOT — the pattern is informative:

    Integer, Short, Byte, Long     −128 to 127
    Character                      0 to 127
    Boolean                        both values, always — there are only two
    Float, Double                  NEVER

    `Float` AND `Double` ARE NOT CACHED BECAUSE THERE IS NO SENSIBLE FINITE SET TO CACHE. There is no
    "small double". So `Double a = 1.0, b = 1.0; a == b` is ALWAYS false — which at least fails
    consistently, and is arguably kinder than the Integer behaviour.

NOW THE DETAIL THAT MOST PEOPLE MISS, AND IT IS GENUINELY USEFUL:

    Integer big = 1000;
    int prim = 1000;
    System.out.println(big == prim);      // TRUE

    COMPARING A WRAPPER WITH A PRIMITIVE UNBOXES THE WRAPPER AND COMPARES VALUES. Binary numeric
    promotion applies, so this is `big.intValue() == prim` — a genuine value comparison, correct for
    every number.

    SO `Integer == Integer` IS IDENTITY AND `Integer == int` IS VALUE. Two comparisons that look
    identical in source, differing only in whether one side happens to be declared as a primitive. That
    is also the safest quick fix when you find this bug: unbox one side deliberately.""",

"""3. THE MECHANISM — the cache class, and what the compiler inserts

`Integer.valueOf` IS ABOUT FIVE LINES, and reading them removes all the mystery:

    public static Integer valueOf(int i) {
        if (i >= IntegerCache.low && i <= IntegerCache.high)
            return IntegerCache.cache[i + (-IntegerCache.low)];   // ← THE SHARED INSTANCE
        return new Integer(i);                                    // ← a fresh object
    }

    private static class IntegerCache {
        static final int low = -128;
        static final int high;              // 127, or higher via a flag
        static final Integer[] cache;
        static { ... allocate every value from low to high ... }
    }

    NOTE THAT `IntegerCache` IS A STATIC NESTED CLASS. That is the initialization-on-demand holder idiom
    again: the 256 objects are not allocated until `valueOf` is first called, and the JVM's per-class
    initialisation lock makes that exactly-once and thread-safe for free.

WHAT THE COMPILER INSERTS, WHICH IS THE WHOLE REASON THIS IS INVISIBLE:

    Integer a = 127;          →   Integer a = Integer.valueOf(127);
    list.add(5);              →   list.add(Integer.valueOf(5));
    map.put("k", 200);        →   map.put("k", Integer.valueOf(200));
    int x = someInteger;      →   int x = someInteger.intValue();

    NONE OF THAT APPEARS IN YOUR SOURCE. You wrote `Integer a = 127` and a factory call happened.

THE UPPER BOUND IS TUNABLE: `-XX:AutoBoxCacheMax=<n>` raises `IntegerCache.high` — for `Integer` ONLY,
not the other wrappers, and the lower bound is fixed at −128.

    WHICH IS A REASON NOT TO RELY ON THE BEHAVIOUR EVEN WITHIN THE RANGE: someone can change where the
    boundary is. Code that is correct at 127 and broken at 128 is fragile; code that is correct because
    a JVM flag was set is not code you want.

`new Integer(128)` versus `Integer.valueOf(128)`:
    `new` ALWAYS creates a distinct object, even for cached values — so `new Integer(1) == new Integer(1)`
    is false. It has been DEPRECATED FOR REMOVAL since Java 9 precisely because it defeats the cache and
    manufactures identity nobody wanted.

THE SAME PHENOMENON WEARING DIFFERENT CLOTHES — worth recognising as one idea:
    STRING LITERALS are interned into a shared pool, so `"hi" == "hi"` is true and
    `"hi" == new String("hi")` is false. Identical mechanism, identical trap.
    `Boolean.valueOf` returns `Boolean.TRUE`/`FALSE`, so `==` on boxed booleans happens to work
    everywhere — which teaches exactly the wrong lesson.
    ENUM constants are genuinely unique per constant, which is why `==` on enums IS correct and
    idiomatic. THAT IS THE ONE PLACE THE HABIT IS RIGHT, and it is a good reason to convert a closed set
    of integer codes into an enum.""",

"""4. EDGE CASES AND FAILURE MODES

CASE 1 — `Integer a = 128, b = 128; a == b` IS FALSE while 127 is true. The headline, and it passes every
test written with small numbers.

CASE 2 — `Integer big = 1000; int prim = 1000; big == prim` IS TRUE. Comparing a wrapper with a primitive
UNBOXES and compares values. Two comparisons that look identical behave differently.

CASE 3 — `new Integer(1) == new Integer(1)` IS FALSE. `new` always allocates, even inside the cache
range. Deprecated for removal since Java 9.

CASE 4 — `Long` HAS ITS OWN CACHE WITH THE SAME BOUNDS. `Long x = 128L, y = 128L; x == y` is false. And
a `Long` compared with an `Integer` by `.equals` is ALWAYS false regardless of value, because `equals`
checks the type.

CASE 5 — `Double a = 1.0, b = 1.0; a == b` IS ALWAYS FALSE. No cache exists for floating point. At least
it fails consistently.

CASE 6 — `-XX:AutoBoxCacheMax` MOVING THE BOUNDARY. Code that works on one JVM configuration and fails
on another, for a value in between.

CASE 7 — A COUNTER IN A `Map<String, Integer>` COMPARED WITH `==`. Works while counts are small; breaks
the day traffic grows past 127. THE FAILURE ARRIVES WITH SUCCESS.

CASE 8 — UNBOXING A NULL. `int x = map.get(k)` where the key is absent throws
`NullPointerException` on a line with no visible method call — the same autoboxing machinery, failing the
other way.

CASE 9 — `==` IN A LAMBDA OR A COMPARATOR. `list.stream().filter(i -> i == target)` where both are
`Integer` compares identities. Silent, and the filter simply returns nothing for large values.

CASE 10 — `synchronized (Integer.valueOf(1))`. That is a GLOBALLY SHARED cached object. Completely
unrelated code can hold your lock.

CASE 11 — `Integer.valueOf(x).equals(someLong)`. False for every value, because `Integer.equals` checks
`instanceof Integer`. Cross-type numeric equality never works with `equals`.

CASE 12 — RELYING ON `==` FOR BOXED BOOLEANS BECAUSE IT ALWAYS WORKS. It does, and it teaches a habit
that breaks on the next type.

CASE 13 — TREATING THIS AS A JVM BUG. The −128..127 behaviour is MANDATED by the specification. It is
portable, deliberate, and will never change.""",

"""5. THE ALTERNATIVES — how to never meet this again

USE PRIMITIVES. `int`, `long`, `double` — no identity, no cache, no null, and `==` means exactly what it
says. THIS IS THE REAL ANSWER: the bug only exists because a value became an object.

USE `.equals` ON WRAPPERS, ALWAYS. Or `Objects.equals(a, b)` when either might be null.

UNBOX ONE SIDE DELIBERATELY. `a.intValue() == b` is a value comparison and reads as one. Useful as the
minimal fix in existing code.

`Integer.compare(a, b) == 0` when you are already writing a comparator, and `Double.compare` for
floating point, which also handles `NaN` and `-0.0` correctly.

TURN ON THE STATIC ANALYSIS RULE. SpotBugs `RC_REF_COMPARISON`, ErrorProne `ReferenceEquality`, IntelliJ's
"Number objects are compared using ==" inspection. THIS IS A BUG CLASS A TOOL CAN ELIMINATE ENTIRELY,
which is a much better answer than remembering.

USE AN ENUM WHEN THE VALUE SET IS CLOSED. Status codes, types, categories. Then `==` becomes genuinely
correct, `switch` becomes exhaustive, and a typo becomes a compile error. THE HABIT OF USING `==` IS
RIGHT FOR ENUMS AND WRONG FOR EVERYTHING ELSE, which is worth internalising as the rule rather than the
exception.

USE PRIMITIVE COLLECTIONS FOR BULK NUMERIC DATA — `int[]`, or Eclipse Collections / fastutil. No boxing
at all, five times less memory, and the whole question disappears.

`IntStream` / `LongStream` / `DoubleStream` rather than `Stream<Integer>`, for the same reason.

`Map.getOrDefault(k, 0)` INSTEAD OF `map.get(k)` at the boundary where a nullable wrapper becomes a
primitive, so the other autoboxing failure — the NPE — cannot happen either.

WHAT TO SAY: "`==` on objects tests identity, and `Integer.valueOf` returns a shared cached instance for
−128 to 127, so the comparison works for exactly the small values a developer tests with and fails for
the large ones production uses. It is mandated by the specification, so no JVM will behave differently.
I use primitives wherever the value is a number, `.equals` on wrappers, and an enum the moment the set of
values is closed — that is the one place `==` is genuinely right."

""",

"""6. HOW TO AVOID IT — numbered steps

STEP 1 — USE PRIMITIVES WHEREVER THE VALUE IS A NUMBER. The bug exists only because a value became an
object.

STEP 2 — NEVER USE `==` ON WRAPPERS. Not "usually not" — never. It works for the values you test with,
which is the worst possible property.

STEP 3 — USE `.equals`, OR `Objects.equals` WHEN NULL IS POSSIBLE.

STEP 4 — IF YOU MUST COMPARE IN PLACE, UNBOX ONE SIDE. `a.intValue() == b` is a value comparison and
looks like one.

STEP 5 — TURN ON THE STATIC ANALYSIS RULE. ErrorProne `ReferenceEquality` or SpotBugs
`RC_REF_COMPARISON`. A tool can remove this bug class entirely.

STEP 6 — CONVERT CLOSED SETS OF NUMERIC CODES INTO ENUMS. Then `==` is correct, `switch` is exhaustive,
and typos are compile errors.

STEP 7 — DO NOT WRITE `new Integer(x)`. Deprecated for removal, and it defeats the cache deliberately.

STEP 8 — NEVER `synchronized` ON A WRAPPER. Cached instances are process-wide shared objects.

STEP 9 — REMEMBER `Long`, `Short`, `Byte` AND `Character` HAVE THE SAME BOUNDS, and `Float`/`Double` have
no cache at all.

STEP 10 — REMEMBER CROSS-TYPE `equals` IS ALWAYS FALSE. An `Integer` never equals a `Long`, whatever the
values.

STEP 11 — USE `getOrDefault` AT THE BOUNDARY where a nullable wrapper becomes a primitive, so the NPE
version of this trap cannot happen either.

STEP 12 — WHEN A COMPARISON "WORKS ON MY MACHINE" ON SMALL NUMBERS, TEST IT WITH A LARGE ONE. That
single check finds this bug immediately.""",

"""7. THE ANSWER IN PLAIN LANGUAGE — what you would say out loud

'`Integer a = 127, b = 127; a == b` is TRUE. Change both to 128 and it's FALSE. The only difference is
the number.

The reason is that `==` on objects asks "are these the same OBJECT" — it has never asked about value.
And when you write `Integer a = 127`, the compiler inserts `Integer.valueOf(127)`, which returns a
CACHED shared instance for −128 to 127 and a brand-new object outside that range. So at 127 both
variables point at literally the same object and `==` is true; at 128 they're two objects holding the
same number. The comparison was never about value — it only looked correct because of the cache.

And that's the worst possible failure pattern, which is why it's worth knowing rather than just
avoiding. It works for exactly the values a developer tests with — loop counters, small ids, the numbers
1 and 2 in a unit test, all under 128. It fails for the values production uses: real database ids, real
counts. And it's REQUIRED by the language specification for that range, so it's portable behaviour, not
a quirk of one JVM. Nothing will save you and no other JVM behaves differently.

The cache isn't arbitrary either. Small integers are overwhelmingly the common case — counters, sizes,
status codes — so valueOf preallocates 256 objects at class init and hands out the shared one when the
value is in range. That turns millions of allocations into zero for the values that actually occur. And
−128 to 127 is exactly the range of a signed byte, which is the natural "small number" boundary; the
same range is used for Byte, Short and Long. Character caches 0 to 127. Float and Double are never
cached, because there's no sensible finite set of "small doubles" — so `Double a = 1.0, b = 1.0; a == b`
is always false, which at least fails consistently.

One detail most people miss, and it's genuinely useful: `Integer big = 1000; int prim = 1000; big ==
prim` is TRUE. Comparing a wrapper with a PRIMITIVE unboxes the wrapper and compares values — binary
numeric promotion applies. So `Integer == Integer` is identity and `Integer == int` is value. Two
comparisons that look identical in source, differing only in how one side happens to be declared. That's
also the safest minimal fix when you find this in existing code: unbox one side deliberately.

Practically: primitives wherever the value is a number, because the bug only exists because a value
became an object. `.equals` on wrappers, always. Turn on the ErrorProne or SpotBugs reference-equality
rule, because this is a bug class a tool can eliminate entirely rather than something to remember. And
an ENUM the moment the value set is closed — that's the one place the `==` habit is genuinely right, and
you also get exhaustive switches and typos as compile errors.'""",

"""8. THE CODE, LINE BY LINE

    // ── THE WHOLE PHENOMENON ────────────────────────────────────────────
    Integer a = 127, b = 127;   System.out.println(a == b);   // true
    Integer c = 128, d = 128;   System.out.println(c == d);   // FALSE
    //                                             ^^^^^^ the ONLY difference is the
    //   number. Nothing about the code changed.

    // ── WHAT THE COMPILER INSERTED ──────────────────────────────────────
    Integer a = 127;      // → Integer a = Integer.valueOf(127);
    list.add(5);          // → list.add(Integer.valueOf(5));
    int x = someInteger;  // → int x = someInteger.intValue();
    // NONE of that is in your source. You wrote an assignment; a factory call ran.

    // ── valueOf, IN FULL ────────────────────────────────────────────────
    public static Integer valueOf(int i) {
        if (i >= IntegerCache.low && i <= IntegerCache.high)
            return IntegerCache.cache[i + (-IntegerCache.low)];  // ← SHARED INSTANCE
        return new Integer(i);                                   // ← a fresh object
    }
    private static class IntegerCache {          // ← the holder idiom: 256 objects are
        static final int low = -128;             //   not allocated until valueOf is
        static final int high;                   //   first called, and the JVM's class
        static final Integer[] cache;            //   init lock makes that exactly-once
        static { /* allocate every value low..high */ }
    }
    // −128..127 is exactly the range of a SIGNED BYTE. Not arbitrary — the natural
    // "small number" boundary, and the same range for Byte, Short and Long.

    // ── THE DETAIL MOST PEOPLE MISS ─────────────────────────────────────
    Integer big = 1000;
    int prim = 1000;
    System.out.println(big == prim);       // TRUE
    //                 ^^^^^^^^^^^ comparing a wrapper with a PRIMITIVE unboxes the
    //   wrapper and compares VALUES (binary numeric promotion). So:
    //     Integer == Integer  →  IDENTITY
    //     Integer == int      →  VALUE
    //   Two comparisons that look identical, differing only in a declaration.

    // ── WHICH WRAPPERS CACHE ────────────────────────────────────────────
    Integer, Short, Byte, Long   →  −128 to 127
    Character                    →  0 to 127
    Boolean                      →  both values, always (there are only two)
    Float, Double                →  NEVER — there is no "small double"
    Double x = 1.0, y = 1.0;  System.out.println(x == y);   // ALWAYS false.
    //                                                          At least it is honest.

    // ── new DEFEATS THE CACHE DELIBERATELY ──────────────────────────────
    System.out.println(new Integer(1) == new Integer(1));   // false, even at 1
    // Deprecated for removal since Java 9, precisely because it manufactures identity
    // nobody wanted.

    // ── THE BUG THAT ARRIVES WITH SUCCESS ───────────────────────────────
    Map<String,Integer> counts = new HashMap<>();
    if (counts.get(user) == threshold) { ... }
    //                   ^^ works perfectly while counts stay under 128.
    //   Breaks the day traffic grows. THE FAILURE ARRIVES WITH SUCCESS.
    if (counts.get(user).equals(threshold)) { ... }        // ← correct
    if (counts.getOrDefault(user, 0) == thresholdInt) { }  // ← better: primitives

    // ── AND THE ONE PLACE THE HABIT IS RIGHT ────────────────────────────
    if (status == Status.ACTIVE) { ... }
    //          ^^ CORRECT and idiomatic. Enum constants are genuinely unique, so
    //   identity IS value equality. Which is a good argument for turning a closed set
    //   of integer codes into an enum: `==` becomes right, `switch` becomes
    //   exhaustive, and a typo becomes a compile error.

    // ── AND ONE THAT IS ALWAYS WRONG ────────────────────────────────────
    Integer.valueOf(1).equals(Long.valueOf(1L));   // FALSE, for every value —
    //                                                Integer.equals checks the TYPE.
    synchronized (Integer.valueOf(1)) { ... }      // a GLOBALLY SHARED lock object""",

"""9. THE TRACE — the same code, four values

FOLLOW `Integer x = N, y = N; x == y` FOR FOUR VALUES:

    N       valueOf does                        x and y point at        x == y
    ---------------------------------------------------------------------------------
    5       in −128..127 → cache[133]            THE SAME OBJECT         true
    127     in range → cache[255]                THE SAME OBJECT         true
    128     OUT of range → new Integer(128)      two DIFFERENT objects   FALSE
    1000    out of range → new Integer(1000)     two different objects   false
    ---------------------------------------------------------------------------------
    THE BOUNDARY IS BETWEEN ROWS 2 AND 3, and there is nothing in the source to mark it. A test written
    with the numbers in rows 1 and 2 certifies code that fails on rows 3 and 4.

NOW THE SAME COMPARISON WITH ONE SIDE DECLARED `int`:

    declaration                          what the comparison compiles to     result
    ---------------------------------------------------------------------------------
    Integer x = 1000; Integer y = 1000;  reference comparison                 FALSE
    Integer x = 1000; int y = 1000;      x.intValue() == y                    TRUE
    int x = 1000;     int y = 1000;      value comparison                     TRUE
    ---------------------------------------------------------------------------------
    ROW 2 IS THE SURPRISING ONE. Changing a single declaration from `Integer` to `int` — nothing about
    the comparison itself — turns identity into value. Binary numeric promotion applies as soon as one
    operand is a primitive, so the wrapper is unboxed.

    AND THAT MEANS THE FIX IS SOMETIMES A DECLARATION RATHER THAN AN EXPRESSION, which is worth knowing
    when you are looking at existing code and wondering why one comparison in a file is fine.

THE PRODUCTION TIMELINE, which is why this entry exists:

    week    what happens                                    the comparison
    ---------------------------------------------------------------------------------
    1       code written; `if (count == LIMIT)` where both   counts are 3, 7, 12 in the
            are Integer                                      tests → all true → PASSES
    2       code review; nothing looks wrong                 —
    3       deployed; real counts are 40, 90, 110            still works
    12      traffic grows; counts reach 130                  SILENTLY FALSE. The branch
                                                             stops firing. Nothing throws.
    12      symptom: "alerts stopped working"                and no exception, no log
    ---------------------------------------------------------------------------------
    THE BUG WAS ALWAYS THERE. It became visible when the system became successful, which is the most
    expensive time for a bug to appear and the hardest moment to reason clearly. And there is no
    exception, no log line and no stack trace — the branch simply stops being taken.

AND THE CACHE-BOUNDARY TRACE, showing why it is not tunable-away:

    configuration                     127   128   1000
    ---------------------------------------------------------------------------------
    default                           true  false false
    -XX:AutoBoxCacheMax=1000          true  TRUE  TRUE
    a JVM with a different default    true  ?     ?
    ---------------------------------------------------------------------------------
    RAISING THE FLAG MAKES THE BUG DISAPPEAR IN TESTING AND REAPPEAR IN AN ENVIRONMENT THAT DOES NOT SET
    IT. Which is strictly worse than the original problem: the code is now correct only because of a
    deployment detail. The specification guarantees −128..127 and permits more, so "it works here" is
    never evidence.

WHAT PRODUCED WHAT:
    == MEANING IDENTITY          produced the whole phenomenon. The cache only decides WHEN identity
                                 and value happen to coincide.
    THE COMMON CASE BEING SMALL  produced the cache — and therefore produced the alignment between
                                 "values I test with" and "values that work".
    NUMERIC PROMOTION            produced row 2 of the second table, where a declaration changes the
                                 meaning of a comparison.""",

"""10. COMPLEXITY, THE MISTAKES, AND THE TAKEAWAY

    `Integer.valueOf`: O(1), and ZERO allocation inside −128..127 — 256 preallocated objects.
    Outside the range: one allocation per call, a 16-byte object plus a 4-byte reference to reach it.
    Cached: Integer, Short, Byte, Long (−128..127), Character (0..127), Boolean (always).
    NOT cached: Float, Double.
    The −128..127 behaviour is MANDATED by the language specification; caching more is permitted.
    `-XX:AutoBoxCacheMax` raises the upper bound for `Integer` only.

THE #1 MISTAKE: `==` on wrappers. It works for exactly the values you test with and fails for the ones
production uses.

THE #2 MISTAKE: concluding from `127 == 127` that boxed comparison is fine. That is the cache, not the
value.

THE #3 MISTAKE: not knowing `Integer == int` is a VALUE comparison. One declaration changes the meaning.

THE #4 MISTAKE: `new Integer(x)`. Always distinct, even inside the cache range. Deprecated for removal.

THE #5 MISTAKE: expecting `Double` to behave the same way. There is no cache; boxed doubles are never
`==`.

THE #6 MISTAKE: cross-type `equals`. An `Integer` never equals a `Long`, whatever the values.

THE #7 MISTAKE: raising `-XX:AutoBoxCacheMax` to make the symptom go away. Now correctness depends on a
deployment flag.

THE #8 MISTAKE: `synchronized` on a wrapper. Cached instances are process-wide shared objects.

THE #9 MISTAKE: `==` inside a lambda or comparator on boxed values. Silent, and the filter simply returns
nothing.

THE #10 MISTAKE: relying on boxed `Boolean ==` because it always works. It teaches a habit that breaks
on the next type.

THE #11 MISTAKE: treating this as a JVM bug. It is specified, portable, deliberate, and permanent.

THE #12 MISTAKE: leaving a closed set of numeric codes as `Integer`s. An enum makes `==` correct,
`switch` exhaustive, and typos compile errors.

ONE-SENTENCE TAKEAWAY: `==` on objects asks whether two references point at the SAME OBJECT, and
autoboxing routes through `Integer.valueOf`, which returns one of 256 preallocated shared instances for
−128..127 and a fresh object outside that range — so the comparison is never about value and merely
COINCIDES with value for small numbers, which is why it passes every test written with loop counters and
fails silently on real database ids, with no exception and no log line; the behaviour is mandated by the
specification so no JVM will differ, `Float` and `Double` are never cached at all, and the one detail
worth carrying is that `Integer == int` UNBOXES and genuinely compares values — so use primitives where
the value is a number, `.equals` on wrappers, a static-analysis rule to eliminate the bug class
entirely, and an enum the moment the value set is closed, which is the single place the `==` habit is
right.""",
]
